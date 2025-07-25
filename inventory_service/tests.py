from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json
import uuid

from inventory_service.models import Product, StockMovement, StockReservation

User = get_user_model()


class InventoryModelTest(TestCase):
    """Test inventory models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            description='A test product',
            price=Decimal('100.00'),
            stock_quantity=50
        )
    
    def test_product_creation(self):
        """Test Product model creation"""
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.price, Decimal('100.00'))
        self.assertEqual(self.product.stock_quantity, 50)
        self.assertIsNotNone(self.product.id)
        self.assertEqual(str(self.product), 'Test Product')
    
    def test_stock_movement_creation(self):
        """Test StockMovement model creation"""
        movement = StockMovement.objects.create(
            product=self.product,
            movement_type='IN',
            quantity=10,
            notes='Test stock in',
            created_by=self.user
        )
        
        self.assertEqual(movement.product, self.product)
        self.assertEqual(movement.movement_type, 'IN')
        self.assertEqual(movement.quantity, 10)
        self.assertEqual(movement.created_by, self.user)
        self.assertIn('Test Product', str(movement))
    
    def test_stock_reservation_creation(self):
        """Test StockReservation model creation"""
        expires_at = timezone.now() + timedelta(hours=1)
        order_id = str(uuid.uuid4())
        
        reservation = StockReservation.objects.create(
            product=self.product,
            quantity=5,
            order_id=order_id,
            expires_at=expires_at
        )
        
        self.assertEqual(reservation.product, self.product)
        self.assertEqual(reservation.quantity, 5)
        self.assertEqual(reservation.order_id, order_id)
        self.assertEqual(reservation.expires_at, expires_at)
        self.assertIn(order_id, str(reservation))


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
class InventoryViewTest(TestCase):
    """Test inventory views"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            description='A test product',
            price=Decimal('100.00'),
            stock_quantity=50
        )
        
        self.client = Client()
    
    def test_product_list_view(self):
        """Test product list API"""
        response = self.client.get(reverse('inventory:product_list'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('products', data)
        self.assertEqual(len(data['products']), 1)
        
        product_data = data['products'][0]
        self.assertEqual(product_data['name'], 'Test Product')
        self.assertEqual(product_data['price'], '100.00')
        self.assertEqual(product_data['stock_quantity'], 50)
    
    def test_product_detail_view(self):
        """Test product detail API"""
        response = self.client.get(
            reverse('inventory:product_detail', kwargs={'product_id': self.product.id})
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'Test Product')
        self.assertEqual(data['price'], '100.00')
        self.assertEqual(data['stock_quantity'], 50)
    
    def test_product_detail_not_found(self):
        """Test product detail with invalid ID"""
        fake_id = uuid.uuid4()
        response = self.client.get(
            reverse('inventory:product_detail', kwargs={'product_id': fake_id})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_add_stock_success(self):
        """Test successful stock addition"""
        initial_stock = self.product.stock_quantity
        
        self.client.force_login(self.user)
        
        data = {
            'product_id': str(self.product.id),
            'quantity': 20,
            'notes': 'Test stock addition',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('inventory:add_stock'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['added_quantity'], 20)
        
        # Check product stock updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock + 20)
        
        # Check stock movement created
        movement = StockMovement.objects.filter(
            product=self.product,
            movement_type='IN',
            quantity=20
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.created_by, self.user)
    
    def test_add_stock_invalid_quantity(self):
        """Test stock addition with invalid quantity"""
        self.client.force_login(self.user)
        
        data = {
            'product_id': str(self.product.id),
            'quantity': -10,
            'notes': 'Invalid quantity',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('inventory:add_stock'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('error', response_data)
    
    def test_reserve_stock_success(self):
        """Test successful stock reservation"""
        initial_stock = self.product.stock_quantity
        order_id = str(uuid.uuid4())
        
        data = {
            'product_id': str(self.product.id),
            'quantity': 5,
            'order_id': order_id,
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('inventory:reserve_stock'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['reserved_quantity'], 5)
        
        # Check product stock reduced
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock - 5)
        
        # Check reservation created
        reservation = StockReservation.objects.filter(order_id=order_id).first()
        self.assertIsNotNone(reservation)
        self.assertEqual(reservation.quantity, 5)
        
        # Check stock movement created
        movement = StockMovement.objects.filter(
            product=self.product,
            movement_type='RESERVED',
            quantity=5,
            reference_id=order_id
        ).first()
        self.assertIsNotNone(movement)
    
    def test_reserve_stock_insufficient(self):
        """Test stock reservation with insufficient stock"""
        order_id = str(uuid.uuid4())
        
        data = {
            'product_id': str(self.product.id),
            'quantity': 100,  # More than available stock (50)
            'order_id': order_id,
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('inventory:reserve_stock'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('Insufficient stock', response_data['error'])
    
    def test_confirm_reservation_success(self):
        """Test successful reservation confirmation"""
        # First create a reservation
        order_id = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(hours=1)
        
        reservation = StockReservation.objects.create(
            product=self.product,
            quantity=5,
            order_id=order_id,
            expires_at=expires_at
        )
        
        data = {
            'order_id': order_id,
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('inventory:confirm_reservation'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['order_id'], order_id)
        
        # Check reservation deleted
        self.assertFalse(StockReservation.objects.filter(order_id=order_id).exists())
        
        # Check stock movement created
        movement = StockMovement.objects.filter(
            product=self.product,
            movement_type='OUT',
            quantity=5,
            reference_id=order_id
        ).first()
        self.assertIsNotNone(movement)
    
    def test_release_reservation_success(self):
        """Test successful reservation release"""
        initial_stock = self.product.stock_quantity
        order_id = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(hours=1)
        
        # Reduce stock first (simulate reservation)
        self.product.stock_quantity -= 5
        self.product.save()
        
        reservation = StockReservation.objects.create(
            product=self.product,
            quantity=5,
            order_id=order_id,
            expires_at=expires_at
        )
        
        data = {
            'order_id': order_id,
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('inventory:release_reservation'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['order_id'], order_id)
        
        # Check stock returned
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock)
        
        # Check reservation deleted
        self.assertFalse(StockReservation.objects.filter(order_id=order_id).exists())
        
        # Check stock movement created
        movement = StockMovement.objects.filter(
            product=self.product,
            movement_type='RELEASED',
            quantity=5,
            reference_id=order_id
        ).first()
        self.assertIsNotNone(movement)
    
    def test_stock_movements_view(self):
        """Test stock movements API"""
        # Create some movements
        StockMovement.objects.create(
            product=self.product,
            movement_type='IN',
            quantity=10,
            notes='Test movement 1'
        )
        
        StockMovement.objects.create(
            product=self.product,
            movement_type='OUT',
            quantity=5,
            notes='Test movement 2'
        )
        
        response = self.client.get(
            reverse('inventory:stock_movements', kwargs={'product_id': self.product.id})
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('movements', data)
        self.assertEqual(len(data['movements']), 2)
        self.assertEqual(data['product_name'], 'Test Product')
    
    def test_cleanup_expired_reservations(self):
        """Test expired reservations cleanup"""
        self.client.force_login(self.admin_user)
        
        # Create expired reservation
        expired_time = timezone.now() - timedelta(hours=1)
        order_id = str(uuid.uuid4())
        
        # Reduce stock first
        initial_stock = self.product.stock_quantity
        self.product.stock_quantity -= 5
        self.product.save()
        
        StockReservation.objects.create(
            product=self.product,
            quantity=5,
            order_id=order_id,
            expires_at=expired_time
        )
        
        response = self.client.get(reverse('inventory:cleanup_expired'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        
        # Check reservation cleaned up
        self.assertFalse(StockReservation.objects.filter(order_id=order_id).exists())
        
        # Check stock returned
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock)
    
    def test_cleanup_expired_reservations_unauthorized(self):
        """Test cleanup endpoint requires admin access"""
        self.client.force_login(self.user)  # Regular user
        
        response = self.client.get(reverse('inventory:cleanup_expired'))
        self.assertEqual(response.status_code, 403)