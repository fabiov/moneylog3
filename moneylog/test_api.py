from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Account, Category, Movement


class ApiTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='api_user', password='password123')
        self.other = User.objects.create_user(username='other', password='password123')
        self.token = Token.objects.create(user=self.user)

        self.account = Account.objects.create(name='Conto', user=self.user, status=Account.Status.MAIN)
        self.closed = Account.objects.create(name='Vecchio', user=self.user, status=Account.Status.CLOSED)
        self.other_account = Account.objects.create(name='Altrui', user=self.other)

        self.category = Category.objects.create(name='Spesa', user=self.user)
        self.inactive = Category.objects.create(name='Dismessa', user=self.user, active=False)
        self.other_category = Category.objects.create(name='Altrui', user=self.other)

        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def expense(self, **overrides):
        data = {'amount': '12.50', 'description': 'Pane', 'account_id': self.account.pk}
        data.update(overrides)
        return self.client.post('/api/v1/expenses/', data, format='json')


class ApiAuthTest(ApiTestCase):
    def test_requires_token(self):
        anon = APIClient()
        for url in ('/api/v1/accounts/', '/api/v1/categories/'):
            self.assertEqual(anon.get(url).status_code, 401)
        self.assertEqual(anon.post('/api/v1/expenses/', {}, format='json').status_code, 401)

    def test_invalid_token(self):
        anon = APIClient()
        anon.credentials(HTTP_AUTHORIZATION='Token wrong')
        self.assertEqual(anon.get('/api/v1/accounts/').status_code, 401)

    def test_token_in_query_string_is_ignored(self):
        anon = APIClient()
        self.assertEqual(anon.get(f'/api/v1/accounts/?token={self.token.key}').status_code, 401)
        self.assertEqual(anon.get(f'/api/v1/accounts/?auth_token={self.token.key}').status_code, 401)

    def test_session_login_is_not_accepted(self):
        anon = APIClient()
        anon.login(username='api_user', password='password123')
        self.assertEqual(anon.get('/api/v1/accounts/').status_code, 401)


class ApiReadTest(ApiTestCase):
    def test_accounts_scoped_to_user(self):
        res = self.client.get('/api/v1/accounts/')
        self.assertEqual(res.status_code, 200)
        names = [a['name'] for a in res.json()]
        self.assertEqual(names, ['Conto', 'Vecchio'])
        self.assertEqual(res.json()[0]['status'], 'main')

    def test_categories_active_only_by_default(self):
        res = self.client.get('/api/v1/categories/')
        self.assertEqual([c['name'] for c in res.json()], ['Spesa'])

    def test_categories_all(self):
        res = self.client.get('/api/v1/categories/?all=1')
        self.assertEqual([c['name'] for c in res.json()], ['Dismessa', 'Spesa'])


class ApiCategoryCreateTest(ApiTestCase):
    def test_create_category(self):
        res = self.client.post('/api/v1/categories/', {'name': ' Viaggi '}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['name'], 'Viaggi')
        self.assertTrue(Category.objects.filter(user=self.user, name='Viaggi').exists())

    def test_duplicate_category_case_insensitive(self):
        res = self.client.post('/api/v1/categories/', {'name': 'SPESA'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_same_name_as_other_user_allowed(self):
        res = self.client.post('/api/v1/categories/', {'name': 'Altrui'}, format='json')
        self.assertEqual(res.status_code, 201)


class ApiMovementTest(ApiTestCase):
    def test_expense_with_category_id_stored_negative(self):
        res = self.expense(category_id=self.category.pk)
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()
        self.assertEqual(body['amount'], '-12.50')
        self.assertFalse(body['category_created'])
        self.assertEqual(body['date'], timezone.localdate().isoformat())
        mov = Movement.objects.get(pk=body['id'])
        self.assertEqual(mov.amount, Decimal('-12.50'))
        self.assertEqual(mov.category, self.category)

    def test_income_stored_positive(self):
        res = self.client.post('/api/v1/incomes/', {
            'amount': '1000', 'description': 'Stipendio', 'account_id': self.account.pk,
            'category_name': 'Stipendio', 'date': '2026-10-27',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()['amount'], '1000.00')
        self.assertTrue(res.json()['category_created'])
        mov = Movement.objects.get(pk=res.json()['id'])
        self.assertEqual(mov.amount, Decimal('1000.00'))
        self.assertEqual(mov.date.isoformat(), '2026-10-27')

    def test_category_name_reuses_existing_case_insensitive(self):
        res = self.expense(category_name='spesa')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['category_id'], self.category.pk)
        self.assertFalse(res.json()['category_created'])
        self.assertEqual(Category.objects.filter(user=self.user).count(), 2)

    def test_category_name_creates_new(self):
        res = self.expense(category_name='Benzina')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()['category_created'])
        cat = Category.objects.get(user=self.user, name='Benzina')
        self.assertEqual(res.json()['category_id'], cat.pk)

    def test_category_name_of_other_user_creates_own(self):
        res = self.expense(category_name='Altrui')
        self.assertEqual(res.status_code, 201)
        self.assertNotEqual(res.json()['category_id'], self.other_category.pk)
        self.assertTrue(res.json()['category_created'])

    def test_inactive_category_rejected(self):
        self.assertEqual(self.expense(category_id=self.inactive.pk).status_code, 400)
        self.assertEqual(self.expense(category_name='dismessa').status_code, 400)

    def test_category_required_exactly_once(self):
        self.assertEqual(self.expense().status_code, 400)
        res = self.expense(category_id=self.category.pk, category_name='Spesa')
        self.assertEqual(res.status_code, 400)

    def test_foreign_category_rejected(self):
        self.assertEqual(self.expense(category_id=self.other_category.pk).status_code, 400)

    def test_account_validation(self):
        self.assertEqual(self.expense(account_id=self.closed.pk, category_id=self.category.pk).status_code, 400)
        self.assertEqual(self.expense(account_id=self.other_account.pk, category_id=self.category.pk).status_code, 400)
        res = self.client.post('/api/v1/expenses/', {
            'amount': '1', 'description': 'x', 'category_id': self.category.pk,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_amount_must_be_positive(self):
        self.assertEqual(self.expense(amount='-5', category_id=self.category.pk).status_code, 400)
        self.assertEqual(self.expense(amount='0', category_id=self.category.pk).status_code, 400)

    def test_failed_expense_does_not_create_category(self):
        res = self.expense(account_id=self.closed.pk, category_name='Nuova')
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Category.objects.filter(name='Nuova').exists())


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class ApiTokenPageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.client.login(username='staff', password='password123')

    def test_requires_admin_login(self):
        self.client.logout()
        res = self.client.get('/admin/api-token/')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/login/', res['Location'])

    def test_generate_regenerate_revoke(self):
        res = self.client.get('/admin/api-token/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Nessun token attivo')

        self.client.post('/admin/api-token/', {'action': 'generate'})
        first = Token.objects.get(user=self.user).key
        self.assertContains(self.client.get('/admin/api-token/'), first)

        self.client.post('/admin/api-token/', {'action': 'generate'})
        second = Token.objects.get(user=self.user).key
        self.assertNotEqual(first, second)

        self.client.post('/admin/api-token/', {'action': 'revoke'})
        self.assertFalse(Token.objects.filter(user=self.user).exists())
