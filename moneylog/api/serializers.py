from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from ..models import Account, Category, Movement


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ('id', 'name', 'status')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'active')
        read_only_fields = ('id', 'active')

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Il nome non può essere vuoto.")
        user = self.context['request'].user
        if Category.objects.filter(user=user, name__iexact=name).exists():
            raise serializers.ValidationError("Esiste già una categoria con questo nome.")
        return name

    def create(self, validated_data):
        return Category.objects.create(user=self.context['request'].user, **validated_data)


class MovementCreateSerializer(serializers.Serializer):
    """
    Creates a movement from a positive amount. The view sets `sign`
    (-1 for expenses, +1 for incomes) in the serializer context.
    A category can be referenced by id or by name; an unknown name is created.
    """
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(max_length=255)
    date = serializers.DateField(required=False)
    account_id = serializers.IntegerField()
    category_id = serializers.IntegerField(required=False)
    category_name = serializers.CharField(max_length=255, required=False)

    def validate_account_id(self, value):
        user = self.context['request'].user
        account = Account.objects.filter(user=user, pk=value).first()
        if account is None:
            raise serializers.ValidationError("Conto non trovato.")
        if account.status == Account.Status.CLOSED:
            raise serializers.ValidationError("Il conto è chiuso.")
        self._account = account
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        category_id = attrs.get('category_id')
        category_name = (attrs.get('category_name') or '').strip()

        if (category_id is None) == (not category_name):
            raise serializers.ValidationError(
                "Specificare esattamente uno tra category_id e category_name."
            )

        if category_id is not None:
            category = Category.objects.filter(user=user, pk=category_id).first()
            if category is None:
                raise serializers.ValidationError({'category_id': "Categoria non trovata."})
            if not category.active:
                raise serializers.ValidationError({'category_id': "La categoria non è attiva."})
            attrs['category'] = category
        else:
            category = Category.objects.filter(user=user, name__iexact=category_name).first()
            if category is not None and not category.active:
                raise serializers.ValidationError({'category_name': "La categoria non è attiva."})
            attrs['category'] = category
            attrs['category_name'] = category_name

        attrs['account'] = self._account
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        sign = self.context['sign']
        category = validated_data['category']
        category_created = False

        with transaction.atomic():
            if category is None:
                category = Category.objects.create(user=user, name=validated_data['category_name'])
                category_created = True
            movement = Movement.objects.create(
                account=validated_data['account'],
                category=category,
                amount=sign * abs(validated_data['amount']),
                date=validated_data.get('date') or timezone.localdate(),
                description=validated_data['description'],
            )

        movement.category_created = category_created
        return movement

    def to_representation(self, instance):
        return {
            'id': instance.pk,
            'account_id': instance.account_id,
            'category_id': instance.category_id,
            'category_name': instance.category.name if instance.category else None,
            'category_created': getattr(instance, 'category_created', False),
            'date': instance.date.isoformat(),
            'amount': str(instance.amount),
            'description': instance.description,
        }
