from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.conf import settings
import os

def dashboard_view(request):
    """Serve the dashboard HTML file"""
    # Get the base directory of the project
    base_dir = settings.BASE_DIR
    dashboard_path = os.path.join(base_dir, 'dashboard.html')
    
    try:
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    except FileNotFoundError:
        # Fallback to a simple dashboard if file not found
        return HttpResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Distributed System Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                h1 { color: #333; text-align: center; }
                .links { display: flex; gap: 20px; justify-content: center; margin: 30px 0; }
                .link { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
                .link:hover { background: #0056b3; }
                .status { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Distributed System Dashboard</h1>
                <p>Welcome to the Distributed System project. This system includes:</p>
                <ul>
                    <li><strong>Wallet Service</strong> - Balance management with idempotency</li>
                    <li><strong>Inventory Service</strong> - Product and stock management</li>
                    <li><strong>Order Service</strong> - Order processing and payments</li>
                </ul>
                
                <div class="links">
                    <a href="/admin/" class="link">Admin Panel</a>
                    <a href="/inventory/products/" class="link">Products API</a>
                    <a href="/api/status/" class="link">System Status</a>
                </div>
                
                <div class="status">
                    <h3>System Status</h3>
                    <p id="status-text">Loading...</p>
                </div>
                
                <h3>API Endpoints</h3>
                <ul>
                    <li><code>GET /inventory/products/</code> - List products</li>
                    <li><code>POST /wallet/submit/</code> - Top-up wallet</li>
                    <li><code>POST /orders/create/</code> - Create order</li>
                    <li><code>POST /orders/payment/process/</code> - Process payment</li>
                </ul>
                
                <p><strong>Test Credentials:</strong> admin/admin</p>
            </div>
            
            <script>
                fetch('/api/status/')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('status-text').innerHTML = `
                            Database: ${data.database}<br>
                            Cache: ${data.cache}<br>
                            Services: ${Object.keys(data.services).length} online
                        `;
                    })
                    .catch(error => {
                        document.getElementById('status-text').textContent = 'Error loading status';
                    });
            </script>
        </body>
        </html>
        """, content_type='text/html')

def api_status(request):
    """Simple API status endpoint"""
    from django.db import connection
    from django.core.cache import cache
    import time
    
    status = {
        'timestamp': time.time(),
        'database': 'unknown',
        'cache': 'unknown',
        'services': {
            'wallet': 'online',
            'inventory': 'online', 
            'orders': 'online'
        }
    }
    
    # Test database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status['database'] = 'online'
    except Exception:
        status['database'] = 'offline'
    
    # Test cache connection
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            status['cache'] = 'online'
        else:
            status['cache'] = 'offline'
    except Exception:
        status['cache'] = 'offline'
    
    return JsonResponse(status)