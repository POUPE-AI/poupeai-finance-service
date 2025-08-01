from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from datetime import datetime
from django.utils import timezone

from drf_spectacular.utils import extend_schema, OpenApiParameter

from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.transactions.models import Transaction

from poupeai_finance_service.dashboard.services import (
    get_transactions_by_period,
    get_chart_data,
    get_initial_balance_until,
    get_category_summary,
    get_invoices_summary,
    fetch_savings_estimate
)

from poupeai_finance_service.dashboard.tools import get_difference_in_percent

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Dashboard'],
        summary="Dashboard data",
        description="Retrieves dashboard data for the specified period.",
        parameters=[
            OpenApiParameter("period", description="Period in 'yyyy-mm' format", type=str, required=False)
        ]
    )
    def get(self, request):
        period = request.query_params.get('period', None)
        
        if period:
            try:
                year, month = map(int, period.split('-'))
                start = datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
                # Fim do mês
                if month == 12:
                    end = start.replace(year=start.year+1, month=1)
                else:
                    end = start.replace(month=start.month+1)
            except Exception:
                return Response({'error': 'Invalid yyyy-mm format.'}, status=400)
        else:
            # Últimos 30 dias, incluindo hoje
            end = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
            start = end - timezone.timedelta(days=30)
            period = None

        if start > timezone.now():
            return Response({'error': 'The specified period cannot be in the future.'}, status=400)
        
        # Get the profile of the authenticated user
        profile = self.request.user
        
        # Get transactions for the specified period
        incomes, expenses = get_transactions_by_period(profile, start, end)

        # Get all bank accounts for the profile
        bank_accounts = BankAccount.objects.filter(profile=profile)
        
        # Calculate initial balance from bank accounts
        initial_balance = get_initial_balance_until(profile, bank_accounts, start)
        balance_chart_data, current_balance = get_chart_data(incomes, expenses, start, end, initial_balance)

        # Calculate the difference in percentage
        balance_difference = get_difference_in_percent(initial_balance, current_balance)
        
        # Get summary of incomes and expenses by category
        incomes_summary = get_category_summary(profile, bank_accounts, 'income', start, end)
        expenses_summary = get_category_summary(profile, bank_accounts, 'expense', start, end)
        invoices_summary = get_invoices_summary(profile, start.year, start.month)

        estimated_saving = fetch_savings_estimate(profile.user_id, Transaction.objects.filter(profile=profile))

        return Response({
            "message": "Dashboard data retrieved successfully.",
            "start_date": start.isoformat(),
            "end_date": (end - timezone.timedelta(days=1)).isoformat(),
            "balance": {
                "current_total": current_balance,
                "difference": balance_difference,
                "chart_data": balance_chart_data
            },
            "incomes": incomes_summary,
            "expenses": expenses_summary,
            "invoices": invoices_summary,
            "spending_by_category": {},
            "estimated_saving": estimated_saving,
        }, status=200)