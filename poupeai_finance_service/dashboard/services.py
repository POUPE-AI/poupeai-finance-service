from poupeai_finance_service.transactions.models import Transaction
from poupeai_finance_service.credit_cards.models import CreditCard, Invoice

from datetime import datetime, date, timedelta

from django.utils import timezone
from django.db import models

from django.conf import settings
from collections import defaultdict
import requests

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
    current_balance = initial_balance # Este é o balanço antes do período 'start'

    # Criamos um defaultdict para agrupar as transações por data eficientemente
    daily_totals = defaultdict(lambda: {'incomes': 0.0, 'expenses': 0.0})

    for income in incomes:
        daily_totals[income.issue_date.isoformat()]['incomes'] += float(income.amount)
    for expense in expenses:
        daily_totals[expense.issue_date.isoformat()]['expenses'] += float(expense.amount)

    # Iterar por cada dia do período (inclusive o 'start', exclusivo o 'end')
    # O range deve ser de 0 até (dias_no_periodo - 1)
    for i in range((end - start).days):
        day = start + timezone.timedelta(days=i) # Começa do 'start' e avança dia a dia
        day_str = day.date().isoformat()

        # Obtenha as transações para o dia atual
        day_incomes = daily_totals[day_str]['incomes']
        day_expenses = daily_totals[day_str]['expenses']

        # Atualize o balanço acumulado
        current_balance += day_incomes - day_expenses

        chart_data.append({
            "date": day_str,
            "balance": float(current_balance),
        })
    return chart_data, current_balance

def get_category_chart_data(queryset, start, end):
    chart_data = []
    # Iterar por cada dia do período (inclusive o 'start', exclusivo o 'end')
    # O range deve ser de 0 até (dias_no_periodo - 1)
    for i in range((end - start).days):
        day = start + timezone.timedelta(days=i) # Já está correto
        day_str = day.date().isoformat()
        day_total = queryset.filter(issue_date=day_str).aggregate(total=models.Sum('amount'))['total'] or 0
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
    cards = CreditCard.objects.filter(profile=profile)
    invoices_data = []
    total_amount = 0.0

    # Faturas do mês atual
    for card in cards:
        invoice = Invoice.objects.filter(credit_card=card, year=year, month=month).first()
        amount = float(invoice.total_amount) if invoice else 0.0
        total_amount += amount
        invoices_data.append({
            "credit_card": card.name,
            "month": f"{month:02d}/{year}",
            "total_amount": amount,
            "paid": invoice.paid if invoice else False,
            "due_date": invoice.due_date.isoformat() if invoice and invoice.due_date else None,
        })

    # Faturas do mês anterior
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    prev_total_amount = 0.0
    for card in cards:
        invoice = Invoice.objects.filter(credit_card=card, year=prev_year, month=prev_month).first()
        prev_total_amount += float(invoice.total_amount) if invoice else 0.0

    # Diferença percentual
    if prev_total_amount == 0:
        percent_diff = 100.0 if total_amount > 0 else -100.0 if total_amount < 0 else 0.0
    else:
        percent_diff = ((total_amount - prev_total_amount) / abs(prev_total_amount)) * 100

    return {
        "current_total": total_amount,
        "difference": percent_diff,
        "chart_data": invoices_data
    }

def fetch_savings_estimate(account_id, transactions_queryset):
    """
    Estima a economia mensal com base nas transações de receita e despesa.
    """
    today = date.today()
    first_day_3_months_ago = (today.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)
    first_day_3_months_ago = first_day_3_months_ago.replace(day=1)
    
    transactions = transactions_queryset.filter(
        issue_date=first_day_3_months_ago
    )

    if len(transactions) == 0:
        return 0.0

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
        "startDate": first_day_3_months_ago.isoformat(),
        "endDate": today.isoformat(),
        "transactions": tx_list,
    }

    url = f"{settings.REPORTS_SERVICE_URL}/savings/estimate"
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # Logue o erro conforme seu padrão
        print(f"Erro ao requisitar savings estimate: {e}")
        return 0.0
