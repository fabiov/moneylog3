from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter, RangeNumericFilter, RelatedDropdownFilter
from .models import Category, Movement, Account, Setting, Provision

class UserRelatedDropdownFilter(RelatedDropdownFilter):
    def field_choices(self, field, request, model_admin):
        return field.get_choices(include_blank=False, limit_choices_to={'user': request.user})

@admin.register(Account)
class AccountAdmin(ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    search_fields = ('name',)
    list_filter = ('status', 'created_at')
    exclude = ('user',)  # Hide the user field from the form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'user_id', None) is None:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'active', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('active', 'created_at')
    exclude = ('user',)  # Hide the user field from the form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'user_id', None) is None:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Movement)
class MovementAdmin(ModelAdmin):
    list_display = ('date', 'description', 'amount', 'category', 'account')
    search_fields = ('description',)
    list_filter = (
        ('date', RangeDateFilter),
        ('amount', RangeNumericFilter),
        ('category', UserRelatedDropdownFilter),
        ('account', UserRelatedDropdownFilter)
    )
    list_filter_submit = True
    list_before_template = "admin/moneylog/movement/accounts_cards.html"
    fields = ('amount', 'description', 'date', 'account', 'category')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(account__user=request.user)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if 'account' not in initial:
            main_account = Account.objects.filter(user=request.user, status=Account.Status.MAIN).first()
            if main_account:
                initial['account'] = main_account.pk
        if 'date' not in initial:
            from django.utils import timezone
            initial['date'] = timezone.localdate()
        return initial

    # Filter dropdown menus when creating a Movement
    # to show only the Accounts and Categories of the logged-in user.
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "account":
            kwargs["queryset"] = Account.objects.filter(user=request.user).exclude(status=Account.Status.CLOSED)
            kwargs["empty_label"] = None
        if db_field.name == "category":
            kwargs["queryset"] = Category.objects.filter(user=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def changelist_view(self, request, extra_context=None):
        from django.db.models import Sum
        active_accounts = Account.objects.filter(user=request.user).exclude(status='closed')
        accounts_data = []
        for acc in active_accounts:
            bal = acc.movements.aggregate(total=Sum('amount'))['total'] or 0.0
            accounts_data.append({
                'name': acc.name,
                'balance': float(bal)
            })
        
        extra_context = extra_context or {}
        extra_context['active_accounts_balances'] = accounts_data
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Setting)
class SettingAdmin(ModelAdmin):
    """
    Pagina preferenze utente (singleton).
    L'utente vede e modifica solo il proprio record.
    """
    exclude = ('user',)

    # I tab in Unfold si definiscono tramite fieldsets con class=["tab"]
    fieldsets = (
        (
            "📅 Calendario",
            {
                "fields": ("month", "payday"),
                "description": "Impostazioni relative al mese e al giorno di paga.",
                "classes": ["tab"],
            },
        ),
        (
            "📊 Calcoli",
            {
                "fields": ("months",),
                "description": "Finestra temporale usata nei calcoli delle medie.",
                "classes": ["tab"],
            },
        ),
        (
            "⚙️ Sistema",
            {
                "fields": ("provisioning",),
                "description": "Opzioni avanzate di sistema.",
                "classes": ["tab"],
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'user_id', None) is None:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        """Reindirizza direttamente al form di modifica del proprio record (singleton)."""
        setting = Setting.for_user(request.user)
        change_url = reverse(
            f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change',
            args=[setting.pk],
        )
        return HttpResponseRedirect(change_url)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Personalizza il titolo della pagina preferenze."""
        extra_context = extra_context or {}
        extra_context['title'] = 'Le mie preferenze'
        extra_context['subtitle'] = 'Configura le impostazioni personali del tuo account'
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(Provision)
class ProvisionAdmin(ModelAdmin):
    list_display = ('date', 'description', 'amount')
    search_fields = ('description',)
    list_filter = ('date',)
    date_hierarchy = 'date'
    exclude = ('user',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'user_id', None) is None:
            obj.user = request.user
        super().save_model(request, obj, form, change)
