from django.contrib import admin
from poupeai_finance_service.goals.models import Goal, GoalDeposit

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'initial_balance', 'goal_amount', 'current_balance', 'percentage_completed', 'target_at', 'is_completed')
    list_filter = ('is_completed',)
    search_fields = ('name', 'description')
    list_per_page = 10

@admin.register(GoalDeposit)
class GoalDepositAdmin(admin.ModelAdmin):
    list_display = ('id', 'goal', 'deposit_amount', 'deposit_at', 'note')
    list_filter = ('goal',)
    search_fields = ('goal__name', 'note')
    list_per_page = 10

