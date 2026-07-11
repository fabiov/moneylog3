from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
from django.utils import timezone
from .models import Account, Movement, Category, Setting, Provision
from .dashboard import dashboard_callback

class DashboardCallbackTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='fabio', password='password123')
        
        # Setting
        self.setting = Setting.for_user(self.user)
        self.setting.provisioning = True
        self.setting.save()

        # Categories
        self.cat_expense = Category.objects.create(name='Spese', user=self.user, active=True)
        self.cat_income = Category.objects.create(name='Stipendio', user=self.user, active=True)

        # Accounts
        self.acc1 = Account.objects.create(name='Main', user=self.user, status='active')
        self.acc2 = Account.objects.create(name='Savings', user=self.user, status='active')

        # Current date for tests
        now = timezone.now()
        self.this_month = now.replace(day=1)
        self.last_month = (self.this_month - datetime.timedelta(days=1)).replace(day=1)

        # Provisions
        Provision.objects.create(user=self.user, date=self.this_month.date(), amount=Decimal('500.00'), description='Fondo Auto')

        # Movements
        # Income this month
        Movement.objects.create(account=self.acc1, category=self.cat_income, date=self.this_month.date(), amount=Decimal('2000.00'), description='Salary')
        # Expense this month
        Movement.objects.create(account=self.acc1, category=self.cat_expense, date=self.this_month.date(), amount=Decimal('-500.00'), description='Rent')
        # Expense last month
        Movement.objects.create(account=self.acc1, category=self.cat_expense, date=self.last_month.date(), amount=Decimal('-400.00'), description='Rent old')

    def test_dashboard_callback_unauthenticated(self):
        from django.contrib.auth.models import AnonymousUser
        req = self.factory.get('/')
        req.user = AnonymousUser()
        context = {}
        res = dashboard_callback(req, context)
        self.assertNotIn('total_balance', res)
        self.assertNotIn('provisioned_total', res)
        self.assertNotIn('spendable_total', res)

    def test_dashboard_callback_authenticated_defaults_to_last_movement(self):
        req = self.factory.get('/')
        req.user = self.user
        context = {}
        res = dashboard_callback(req, context)

        # Check basic stats injections
        self.assertIn('total_balance', res)
        self.assertIn('provisioned_total', res)
        self.assertIn('spendable_total', res)
        # 2000 - 500 - 400 = 1100
        self.assertEqual(res['total_balance'], 1100.0)
        
        # provisioned_total = category_movements (1100) + provisions (500) = 1600.0
        self.assertEqual(res['provisioned_total'], 1600.0)
        
        # spendable_total = total_balance (1100) - provisioned_total (1600) = -500
        self.assertEqual(res['spendable_total'], -500.0)
        
        # Reference date should be this_month
        self.assertEqual(res['reference_date'], self.this_month.date())

        # Check month flow (only this_month: +2000, -500)
        self.assertEqual(res['month_income'], 2000.0)
        self.assertEqual(res['month_expense'], 500.0)
        self.assertEqual(res['month_savings'], 1500.0)

        # Provisioning total = 500
        self.assertIsNotNone(res['provisioning_stats'])
        self.assertEqual(res['provisioning_stats']['total_provisions'], 500.0)

    def test_dashboard_callback_with_query_params(self):
        # Target last_month specifically
        req = self.factory.get(f'/?year={self.last_month.year}&month={self.last_month.month}')
        req.user = self.user
        context = {}
        res = dashboard_callback(req, context)

        self.assertEqual(res['reference_date'], self.last_month.date())
        # Month flow should be 0 income, 400 expense
        self.assertEqual(res['month_income'], 0.0)
        self.assertEqual(res['month_expense'], 400.0)
