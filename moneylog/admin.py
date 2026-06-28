from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Category, Movement, Account

@admin.register(Account)
class AccountAdmin(ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    search_fields = ('name',)
    list_filter = ('status', 'created_at')
    exclude = ('user',)  # Nasconde il campo user dal form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'user_id', None) is None:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('active', 'created_at')
    exclude = ('user',)  # Nasconde il campo user dal form

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
    list_filter = ('date', 'category', 'account')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(account__user=request.user)

    # Filtra i menu a tendina (dropdown) in fase di creazione del Movimento 
    # per mostrare solo gli Account e le Categorie dell'utente loggato.
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "account":
            kwargs["queryset"] = Account.objects.filter(user=request.user)
        if db_field.name == "category":
            kwargs["queryset"] = Category.objects.filter(user=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
