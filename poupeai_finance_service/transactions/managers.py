import calendar
import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction as db_transaction
from rest_framework import serializers

from poupeai_finance_service.credit_cards.models import Invoice

class TransactionManager(models.Manager):
    def _calculate_installment_date(self, base_date, installment_offset):
        year = base_date.year
        month = base_date.month + installment_offset

        while month > 12:
            month -= 12
            year += 1
        
        last_day_of_month = calendar.monthrange(year, month)[1]
        day = min(base_date.day, last_day_of_month)

        return base_date.replace(year=year, month=month, day=day)

    @db_transaction.atomic
    def create_installment_transactions(self, **validated_data):
        credit_card = validated_data['credit_card']
        total_installments = validated_data['total_installments']
        issue_date = validated_data['issue_date']
        original_purchase_description = validated_data.get('description')

        purchase_group_uuid = uuid.uuid4()
        transactions = []

        for i in range(1, total_installments + 1):
            installment_issue_date = self._calculate_installment_date(issue_date, i-1)
            invoice = Invoice.objects.get_or_create_invoice(
                credit_card=credit_card,
                issue_date=installment_issue_date
            )

            installment_data = {
                **validated_data,
                'is_installment': True,
                'installment_number': i,
                'total_installments': total_installments,
                'purchase_group_uuid': purchase_group_uuid,
                'original_purchase_description': original_purchase_description,
                'issue_date': installment_issue_date,
                'invoice': invoice,
                'description': f"{original_purchase_description} ({i}/{total_installments})",
            }
            installment_data.pop('apply_to_all_installments', None)
            
            transaction_instance = self.model(**installment_data)
            try:
                transaction_instance.full_clean()
            except ValidationError as e:
                raise serializers.ValidationError(e.message_dict)
            transaction_instance.save()
            transactions.append(transaction_instance)
        
        return transactions