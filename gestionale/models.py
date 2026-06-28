from django.db import models
from django.contrib.auth.models import User

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