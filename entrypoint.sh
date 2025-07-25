#!/bin/sh

echo "Starting database migrations..."
python manage.py makemigrations core
python manage.py makemigrations wallet
python manage.py makemigrations inventory_service
python manage.py makemigrations order_service
python manage.py migrate

echo "Creating superuser..."
python manage.py createsuperuser --noinput --username=admin --email=admin@example.com || echo "Superuser already exists"
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user = User.objects.get(username='admin')
    user.set_password('admin')
    user.balance = 10000.00
    user.save()
    print('Admin user updated with balance: 10000.00')
except User.DoesNotExist:
    print('Admin user not found')
"

echo "Creating sample data..."
python manage.py shell -c "
from inventory_service.models import Product
from django.contrib.auth import get_user_model

# Create sample products
if not Product.objects.exists():
    products = [
        {'name': 'Laptop Gaming', 'description': 'High-performance gaming laptop', 'price': 15000000, 'stock_quantity': 10},
        {'name': 'Smartphone Android', 'description': 'Latest Android smartphone', 'price': 8000000, 'stock_quantity': 25},
        {'name': 'Wireless Headphones', 'description': 'Premium wireless headphones', 'price': 2500000, 'stock_quantity': 50},
        {'name': 'Mechanical Keyboard', 'description': 'RGB mechanical keyboard', 'price': 1500000, 'stock_quantity': 30},
        {'name': 'Gaming Mouse', 'description': 'High-precision gaming mouse', 'price': 800000, 'stock_quantity': 40},
    ]
    
    for product_data in products:
        Product.objects.create(**product_data)
    
    print('Sample products created')
else:
    print('Products already exist')

# Create additional test users
User = get_user_model()
test_users = [
    {'username': 'testuser1', 'email': 'test1@example.com', 'balance': 5000000},
    {'username': 'testuser2', 'email': 'test2@example.com', 'balance': 7500000},
]

for user_data in test_users:
    username = user_data.pop('username')
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, password='testpass123', **user_data)
        print(f'Created test user: {username} with balance: {user.balance}')
"

echo "Starting Django development server..."
python manage.py runserver 0.0.0.0:8000