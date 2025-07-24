from django.test import TestCase
from django.urls import reverse
from .models import TopUp, TopUpLog
from django.contrib.auth import get_user_model
import uuid

class TopUpTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass', balance=0)
        self.client.login(username='testuser', password='testpass')

    def test_topup_atomicity(self):
        initial_balance = self.user.balance
        amount = 1000  # Pastikan amount lebih besar dari 0
        idempotency_key = str(uuid.uuid4())  # Generate UUID untuk Idempotency-Key

        response = self.client.post(
            reverse('topup_submit'),
            {'amount': amount},
            HTTP_IDEMPOTENCY_KEY=idempotency_key  # Tambahkan Idempotency-Key dalam header
        )
        self.assertEqual(response.status_code, 200)

        # Periksa apakah TopUp dan TopUpLog terbentuk
        topup = TopUp.objects.filter(user=self.user, amount=amount).first()
        self.assertIsNotNone(topup)

        log = TopUpLog.objects.filter(topup=topup).first()
        self.assertIsNotNone(log)

        # Periksa apakah saldo bertambah
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, initial_balance + amount)