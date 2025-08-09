import random
import itertools
from django.core.management.base import BaseCommand
from django.db import transaction
from poupeai_finance_service.transactions.factories import TransactionFactory
from poupeai_finance_service.profiles.models import Profile
from poupeai_finance_service.categories.models import Category
from poupeai_finance_service.bank_accounts.models import BankAccount
from poupeai_finance_service.credit_cards.models import CreditCard
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the database with a large number of transactions for performance testing.'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10000, help='Number of transactions to create.')

    @transaction.atomic
    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(f'Preparing to create {count} transactions...')

        profile, _ = Profile.objects.get_or_create()
        
        categories = list(Category.objects.filter(profile=profile))
        if not categories:
             categories = [
                Category.objects.create(profile=profile, name=f'Test Categoria {i}', type=random.choice(['income', 'expense']))
                for i in range(5)
            ]

        bank_accounts = list(BankAccount.objects.filter(profile=profile))
        if not bank_accounts:
            bank_accounts = [
                BankAccount.objects.create(profile=profile, name=f'Test Conta {i}')
                for i in range(2)
            ]
        
        credit_cards = list(CreditCard.objects.filter(profile=profile))
        if not credit_cards:
            credit_cards = [
                CreditCard.objects.create(profile=profile, name=f'Test Cartão {i}', closing_day=10, due_day=20, credit_limit=5000.00)
                for i in range(2)
            ]

        self.stdout.write('Prerequisite data is ready. Starting transaction creation...')
        
        category_cycle = itertools.cycle(categories)
        bank_account_cycle = itertools.cycle(bank_accounts)
        credit_card_cycle = itertools.cycle(credit_cards)
        
        transactions_to_create = []
        for i in range(count):
            source_type = random.choice(['BANK_ACCOUNT', 'CREDIT_CARD'])
            
            common_data = {
                'profile': profile,
                'category': next(category_cycle),
                'source_type': source_type,
            }

            if source_type == 'BANK_ACCOUNT':
                common_data['bank_account'] = next(bank_account_cycle)
                common_data['credit_card'] = None
            else:
                common_data['credit_card'] = next(credit_card_cycle)
                common_data['bank_account'] = None
            
            transaction_instance = TransactionFactory.build(**common_data)
            transactions_to_create.append(transaction_instance)

            if (i + 1) % 1000 == 0:
                self.stdout.write(f'{i + 1}/{count} transactions prepared...')

        self.stdout.write('Bulk creating transactions... This might take a moment.')
        TransactionFactory._meta.model.objects.bulk_create(transactions_to_create, batch_size=1000)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} transactions!'))