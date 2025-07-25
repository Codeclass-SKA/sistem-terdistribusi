from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from core.models import CustomUser

User = get_user_model()


class CoreModelTest(TestCase):
    """Test core models"""
    
    def test_custom_user_creation(self):
        """Test CustomUser model creation"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            balance=Decimal('1000.00')
        )
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.balance, Decimal('1000.00'))
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_custom_user_default_balance(self):
        """Test CustomUser default balance"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertEqual(user.balance, Decimal('0.00'))
    
    def test_superuser_creation(self):
        """Test superuser creation"""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.balance, Decimal('0.00'))
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertEqual(str(user), 'testuser')


class CoreViewTest(TestCase):
    """Test core views"""
    
    def test_dashboard_view(self):
        """Test dashboard view accessibility"""
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Distributed System Dashboard', response.content)
        self.assertIn(b'Wallet Service', response.content)
        self.assertIn(b'Inventory Service', response.content)
        self.assertIn(b'Order Service', response.content)
    
    def test_api_status_view(self):
        """Test API status endpoint"""
        response = self.client.get('/api/status/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertIn('timestamp', data)
        self.assertIn('database', data)
        self.assertIn('cache', data)
        self.assertIn('services', data)
        
        # Check services structure
        services = data['services']
        self.assertIn('wallet', services)
        self.assertIn('inventory', services)
        self.assertIn('orders', services)
        
        # All services should be online in test environment
        self.assertEqual(services['wallet'], 'online')
        self.assertEqual(services['inventory'], 'online')
        self.assertEqual(services['orders'], 'online')