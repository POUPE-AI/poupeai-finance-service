from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from datetime import datetime
from django.utils import timezone

from drf_spectacular.utils import extend_schema, OpenApiParameter

from poupeai_finance_service.transactions.models import Transaction
from poupeai_finance_service.bank_accounts.models import BankAccount

from poupeai_finance_service.users.querysets import get_profile_by_user

from django.db import models


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
            except Exception:
                return Response({'error': 'Invalid yyyy-mm format.'}, status=400)
        else:
            start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period = start.strftime('%Y-%m')
        
        if start > timezone.now():
            return Response({'error': 'The specified period cannot be in the future.'}, status=400)
        
        if start.month == 12:
            end = start.replace(year=start.year+1, month=1)
        else:
            end = start.replace(month=start.month+1)
        
        profile = get_profile_by_user(self.request.user)
        
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
        
        total_incomes = incomes.aggregate(total=models.Sum('amount'))['total'] or 0
        total_expenses = expenses.aggregate(total=models.Sum('amount'))['total'] or 0

        bank_accounts = BankAccount.objects.filter(profile=profile)
        balance = sum([account.current_balance for account in bank_accounts])
        
        return Response({
            "message": "Dashboard data retrieved successfully.",
            "start_date": start.isoformat() if period else None,
            "end_date": ((start.replace(day=1) + timezone.timedelta(days=31)).replace(day=1) - timezone.timedelta(days=1)).isoformat() if period else None,
            "overview": {
                "total_incomes": total_incomes,
                "total_expenses": total_expenses,
                "balance": balance,
            },
            "economy": {
                "total_incomes": 0,
                "total_expenses": 0,
                "economy_value": 0,
                "economy_percentage": 0,
            },
            "latest_transactions": [],
            "expenses_by_category": [],
            "incomes_by_category": [],
            "expenses_evolution": [],
            "incomes_evolution": [],
            "expenses_x_incomes": [],
            "rankings": {
                "top_expenses": [],
                "top_incomes": []
            }
        }, status=200)