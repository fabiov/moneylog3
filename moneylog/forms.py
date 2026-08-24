from decimal import Decimal
from django import forms
from django.utils import timezone
from unfold.forms import BaseDialogForm
from unfold.widgets import (
    UnfoldAdminDateWidget,
    UnfoldAdminDecimalFieldWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextInputWidget,
)
from .models import Account


class TransferForm(BaseDialogForm):
    from_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        label="Conto Origine (Uscita)",
        required=True,
        widget=UnfoldAdminSelectWidget,
    )
    to_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        label="Conto Destinazione (Entrata)",
        required=True,
        widget=UnfoldAdminSelectWidget,
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        label="Importo (€)",
        required=True,
        widget=UnfoldAdminDecimalFieldWidget,
    )
    date = forms.DateField(
        label="Data",
        initial=timezone.localdate,
        required=True,
        widget=UnfoldAdminDateWidget,
    )
    description = forms.CharField(
        max_length=255,
        initial="Giroconto",
        label="Descrizione",
        required=True,
        widget=UnfoldAdminTextInputWidget,
    )

    def __init__(self, request, object_id=None, *args, **kwargs):
        super().__init__(request, object_id=object_id, *args, **kwargs)
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            accounts_qs = Account.objects.filter(user=request.user).exclude(status=Account.Status.CLOSED).order_by('name')
            self.fields['from_account'].queryset = accounts_qs
            self.fields['to_account'].queryset = accounts_qs

            main_account = accounts_qs.filter(status=Account.Status.MAIN).first()
            if main_account:
                self.fields['from_account'].initial = main_account.pk

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get('from_account')
        to_account = cleaned_data.get('to_account')
        amount = cleaned_data.get('amount')

        if from_account and to_account and from_account == to_account:
            raise forms.ValidationError("Il conto di origine e di destinazione non possono coincidere.")

        if amount is not None and amount <= 0:
            raise forms.ValidationError("L'importo del giroconto deve essere maggiore di zero.")

        return cleaned_data
