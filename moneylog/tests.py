from decimal import Decimal
import datetime
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from .models import Account, Category, Movement
from .forms import TransferForm
from .admin import MovementAdmin


class TransferTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username='admin', password='password123')
        self.account_from = Account.objects.create(name='Conto Corrente', user=self.user, status=Account.Status.MAIN)
        self.account_to = Account.objects.create(name='Conto Risparmio', user=self.user, status=Account.Status.OPEN)
        self.category = Category.objects.create(name='Giroconto', user=self.user, active=True)
        self.site = AdminSite()
        self.admin = MovementAdmin(Movement, self.site)

    def test_transfer_form_validation(self):
        req = self.factory.get('/')
        req.user = self.user

        # Test same account validation error
        form_same = TransferForm(
            req,
            data={
                'from_account': self.account_from.pk,
                'to_account': self.account_from.pk,
                'amount': '100.00',
                'date': timezone.localdate().strftime('%Y-%m-%d'),
                'description': 'Test',
                '_form_submitted': True,
            }
        )
        self.assertFalse(form_same.is_valid())
        self.assertIn("devono essere diversi", str(form_same.errors))

        # Test valid transfer form
        form_valid = TransferForm(
            req,
            data={
                'from_account': self.account_from.pk,
                'to_account': self.account_to.pk,
                'amount': '250.00',
                'date': timezone.localdate().strftime('%Y-%m-%d'),
                'description': 'Spostamento fondi',
                '_form_submitted': True,
            }
        )
        self.assertTrue(form_valid.is_valid())

    def test_make_transfer_action(self):
        post_data = {
            'from_account': str(self.account_from.pk),
            'to_account': str(self.account_to.pk),
            'amount': '500.00',
            'date': '2026-08-25',
            'description': 'Giroconto mensile',
            '_form_submitted': 'True',
        }
        req = self.factory.post('/', data=post_data)
        req.user = self.user
        setattr(req, 'session', 'session')
        messages = FallbackStorage(req)
        setattr(req, '_messages', messages)

        response = self.admin.make_transfer(req)
        self.assertEqual(response.status_code, 302)

        out_mov = Movement.objects.get(account=self.account_from)
        in_mov = Movement.objects.get(account=self.account_to)

        self.assertEqual(out_mov.amount, Decimal('-500.00'))
        self.assertEqual(in_mov.amount, Decimal('500.00'))
        self.assertEqual(out_mov.related_movement, in_mov)
        self.assertEqual(in_mov.related_movement, out_mov)

    def test_make_transfer_action_htmx(self):
        post_data = {
            'from_account': str(self.account_from.pk),
            'to_account': str(self.account_to.pk),
            'amount': '300.00',
            'date': '2026-08-25',
            'description': 'Giroconto HTMX',
            '_form_submitted': 'True',
        }
        req = self.factory.post('/admin/moneylog/movement/make_transfer/', data=post_data, HTTP_HX_REQUEST='true')
        req.user = self.user
        setattr(req, 'session', 'session')
        messages = FallbackStorage(req)
        setattr(req, '_messages', messages)

        response = self.admin.make_transfer(req)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('HX-Redirect'), '/admin/moneylog/movement/')

    def test_sync_save_model(self):
        req = self.factory.get('/')
        req.user = self.user

        out_mov = Movement.objects.create(
            account=self.account_from,
            amount=Decimal('-100.00'),
            date=datetime.date(2026, 8, 20),
            description='Giroconto'
        )
        in_mov = Movement.objects.create(
            account=self.account_to,
            amount=Decimal('100.00'),
            date=datetime.date(2026, 8, 20),
            description='Giroconto',
            related_movement=out_mov
        )
        out_mov.related_movement = in_mov
        out_mov.save()

        # Update out_mov amount and date in admin save_model
        out_mov.amount = Decimal('-150.00')
        out_mov.date = datetime.date(2026, 8, 21)
        self.admin.save_model(req, out_mov, form=None, change=True)

        in_mov.refresh_from_db()
        self.assertEqual(in_mov.amount, Decimal('150.00'))
        self.assertEqual(in_mov.date, datetime.date(2026, 8, 21))

    def test_sync_delete_model(self):
        req = self.factory.get('/')
        req.user = self.user

        out_mov = Movement.objects.create(
            account=self.account_from,
            amount=Decimal('-100.00'),
            date=datetime.date(2026, 8, 20),
            description='Giroconto'
        )
        in_mov = Movement.objects.create(
            account=self.account_to,
            amount=Decimal('100.00'),
            date=datetime.date(2026, 8, 20),
            description='Giroconto',
            related_movement=out_mov
        )
        out_mov.related_movement = in_mov
        out_mov.save()

        self.admin.delete_model(req, out_mov)

        self.assertFalse(Movement.objects.filter(pk=out_mov.pk).exists())
        self.assertFalse(Movement.objects.filter(pk=in_mov.pk).exists())
