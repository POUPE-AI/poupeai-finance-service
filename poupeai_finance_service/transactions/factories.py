import factory
import random
from faker import Faker
from poupeai_finance_service.profiles.models import Profile
from poupeai_finance_service.categories.models import Category
from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.credit_cards.models import CreditCard
from .models import Transaction

fake = Faker('pt_BR')

class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    description = factory.Faker('sentence', nb_words=4)
    amount = factory.LazyFunction(lambda: round(random.uniform(10.5, 999.9), 2))
    issue_date = factory.Faker('date_between', start_date='-2y', end_date='today')
    
    profile = None
    category = None
    bank_account = None
    credit_card = None
    source_type = 'BANK_ACCOUNT'

    @factory.post_generation
    def set_type(self, create, extracted, **kwargs):
        if self.category:
            self.type = self.category.type

    @factory.post_generation
    def set_source(self, create, extracted, **kwargs):
        if self.source_type == 'BANK_ACCOUNT':
            self.credit_card = None
        elif self.source_type == 'CREDIT_CARD':
            self.bank_account = None