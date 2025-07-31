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
        transaction_date__lt=until_date
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    expenses = Transaction.objects.filter(
        profile=profile,
        type='expense',
        transaction_date__lt=until_date
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    return initial_balance + incomes - expenses

def get_transactions_by_period(profile, start, end):
    incomes = Transaction.objects.filter(
        profile=profile,
        type='income',
        transaction_date__gte=start,
        transaction_date__lt=end
    )
    expenses = Transaction.objects.filter(
        profile=profile,
        type='expense',
        transaction_date__gte=start,
        transaction_date__lt=end
    )
    return incomes, expenses

def get_chart_data(incomes, expenses, start, end, initial_balance):
    chart_data = []
    current_balance = initial_balance
    for i in range((end - start).days):
        day = start + timezone.timedelta(days=i)
        day_incomes = incomes.filter(transaction_date=day.date()).aggregate(total=models.Sum('amount'))['total'] or 0
        day_expenses = expenses.filter(transaction_date=day.date()).aggregate(total=models.Sum('amount'))['total'] or 0
        current_balance += day_incomes - day_expenses
        chart_data.append({
            "date": day.date().isoformat(),
            "balance": float(current_balance),
        })
    return chart_data, current_balance

def get_category_chart_data(queryset, start, end):
    """
    Gera dados diários para receitas ou despesas.
    """
    chart_data = []
    for i in range((end - start).days):
        day = start + timezone.timedelta(days=i)
        day_total = queryset.filter(transaction_date=day.date()).aggregate(total=models.Sum('amount'))['total'] or 0
        chart_data.append({
            "date": day.date().isoformat(),
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
        transaction_date__gte=start,
        transaction_date__lt=end
    )
    current_total = queryset.aggregate(total=models.Sum('amount'))['total'] or 0

    # Transações do período anterior
    prev_total = Transaction.objects.filter(
        profile=profile,
        type=category_type,
        transaction_date__lt=start
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
        "total": total_amount,
        "difference": percent_diff,
        "chart_data": invoices_data
    }

def fetch_savings_estimate(profile, account_id, transactions_queryset):
    """
    Estima a economia mensal com base nas transações de receita e despesa.
    """
    today = date.today()
    first_day_3_months_ago = (today.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)
    first_day_3_months_ago = first_day_3_months_ago.replace(day=1)
    
    transactions = transactions_queryset.filter(
        transaction_date__gte=first_day_3_months_ago
    )

    if len(transactions) == 0:
        return 0.0

    tx_list = []
    for t in transactions:
        tx_list.append({
            "id": t.id,
            "description": t.description,
            "amount": float(t.amount),
            "date": t.transaction_date.isoformat(),
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
    