from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from datetime import datetime
from django.utils import timezone

from drf_spectacular.utils import extend_schema, OpenApiParameter

from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.profiles.api.permissions import IsProfileActive
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
    permission_classes = [IsProfileActive, IsAuthenticated]
    
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
        
        # Obtenha as datas de início e fim como objetos date simples para consistência com issue_date
        if period:
            try:
                year, month = map(int, period.split('-'))
                start_dt = datetime(year, month, 1) # Sem tzinfo por enquanto
                # Fim do mês (início do próximo mês para filtro exclusivo)
                if month == 12:
                    end_dt = start_dt.replace(year=start_dt.year+1, month=1)
                else:
                    end_dt = start_dt.replace(month=start_dt.month+1)
            except Exception:
                return Response({'error': 'Invalid yyyy-mm format.'}, status=400)
        else:
            # Últimos 30 dias, incluindo o dia atual.
            today_dt = timezone.now() # Use timezone.now() aqui para pegar a data atual com fuso horário
            end_dt = today_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
            start_dt = end_dt - timezone.timedelta(days=30)
            
        # Converter para objetos date simples para os filtros
        # E para passar para as funções de serviço
        start_date_obj = start_dt.date()
        end_date_obj = end_dt.date()

        # Validação de data (opcional, pode ser ajustado para usar date_obj)
        if start_date_obj > timezone.now().date(): # Comparar date com date
             return Response({'error': 'The specified period cannot be in the future.'}, status=400)
        
        profile = self.request.user
        
        # Passar os objetos date para as funções de serviço
        incomes, expenses = get_transactions_by_period(profile, start_date_obj, end_date_obj)
        
        bank_accounts = BankAccount.objects.filter(profile=profile)
        
        initial_balance = get_initial_balance_until(profile, bank_accounts, start_date_obj)
        balance_chart_data, current_balance = get_chart_data(incomes, expenses, start_date_obj, end_date_obj, initial_balance)

        balance_difference = get_difference_in_percent(initial_balance, current_balance)
        
        incomes_summary = get_category_summary(profile, bank_accounts, 'income', start_date_obj, end_date_obj)
        expenses_summary = get_category_summary(profile, bank_accounts, 'expense', start_date_obj, end_date_obj)
        
        # Para get_invoices_summary, passe o ano e mês do start_dt
        invoices_summary = get_invoices_summary(profile, start_dt.year, start_dt.month)

        estimated_saving = fetch_savings_estimate(profile.user_id, Transaction.objects.filter(profile=profile))

        return Response({
            "message": "Dashboard data retrieved successfully.",
            "start_date": start_date_obj.isoformat(), # Usar a data simples para o output
            "end_date": (end_date_obj - timezone.timedelta(days=1)).isoformat(), # Usar a data simples para o output
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