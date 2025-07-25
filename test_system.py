#!/usr/bin/env python3
"""
Distributed System Testing Script

This script tests all the APIs in the distributed system to verify functionality.
Run this after starting the system with docker-compose up -d
"""

import requests
import json
import time
import uuid
from typing import Dict, Any, Optional

class DistributedSystemTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        self.current_user = None
        
    def get_csrf_token(self) -> str:
        """Get CSRF token for authentication"""
        response = self.session.get(f"{self.base_url}/admin/login/")
        if response.status_code == 200:
            # Extract CSRF token from response
            import re
            match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']*)["\']', response.text)
            if match:
                return match.group(1)
        return ""
    
    def login(self, username: str = "admin", password: str = "admin") -> bool:
        """Login to get session authentication"""
        csrf_token = self.get_csrf_token()
        
        login_data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrf_token,
            'next': '/admin/'
        }
        
        response = self.session.post(
            f"{self.base_url}/admin/login/", 
            data=login_data,
            headers={'Referer': f"{self.base_url}/admin/login/"}
        )
        
        if response.status_code == 302:  # Redirect after successful login
            self.current_user = username
            print(f"✅ Successfully logged in as {username}")
            return True
        else:
            print(f"❌ Login failed for {username}")
            return False
    
    def test_wallet_topup(self) -> bool:
        """Test wallet top-up functionality with idempotency"""
        print("\n🔄 Testing Wallet Top-up...")
        
        # First top-up
        idempotency_key = str(uuid.uuid4())
        data = {
            'amount': '1000000',
            '_idempotency_key': idempotency_key
        }
        
        response = self.session.post(f"{self.base_url}/wallet/submit/", data=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Top-up successful: {result}")
            
            # Test idempotency - same request should return same result
            response2 = self.session.post(f"{self.base_url}/wallet/submit/", data=data)
            if response2.status_code == 200:
                result2 = response2.json()
                if result == result2:
                    print("✅ Idempotency working correctly")
                    return True
                else:
                    print("❌ Idempotency failed - different results")
                    return False
            else:
                print(f"❌ Second request failed: {response2.status_code}")
                return False
        else:
            print(f"❌ Top-up failed: {response.status_code} - {response.text}")
            return False
    
    def test_inventory_list_products(self) -> Optional[list]:
        """Test listing products"""
        print("\n📦 Testing Inventory - List Products...")
        
        response = self.session.get(f"{self.base_url}/inventory/products/")
        
        if response.status_code == 200:
            result = response.json()
            products = result.get('products', [])
            print(f"✅ Found {len(products)} products")
            for product in products[:3]:  # Show first 3 products
                print(f"   - {product['name']}: {product['price']} (Stock: {product['stock_quantity']})")
            return products
        else:
            print(f"❌ Failed to list products: {response.status_code}")
            return None
    
    def test_inventory_add_stock(self, product_id: str) -> bool:
        """Test adding stock to a product"""
        print(f"\n📈 Testing Inventory - Add Stock to {product_id}...")
        
        data = {
            'product_id': product_id,
            'quantity': 10,
            'notes': 'Test stock addition'
        }
        
        response = self.session.post(
            f"{self.base_url}/inventory/stock/add/",
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Stock added successfully: {result}")
            return True
        else:
            print(f"❌ Failed to add stock: {response.status_code} - {response.text}")
            return False
    
    def test_inventory_reserve_stock(self, product_id: str, order_id: str) -> bool:
        """Test stock reservation"""
        print(f"\n🔒 Testing Inventory - Reserve Stock...")
        
        data = {
            'product_id': product_id,
            'quantity': 2,
            'order_id': order_id
        }
        
        response = self.session.post(
            f"{self.base_url}/inventory/stock/reserve/",
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Stock reserved successfully: {result}")
            return True
        else:
            print(f"❌ Failed to reserve stock: {response.status_code} - {response.text}")
            return False
    
    def test_order_creation(self, product_id: str) -> Optional[str]:
        """Test order creation"""
        print(f"\n🛒 Testing Order Creation...")
        
        data = {
            'items': [
                {
                    'product_id': product_id,
                    'quantity': 2
                }
            ],
            'shipping_address': '123 Test Street, Test City, Test Country',
            'notes': 'Test order from automated testing'
        }
        
        response = self.session.post(
            f"{self.base_url}/orders/create/",
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            order_id = result.get('order_id')
            print(f"✅ Order created successfully: {order_id}")
            print(f"   Total: {result.get('total_amount')}")
            return order_id
        else:
            print(f"❌ Failed to create order: {response.status_code} - {response.text}")
            return None
    
    def test_order_payment(self, order_id: str) -> bool:
        """Test order payment processing"""
        print(f"\n💳 Testing Order Payment...")
        
        data = {
            'order_id': order_id
        }
        
        response = self.session.post(
            f"{self.base_url}/orders/payment/process/",
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Payment processed successfully: {result}")
            return True
        else:
            print(f"❌ Payment failed: {response.status_code} - {response.text}")
            return False
    
    def test_order_details(self, order_id: str) -> bool:
        """Test getting order details"""
        print(f"\n📋 Testing Order Details...")
        
        response = self.session.get(f"{self.base_url}/orders/{order_id}/")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Order details retrieved:")
            print(f"   Status: {result.get('status')}")
            print(f"   Total: {result.get('total_amount')}")
            print(f"   Items: {len(result.get('items', []))}")
            return True
        else:
            print(f"❌ Failed to get order details: {response.status_code}")
            return False
    
    def test_user_orders(self) -> bool:
        """Test listing user orders"""
        print(f"\n📝 Testing User Orders List...")
        
        response = self.session.get(f"{self.base_url}/orders/user/orders/")
        
        if response.status_code == 200:
            result = response.json()
            orders = result.get('orders', [])
            print(f"✅ Found {len(orders)} orders for current user")
            for order in orders[:3]:  # Show first 3 orders
                print(f"   - Order {order['order_id']}: {order['status']} - {order['total_amount']}")
            return True
        else:
            print(f"❌ Failed to list user orders: {response.status_code}")
            return False
    
    def test_stock_movements(self, product_id: str) -> bool:
        """Test stock movement history"""
        print(f"\n📊 Testing Stock Movement History...")
        
        response = self.session.get(f"{self.base_url}/inventory/products/{product_id}/movements/")
        
        if response.status_code == 200:
            result = response.json()
            movements = result.get('movements', [])
            print(f"✅ Found {len(movements)} stock movements")
            for movement in movements[:3]:  # Show first 3 movements
                print(f"   - {movement['movement_type']}: {movement['quantity']} at {movement['created_at']}")
            return True
        else:
            print(f"❌ Failed to get stock movements: {response.status_code}")
            return False
    
    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive Distributed System Test")
        print("=" * 60)
        
        # Login
        if not self.login():
            print("❌ Cannot proceed without authentication")
            return
        
        # Test wallet functionality
        wallet_success = self.test_wallet_topup()
        
        # Test inventory functionality
        products = self.test_inventory_list_products()
        if not products:
            print("❌ Cannot proceed without products")
            return
        
        product_id = products[0]['id']  # Use first product for testing
        
        # Add stock to product
        stock_add_success = self.test_inventory_add_stock(product_id)
        
        # Create an order
        order_id = self.test_order_creation(product_id)
        if not order_id:
            print("❌ Cannot proceed without order")
            return
        
        # Test order details
        order_details_success = self.test_order_details(order_id)
        
        # Process payment
        payment_success = self.test_order_payment(order_id)
        
        # Test additional features
        user_orders_success = self.test_user_orders()
        stock_movements_success = self.test_stock_movements(product_id)
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 Test Summary:")
        print(f"   Wallet Top-up: {'✅' if wallet_success else '❌'}")
        print(f"   Inventory Stock Add: {'✅' if stock_add_success else '❌'}")
        print(f"   Order Creation: {'✅' if order_id else '❌'}")
        print(f"   Order Details: {'✅' if order_details_success else '❌'}")
        print(f"   Payment Processing: {'✅' if payment_success else '❌'}")
        print(f"   User Orders: {'✅' if user_orders_success else '❌'}")
        print(f"   Stock Movements: {'✅' if stock_movements_success else '❌'}")
        
        all_success = all([
            wallet_success, stock_add_success, order_id, 
            order_details_success, payment_success, 
            user_orders_success, stock_movements_success
        ])
        
        if all_success:
            print("\n🎉 All tests passed! Distributed system is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Check the logs above for details.")
        
        return all_success

def main():
    """Main function to run the tests"""
    print("Distributed System API Tester")
    print("Make sure the system is running with: docker-compose up -d")
    print("Waiting 5 seconds for system to be ready...")
    time.sleep(5)
    
    tester = DistributedSystemTester()
    
    try:
        success = tester.run_comprehensive_test()
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the system. Make sure it's running on http://localhost:8000")
        exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        exit(1)

if __name__ == "__main__":
    main()