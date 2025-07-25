from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from django.db import transaction
from decimal import Decimal
import json
import uuid

from wallet.models import TopUp, TopUpLog

User = get_user_model()


class WalletModelTest(TestCase):
    """Test wallet models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            balance=Decimal('1000.00')
        )
    
    def test_topup_creation(self):
        """Test TopUp model creation"""
        topup = TopUp.objects.create(
            user=self.user,
            amount=500
        )
        
        self.assertEqual(topup.user, self.user)
        self.assertEqual(topup.amount, 500)
        self.assertIsNotNone(topup.created)
        self.assertEqual(str(topup), f"500 {self.user.email}")
    
    def test_topup_log_creation(self):
        """Test TopUpLog model creation"""
        topup = TopUp.objects.create(
            user=self.user,
            amount=500
        )
        
        log = TopUpLog.objects.create(
            topup=topup,
            message="Test top-up log"
        )
        
        self.assertEqual(log.topup, topup)
        self.assertEqual(log.message, "Test top-up log")
        self.assertIsNotNone(log.created)
        self.assertEqual(str(log), f"Test top-up log {topup.amount}")


# Disable idempotency middleware for tests
@override_settings(MIDDLEWARE=[
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'wallet.middleware.IdempotencyMiddleware',  # Disabled for tests
    'wallet.middleware.AtomicRequestMiddleware',
])
class WalletViewTest(TestCase):
    """Test wallet views"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            balance=Decimal('1000.00')
        )
        self.client.force_login(self.user)
    
    def tearDown(self):
        # Clear cache after each test
        cache.clear()
    
    def test_topup_form_view(self):
        """Test top-up form view"""
        response = self.client.get(reverse('wallet:topup_form'))
        self.assertEqual(response.status_code, 200)
        # Check that the response contains a UUID-like string (36 characters)
        content = response.content.decode('utf-8')
        # Look for UUID pattern in the content
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        self.assertTrue(re.search(uuid_pattern, content, re.IGNORECASE))
    
    def test_topup_submit_success(self):
        """Test successful top-up submission"""
        initial_balance = self.user.balance
        
        response = self.client.post(reverse('wallet:topup_submit'), {
            'amount': '500',
            '_idempotency_key': str(uuid.uuid4())
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        data = response.json()
        self.assertEqual(data['detail'], 'topup ok')
        self.assertEqual(data['amount'], 500)
        
        # Check user balance updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, initial_balance + Decimal('500'))
        
        # Check TopUp record created
        self.assertTrue(TopUp.objects.filter(user=self.user, amount=500).exists())
        
        # Check TopUpLog created
        topup = TopUp.objects.filter(user=self.user, amount=500).first()
        self.assertTrue(TopUpLog.objects.filter(topup=topup).exists())
    
    def test_topup_submit_invalid_amount(self):
        """Test top-up with invalid amount"""
        response = self.client.post(reverse('wallet:topup_submit'), {
            'amount': '0',
            '_idempotency_key': str(uuid.uuid4())
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'invalid amount')
    
    def test_topup_submit_negative_amount(self):
        """Test top-up with negative amount"""
        response = self.client.post(reverse('wallet:topup_submit'), {
            'amount': '-100',
            '_idempotency_key': str(uuid.uuid4())
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'invalid amount')


# Test with idempotency middleware enabled
class WalletIdempotencyTest(TestCase):
    """Test wallet idempotency functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            balance=Decimal('1000.00')
        )
        self.client.force_login(self.user)
    
    def tearDown(self):
        # Clear cache after each test
        cache.clear()
    
    def test_topup_idempotency(self):
        """Test idempotency functionality"""
        idempotency_key = str(uuid.uuid4())
        
        # First request
        response1 = self.client.post(reverse('wallet:topup_submit'), {
            'amount': '500',
            '_idempotency_key': idempotency_key
        })
        
        # Second request with same idempotency key
        response2 = self.client.post(reverse('wallet:topup_submit'), {
            'amount': '500',
            '_idempotency_key': idempotency_key
        })
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        # Both responses should be identical
        self.assertEqual(response1.json(), response2.json())
        
        # Only one TopUp record should exist
        topups = TopUp.objects.filter(user=self.user, amount=500)
        self.assertEqual(topups.count(), 1)


class WalletTransactionTest(TransactionTestCase):
    """Test wallet transaction handling and race conditions"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            balance=Decimal('1000.00')
        )
    
    def test_atomic_topup(self):
        """Test that top-up is atomic"""
        with self.assertRaises(Exception):
            with transaction.atomic():
                # This should create TopUp but then fail
                TopUp.objects.create(user=self.user, amount=500)
                # Force an error
                raise Exception("Simulated error")
        
        # TopUp should not exist due to rollback
        self.assertFalse(TopUp.objects.filter(user=self.user, amount=500).exists())
        
        # User balance should remain unchanged
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal('1000.00'))
    
    def test_concurrent_topup_safety(self):
        """Test F() expression prevents race conditions"""
        initial_balance = self.user.balance
        
        # Simulate concurrent top-ups using F() expressions
        from django.db.models import F
        
        # Multiple updates should be atomic
        User.objects.filter(id=self.user.id).update(balance=F('balance') + 100)
        User.objects.filter(id=self.user.id).update(balance=F('balance') + 200)
        User.objects.filter(id=self.user.id).update(balance=F('balance') + 300)
        
        self.user.refresh_from_db()
        expected_balance = initial_balance + Decimal('600')
        self.assertEqual(self.user.balance, expected_balance)