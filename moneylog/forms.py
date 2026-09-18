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


class GroupedModelChoiceIterator(forms.models.ModelChoiceIterator):
    def __iter__(self):
        if self.field.empty_label is not None:
            yield ('', self.field.empty_label)

        active_qs = self.queryset.exclude(status=Account.Status.CLOSED).order_by('name')
        active_choices = [self.choice(obj) for obj in active_qs]
        if active_choices:
            yield ('Attivi', active_choices)

        closed_qs = self.queryset.filter(status=Account.Status.CLOSED).order_by('name')
        closed_choices = [self.choice(obj) for obj in closed_qs]
        if closed_choices:
            yield ('Chiusi', closed_choices)


class GroupedModelChoiceField(forms.ModelChoiceField):
    iterator = GroupedModelChoiceIterator


class TransferForm(BaseDialogForm):
    from_account = GroupedModelChoiceField(
        queryset=Account.objects.none(),
        label="Conto Origine (Uscita)",
        required=True,
        empty_label=None,
        widget=UnfoldAdminSelectWidget,
    )
    to_account = GroupedModelChoiceField(
        queryset=Account.objects.none(),
        label="Conto Destinazione (Entrata)",
        required=True,
        empty_label=None,
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
            accounts_qs = Account.objects.filter(user=request.user)
            self.fields['from_account'].queryset = accounts_qs
            self.fields['from_account'].empty_label = None
            self.fields['to_account'].queryset = accounts_qs
            self.fields['to_account'].empty_label = None

            main_account = accounts_qs.filter(status=Account.Status.MAIN).first()
            if main_account:
                self.fields['from_account'].initial = main_account.pk

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get('from_account')
        to_account = cleaned_data.get('to_account')
        amount = cleaned_data.get('amount')

        if from_account and to_account and from_account == to_account:
            self.add_error('to_account', "Il conto di destinazione deve essere diverso dal conto di origine.")
            raise forms.ValidationError("Il conto di origine e il conto di destinazione devono essere diversi.")

        if amount is not None and amount <= 0:
            self.add_error('amount', "L'importo del giroconto deve essere maggiore di zero.")
            raise forms.ValidationError("L'importo del giroconto deve essere maggiore di zero.")

        return cleaned_data
