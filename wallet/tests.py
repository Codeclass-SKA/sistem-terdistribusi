from django.test import TestCase
from django.urls import reverse
from .models import TopUp, TopUpLog
from django.contrib.auth.models import User

class TopUpTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

    def test_topup_atomicity(self):
        initial_balance = self.user.balance  # Misalnya, Anda punya field balance di User model
        amount = 1000

        response = self.client.post(reverse('topup_submit'), {'amount': amount})
        self.assertEqual(response.status_code, 200)

        # Periksa apakah TopUp dan TopUpLog terbentuk
        topup = TopUp.objects.filter(user=self.user, amount=amount).first()
        self.assertIsNotNone(topup)

        log = TopUpLog.objects.filter(topup=topup).first()
        self.assertIsNotNone(log)

        # Periksa apakah saldo bertambah
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, initial_balance + amount)
