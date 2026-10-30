from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Account, Category
from .serializers import AccountSerializer, CategorySerializer, MovementCreateSerializer


class AccountListView(generics.ListAPIView):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('name')


class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.filter(user=self.request.user).order_by('name')
        if self.request.query_params.get('all') not in ('1', 'true'):
            qs = qs.filter(active=True)
        return qs


class MovementCreateView(APIView):
    sign = None

    def post(self, request):
        serializer = MovementCreateSerializer(
            data=request.data, context={'request': request, 'sign': self.sign}
        )
        serializer.is_valid(raise_exception=True)
        movement = serializer.save()
        return Response(serializer.to_representation(movement), status=status.HTTP_201_CREATED)


class ExpenseCreateView(MovementCreateView):
    sign = -1


class IncomeCreateView(MovementCreateView):
    sign = 1
