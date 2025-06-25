from django.conf import settings
from django.contrib import admin
from django.urls import include
from django.urls import path
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView

urlpatterns = [
    path("api/v1/", include("config.api_router")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),

    path('api/v1/users/', include('users.urls', namespace='users')),
    path('api/v1/categories/', include('categories.urls', namespace='categories')),
    path('api/v1/bank-accounts/', include('bank_accounts.urls', namespace='bank-accounts')),
    path("api/v1/credit-cards/", include("credit_cards.urls", namespace="credit_cards")),
    path("api/v1/transactions/", include('transactions.urls', namespace='transactions')),
    path("api/v1/goals/", include("goals.urls", namespace="goals")),
    path("api/v1/budgets/", include("budgets.urls", namespace="budgets")),
    path("api/v1/dashboard/", include("dashboard.urls", namespace="dashboard")),
]

# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [path(settings.ADMIN_URL, admin.site.urls)]

    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
