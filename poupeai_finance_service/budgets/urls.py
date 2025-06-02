from rest_framework.routers import DefaultRouter
from poupeai_finance_service.budgets.api.viewsets import BudgetViewSet

router = DefaultRouter()
router.register(r'', BudgetViewSet)

app_name = 'budgets'

urlpatterns = router.urls