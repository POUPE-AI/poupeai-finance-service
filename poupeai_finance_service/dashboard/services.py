import structlog

from poupeai_finance_service.transactions.models import Transaction
from poupeai_finance_service.credit_cards.models import CreditCard, Invoice

from datetime import date
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce

from decimal import Decimal

from django.conf import settings
from collections import defaultdict
import requests

log = structlog.get_logger(__name__)

def get_initial_balance_until(profile, bank_accounts, until_date):
    initial_balance = sum([account.initial_balance for account in bank_accounts])
    incomes = Transaction.objects.filter(
        profile=profile,
        type='income',
        issue_date__lt=until_date,
        source_type='BANK_ACCOUNT' # Adicionado filtro
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    expenses = Transaction.objects.filter(
        profile=profile,
        type='expense',
        issue_date__lt=until_date,
        source_type='BANK_ACCOUNT' # Adicionado filtro
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    return initial_balance + incomes - expenses

def get_transactions_by_period(profile, start, end):
    incomes = Transaction.objects.filter(
        profile=profile,
        type='income',
        issue_date__gte=start,
        issue_date__lt=end,
        source_type='BANK_ACCOUNT' # Adicionado filtro
    )
    expenses = Transaction.objects.filter(
        profile=profile,
        type='expense',
        issue_date__gte=start,
        issue_date__lt=end,
        source_type='BANK_ACCOUNT' # Adicionado filtro
    )
    return incomes, expenses

def get_chart_data(incomes, expenses, start, end, initial_balance):
    chart_data = []
    current_balance = initial_balance 

    daily_totals = defaultdict(lambda: {'incomes': Decimal('0.0'), 'expenses': Decimal('0.0')})

    # Certifique-se de que os objetos incomes e expenses sejam QuerySets
    # Iterar sobre QuerySet para agrupar por data (já está ok como amount é Decimal)
    for income in incomes:
        daily_totals[income.issue_date.isoformat()]['incomes'] += income.amount 
    for expense in expenses:
        daily_totals[expense.issue_date.isoformat()]['expenses'] += expense.amount 

    # Iterar sobre cada dia do período. Agora 'start' e 'end' são objetos date.
    for i in range((end - start).days): 
        day = start + timezone.timedelta(days=i)
        day_str = day.isoformat() # Usar isoformat direto do objeto date
        
        day_incomes = daily_totals[day_str]['incomes']
        day_expenses = daily_totals[day_str]['expenses']
        
        current_balance += day_incomes - day_expenses

        chart_data.append({
            "date": day_str,
            "balance": float(current_balance),
        })
    return chart_data, current_balance

def get_category_chart_data(queryset, start, end):
    chart_data = []
    for i in range((end - start).days):
        day = start + timezone.timedelta(days=i)
        day_str = day.isoformat() # Usar isoformat direto do objeto date
        # O queryset já vem filtrado pelo período. Agora filtramos por objeto date.
        day_total = queryset.filter(issue_date=day).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.0') # <--- ALTEARADO AQUI (day e Decimal)
        chart_data.append({
            "date": day_str,
            "total": float(day_total),
        })
    return chart_data

def get_category_summary(profile, bank_accounts, category_type, start, end):
    """
    Calcula o total, diferença percentual e chart_data para receitas ou despesas.
    """
    # Transações do período atual
    queryset = Transaction.objects.filter(
        profile=profile,
        type=category_type,
        issue_date__gte=start,
        issue_date__lt=end,
        source_type='BANK_ACCOUNT' # Adicionado filtro
    )
    current_total = queryset.aggregate(total=models.Sum('amount'))['total'] or 0

    # Transações do período anterior
    # Importante: o cálculo da diferença percentual está comparando o total atual
    # com o *total acumulado até o início do período atual*. Se você deseja
    # comparar com o total do *período imediatamente anterior*, esta lógica precisaria ser alterada.
    # Por ora, mantemos o filtro source_type.
    prev_total = Transaction.objects.filter(
        profile=profile,
        type=category_type,
        issue_date__lt=start,
        source_type='BANK_ACCOUNT' # Adicionado filtro
    ).aggregate(total=models.Sum('amount'))['total'] or 0

    # Diferença percentual
    if prev_total == 0:
        percent_diff = 100.0 if current_total > 0 else -100.0 if current_total < 0 else 0.0
    else:
        percent_diff = ((current_total - prev_total) / abs(prev_total)) * 100

    # Chart data
    chart_data = get_category_chart_data(queryset, start, end)

    return {
        "current_total": float(current_total),
        "difference": percent_diff,
        "chart_data": chart_data
    }

def get_invoices_summary(profile, year, month):
    """
    Retorna para cada cartão o valor da fatura do mês/ano, o total do mês e a diferença percentual do mês anterior.
    """
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
        
    total_annotation = Coalesce(Sum('transactions__amount'), Decimal('0.0'))

    current_month_prefetch = models.Prefetch(
        'invoices',
        queryset=Invoice.objects.filter(year=year, month=month).annotate(total=total_annotation),
        to_attr='current_invoices'
    )
    
    previous_month_prefetch = models.Prefetch(
        'invoices',
        queryset=Invoice.objects.filter(year=prev_year, month=prev_month).annotate(total=total_annotation),
        to_attr='previous_invoices'
    )

    cards = CreditCard.objects.filter(profile=profile).prefetch_related(
        current_month_prefetch, previous_month_prefetch
    )

    invoices_data = []
    total_amount = Decimal('0.0')
    prev_total_amount = Decimal('0.0')

    for card in cards:
        current_invoice = card.current_invoices[0] if card.current_invoices else None
        current_amount = current_invoice.total if current_invoice else Decimal('0.0')
        total_amount += current_amount

        previous_invoice = card.previous_invoices[0] if card.previous_invoices else None
        previous_amount = previous_invoice.total if previous_invoice else Decimal('0.0')
        prev_total_amount += previous_amount

        invoices_data.append({
            "credit_card": card.name,
            "month": f"{month:02d}/{year}",
            "total_amount": float(current_amount),
            "paid": current_invoice.is_paid if current_invoice else False,
            "due_date": current_invoice.due_date.isoformat() if current_invoice and current_invoice.due_date else None,
        })

    if prev_total_amount == 0:
        percent_diff = 100.0 if total_amount > 0 else 0.0
    else:
        percent_diff = float(((total_amount - prev_total_amount) / abs(prev_total_amount)) * 100)

    return {
        "current_total": float(total_amount),
        "difference": round(percent_diff, 2),
        "chart_data": invoices_data
    }

def fetch_savings_estimate(account_id, transactions_queryset, access_token):
    """
    Estima a economia mensal com base nas transações de receita e despesa.
    """
    today = date.today()
    start_date = today.replace(day=1) - relativedelta(months=3)
    
    transactions = transactions_queryset.prefetch_related("category").filter(
        issue_date__gte=start_date,
        issue_date__lte=today
    )

    if len(transactions) == 0:
        return {
            "estimated_savings": 0,
            "savings_percentage": 0,
            "message": f"Não há transações no período atual.",
        }

    tx_list = []
    for t in transactions:
        tx_list.append({
            "id": t.id,
            "description": t.description,
            "amount": float(t.amount),
            "date": t.issue_date.isoformat(),
            "category": t.category.name if hasattr(t, "category") and t.category else "",
            "type": t.type,
        })

    payload = {
        "accountId": str(account_id),
        "startDate": start_date.isoformat(),
        "endDate": today.isoformat(),
        "transactions": tx_list,
    }

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = f"{settings.REPORTS_SERVICE_URL}/savings/estimate"
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error(
            "Savings estimate request failed",
            event_type="SAVINGS_ESTIMATE_REQUEST_FAILED",
            event_details={
                "account_id": str(account_id),
                "request_url": url,
                "reason": str(e)
            },
            exc_info=e
        )
        return 0.0
    except ValueError as e:
        log.error(
            "Invalid response from savings estimate service",
            event_type="SAVINGS_ESTIMATE_INVALID_RESPONSE",
            event_details={"account_id": str(account_id), "request_url": url},
            exc_info=e
        )
        return 0.0
