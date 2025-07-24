from django.test import TestCase, override_settings
from django.urls import reverse
from .models import TopUp, TopUpLog
from django.contrib.auth import get_user_model
import threading
import uuid


class TopUpTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass', balance=0)
        self.client.login(username='testuser', password='testpass')

    @override_settings(DEBUG=True)
    def test_topup_race_condition(self):
        initial_balance = self.user.balance
        amount = 1000
        idempotency_key = str(uuid.uuid4())

        def topup_request():
            self.client.post(
                reverse('topup_submit'),
                {'amount': amount},
                HTTP_IDEMPOTENCY_KEY=idempotency_key
            )

        # Buat dua thread yang melakukan top-up secara bersamaan
        thread1 = threading.Thread(target=topup_request)
        thread2 = threading.Thread(target=topup_request)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Periksa apakah saldo bertambah dengan benar
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, initial_balance + amount * 2)

    def tearDown(self):
        # Tutup sesi database secara eksplisit
        from django.db import connection
        connection.close()
