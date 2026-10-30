from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('accounts/', views.AccountListView.as_view(), name='accounts'),
    path('categories/', views.CategoryListCreateView.as_view(), name='categories'),
    path('expenses/', views.ExpenseCreateView.as_view(), name='expenses'),
    path('incomes/', views.IncomeCreateView.as_view(), name='incomes'),
]
