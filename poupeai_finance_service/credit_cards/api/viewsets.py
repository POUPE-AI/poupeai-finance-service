from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from poupeai_finance_service.credit_cards.models import CreditCard
from poupeai_finance_service.credit_cards.api.serializers import CreditCardSerializer
from poupeai_finance_service.users.api.permissions import IsProfileActive
from poupeai_finance_service.users.querysets import get_profile_by_user

class CreditCardViewSet(ModelViewSet):
    queryset = CreditCard.objects.all()
    serializer_class = CreditCardSerializer
    permission_classes = [IsAuthenticated, IsProfileActive]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            profile = get_profile_by_user(user)
            return self.queryset.filter(profile=profile).order_by('name')
        return self.queryset.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context['profile'] = get_profile_by_user(self.request.user)
        return context