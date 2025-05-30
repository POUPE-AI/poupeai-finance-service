from django.db import models
import calendar

class InvoiceManager(models.Manager):
    def get_or_create_invoice(self, credit_card, transaction_date):
        closing_day = credit_card.closing_day
        transaction_day = transaction_date.day
        
        if transaction_day > closing_day:
            invoice_month = transaction_date.month + 1
            invoice_year = transaction_date.year
            if invoice_month > 12:
                invoice_month = 1
                invoice_year += 1
        else:
            invoice_month = transaction_date.month
            invoice_year = transaction_date.year
        
        due_day = credit_card.due_day
        last_day_of_invoice_month = calendar.monthrange(invoice_year, invoice_month)[1]
        due_day = min(due_day, last_day_of_invoice_month)
        invoice_due_date = transaction_date.replace(year=invoice_year, month=invoice_month, day=due_day)

        invoice, created = self.get_or_create(
            credit_card=credit_card,
            month=invoice_month,
            year=invoice_year,
            defaults={'due_date': invoice_due_date}
        )
        
        return invoice