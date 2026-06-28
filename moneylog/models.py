from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.db.models import Min, Sum

class Category(models.Model):
    # Django crea automaticamente un id 'bigint auto_increment'
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'  # Forza il nome della tabella come richiesto
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorie'

    def __str__(self):
        return self.name

    def average(self, months: int) -> float:
        now = timezone.now().date()
        from_date = now - relativedelta(months=months)
        
        # Assumiamo che ci sia un modello Movement con una ForeignKey a Category
        # (con related_name='movements'), e campi 'date' e 'amount'.
        first_movement_dict = self.movements.aggregate(min_date=Min('date'))
        first_movement_date = first_movement_dict['min_date']

        if first_movement_date and first_movement_date > from_date:
            from_date = first_movement_date
            delta = relativedelta(now, first_movement_date)
            months = delta.years * 12 + delta.months
            
            if months == 0:
                months = 1

        if months <= 0:
            return 0.0

        total_amount = self.movements.filter(date__gte=from_date).aggregate(
            total=Sum('amount')
        )['total']
        
        if total_amount is None:
            total_amount = 0.0

        return round(float(total_amount) / months, 2)


class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default='active')  # e.g., 'active', 'closed'
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts'
        verbose_name = 'Conto'
        verbose_name_plural = 'Conti'

    def __str__(self):
        return self.name


class Movement(models.Model):
    account = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name='movements'
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='movements'
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'movements'
        verbose_name = 'Movimento'
        verbose_name_plural = 'Movimenti'

    def __str__(self):
        return f"{self.date} - {self.description} ({self.amount})"

    @classmethod
    def most_used_account_id(cls, user_id: int) -> int | None:
        from django.db.models import Count
        
        # Filtriamo tramite la relazione con account (assumendo che user_id si trovi in Account)
        # Se user_id si trova su Movement, cambia in `user_id=user_id`
        result = cls.objects.filter(
            account__user_id=user_id
        ).exclude(
            account__status='closed'
        ).values(
            'account_id'
        ).annotate(
            account_count=Count('account_id')
        ).order_by('-account_count').first()

        return result['account_id'] if result else None