from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
import json
import uuid

from order_service.models import Order, OrderItem, OrderStatusHistory, PaymentRecord
from inventory_service.models import Product

User = get_user_model()


class OrderModelTest(TestCase):
    """Test order models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            balance=Decimal('10000.00')
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            description='A test product',
            price=Decimal('100.00'),
            stock_quantity=50
        )
        
        self.order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('200.00'),
            shipping_address='123 Test St, Test City',
            notes='Test order'
        )
    
    def test_order_creation(self):
        """Test Order model creation"""
        self.assertEqual(self.order.customer, self.user)
        self.assertEqual(self.order.status, 'PENDING')
        self.assertEqual(self.order.total_amount, Decimal('200.00'))
        self.assertEqual(self.order.shipping_address, '123 Test St, Test City')
        self.assertIn(str(self.order.id), str(self.order))
    
    def test_order_item_creation(self):
        """Test OrderItem model creation"""
        item = OrderItem.objects.create(
            order=self.order,
            product_id=self.product.id,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=2,
            subtotal=self.product.price * 2
        )
        
        self.assertEqual(item.order, self.order)
        self.assertEqual(item.product_id, self.product.id)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.subtotal, Decimal('200.00'))
        self.assertIn(self.product.name, str(item))
    
    def test_order_status_history_creation(self):
        """Test OrderStatusHistory model creation"""
        history = OrderStatusHistory.objects.create(
            order=self.order,
            from_status='PENDING',
            to_status='CONFIRMED',
            notes='Order confirmed',
            changed_by=self.user
        )
        
        self.assertEqual(history.order, self.order)
        self.assertEqual(history.from_status, 'PENDING')
        self.assertEqual(history.to_status, 'CONFIRMED')
        self.assertEqual(history.changed_by, self.user)
        self.assertIn('PENDING → CONFIRMED', str(history))
    
    def test_payment_record_creation(self):
        """Test PaymentRecord model creation"""
        payment = PaymentRecord.objects.create(
            order=self.order,
            payment_type='WALLET',
            amount=Decimal('200.00'),
            status='COMPLETED',
            transaction_id='test_txn_123'
        )
        
        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.payment_type, 'WALLET')
        self.assertEqual(payment.amount, Decimal('200.00'))
        self.assertEqual(payment.status, 'COMPLETED')
        self.assertIn(str(self.order.id), str(payment))


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
class OrderViewTest(TestCase):
    """Test order views"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            balance=Decimal('10000.00')
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
    
    def test_create_order_success(self):
        """Test successful order creation"""
        self.client.force_login(self.user)
        
        data = {
            'items': [
                {
                    'product_id': str(self.product.id),
                    'quantity': 2
                }
            ],
            'shipping_address': '123 Test St, Test City',
            'notes': 'Test order',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:create_order'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn('order_id', response_data)
        self.assertEqual(response_data['status'], 'PENDING')
        
        # Check order created
        order_id = response_data['order_id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.customer, self.user)
        self.assertEqual(order.status, 'PENDING')
        
        # Check order items created
        items = order.items.all()
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().quantity, 2)
        
        # Check status history created
        history = order.status_history.all()
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().to_status, 'PENDING')
    
    def test_create_order_unauthorized(self):
        """Test order creation without authentication"""
        data = {
            'items': [
                {
                    'product_id': str(self.product.id),
                    'quantity': 2
                }
            ],
            'shipping_address': '123 Test St, Test City',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:create_order'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_create_order_no_items(self):
        """Test order creation with no items"""
        self.client.force_login(self.user)
        
        data = {
            'items': [],
            'shipping_address': '123 Test St, Test City',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:create_order'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('must contain at least one item', response_data['error'])
    
    def test_create_order_no_shipping_address(self):
        """Test order creation without shipping address"""
        self.client.force_login(self.user)
        
        data = {
            'items': [
                {
                    'product_id': str(self.product.id),
                    'quantity': 2
                }
            ],
            'shipping_address': '',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:create_order'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('required', response_data['error'])
    
    def test_order_detail_success(self):
        """Test order detail view"""
        order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('200.00'),
            shipping_address='123 Test St, Test City'
        )
        
        OrderItem.objects.create(
            order=order,
            product_id=self.product.id,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=2,
            subtotal=Decimal('200.00')
        )
        
        self.client.force_login(self.user)
        
        response = self.client.get(
            reverse('orders:order_detail', kwargs={'order_id': order.id})
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['order_id'], str(order.id))
        self.assertEqual(data['customer'], self.user.username)
        self.assertEqual(len(data['items']), 1)
    
    def test_order_detail_unauthorized(self):
        """Test order detail view without authentication"""
        order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('200.00'),
            shipping_address='123 Test St, Test City'
        )
        
        response = self.client.get(
            reverse('orders:order_detail', kwargs={'order_id': order.id})
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_order_detail_forbidden(self):
        """Test order detail view for different user's order"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        order = Order.objects.create(
            customer=other_user,
            total_amount=Decimal('200.00'),
            shipping_address='123 Test St, Test City'
        )
        
        self.client.force_login(self.user)
        
        response = self.client.get(
            reverse('orders:order_detail', kwargs={'order_id': order.id})
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_user_orders_list(self):
        """Test user orders list view"""
        # Create multiple orders for user
        order1 = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('100.00'),
            shipping_address='123 Test St'
        )
        
        order2 = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('200.00'),
            shipping_address='456 Test Ave'
        )
        
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('orders:user_orders'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('orders', data)
        self.assertEqual(len(data['orders']), 2)
    
    def test_process_payment_success(self):
        """Test successful payment processing"""
        order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('100.00'),
            shipping_address='123 Test St, Test City',
            status='PENDING'
        )
        
        initial_balance = self.user.balance
        
        self.client.force_login(self.user)
        
        data = {
            'order_id': str(order.id),
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:process_payment'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['order_id'], str(order.id))
        
        # Check user balance deducted
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, initial_balance - Decimal('100.00'))
        
        # Check order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'CONFIRMED')
        
        # Check payment record created
        payment = PaymentRecord.objects.filter(order=order, payment_type='WALLET').first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, 'COMPLETED')
        self.assertEqual(payment.amount, Decimal('100.00'))
    
    def test_process_payment_insufficient_balance(self):
        """Test payment with insufficient balance"""
        order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('20000.00'),  # More than user balance
            shipping_address='123 Test St, Test City',
            status='PENDING'
        )
        
        self.client.force_login(self.user)
        
        data = {
            'order_id': str(order.id),
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:process_payment'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('Insufficient balance', response_data['error'])
    
    def test_cancel_order_success(self):
        """Test successful order cancellation"""
        order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('100.00'),
            shipping_address='123 Test St, Test City',
            status='PENDING'
        )
        
        self.client.force_login(self.user)
        
        data = {
            'order_id': str(order.id),
            'reason': 'Customer changed mind',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:cancel_order'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'CANCELLED')
        
        # Check order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'CANCELLED')
        
        # Check status history updated
        history = order.status_history.filter(to_status='CANCELLED').first()
        self.assertIsNotNone(history)
        self.assertIn('Customer changed mind', history.notes)
    
    def test_cancel_order_with_refund(self):
        """Test order cancellation with refund"""
        order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('100.00'),
            shipping_address='123 Test St, Test City',
            status='CONFIRMED'  # Already paid
        )
        
        # Create payment record
        PaymentRecord.objects.create(
            order=order,
            payment_type='WALLET',
            amount=Decimal('100.00'),
            status='COMPLETED',
            transaction_id='test_payment'
        )
        
        # Deduct from user balance (simulate payment)
        self.user.balance -= Decimal('100.00')
        self.user.save()
        initial_balance = self.user.balance
        
        self.client.force_login(self.user)
        
        data = {
            'order_id': str(order.id),
            'reason': 'Product unavailable',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:cancel_order'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'CANCELLED')
        self.assertIn('refund_amount', response_data)
        
        # Check refund processed
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, initial_balance + Decimal('100.00'))
        
        # Check refund payment record created
        refund = PaymentRecord.objects.filter(
            order=order,
            payment_type='REFUND',
            status='COMPLETED'
        ).first()
        self.assertIsNotNone(refund)
    
    def test_update_order_status_admin(self):
        """Test order status update by admin"""
        order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('100.00'),
            shipping_address='123 Test St, Test City',
            status='CONFIRMED'
        )
        
        self.client.force_login(self.admin_user)
        
        data = {
            'order_id': str(order.id),
            'status': 'SHIPPED',
            'notes': 'Package shipped via FedEx',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:update_status'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['new_status'], 'SHIPPED')
        
        # Check order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'SHIPPED')
        
        # Check status history created
        history = order.status_history.filter(to_status='SHIPPED').first()
        self.assertIsNotNone(history)
        self.assertEqual(history.changed_by, self.admin_user)
    
    def test_update_order_status_unauthorized(self):
        """Test order status update by regular user"""
        order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('100.00'),
            shipping_address='123 Test St, Test City',
            status='CONFIRMED'
        )
        
        self.client.force_login(self.user)  # Regular user
        
        data = {
            'order_id': str(order.id),
            'status': 'SHIPPED',
            '_idempotency_key': str(uuid.uuid4())
        }
        
        response = self.client.post(
            reverse('orders:update_status'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_order_status_history(self):
        """Test order status history view"""
        order = Order.objects.create(
            customer=self.user,
            total_amount=Decimal('100.00'),
            shipping_address='123 Test St, Test City'
        )
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            from_status='',
            to_status='PENDING',
            notes='Order created',
            changed_by=self.user
        )
        
        OrderStatusHistory.objects.create(
            order=order,
            from_status='PENDING',
            to_status='CONFIRMED',
            notes='Payment confirmed',
            changed_by=self.user
        )
        
        self.client.force_login(self.user)
        
        response = self.client.get(
            reverse('orders:order_history', kwargs={'order_id': order.id})
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('history', data)
        self.assertEqual(len(data['history']), 2)