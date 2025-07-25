from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
import json

from .models import Product, StockMovement, StockReservation


def product_list(request):
    """Get all products with current stock"""
    products = Product.objects.all()
    data = []
    for product in products:
        data.append({
            'id': str(product.id),
            'name': product.name,
            'description': product.description,
            'price': str(product.price),
            'stock_quantity': product.stock_quantity,
            'created_at': product.created_at.isoformat(),
        })
    return JsonResponse({'products': data})


def product_detail(request, product_id):
    """Get product details"""
    product = get_object_or_404(Product, id=product_id)
    return JsonResponse({
        'id': str(product.id),
        'name': product.name,
        'description': product.description,
        'price': str(product.price),
        'stock_quantity': product.stock_quantity,
        'created_at': product.created_at.isoformat(),
        'updated_at': product.updated_at.isoformat(),
    })


@transaction.atomic
def add_stock(request):
    """Add stock to a product"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 0))
        notes = data.get('notes', '')
        
        if quantity <= 0:
            return JsonResponse({'error': 'Quantity must be positive'}, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        
        # Update stock using F() expression to prevent race conditions
        Product.objects.filter(id=product_id).update(
            stock_quantity=F('stock_quantity') + quantity
        )
        
        # Create stock movement record
        StockMovement.objects.create(
            product=product,
            movement_type='IN',
            quantity=quantity,
            notes=notes,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Refresh product data
        product.refresh_from_db()
        
        return JsonResponse({
            'message': 'Stock added successfully',
            'product_id': str(product.id),
            'new_stock_quantity': product.stock_quantity,
            'added_quantity': quantity
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid quantity'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@transaction.atomic
def reserve_stock(request):
    """Reserve stock for an order (with expiration)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 0))
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({'error': 'Order ID is required'}, status=400)
        
        if quantity <= 0:
            return JsonResponse({'error': 'Quantity must be positive'}, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        
        # Check if we have enough stock
        if product.stock_quantity < quantity:
            return JsonResponse({
                'error': 'Insufficient stock',
                'available': product.stock_quantity,
                'requested': quantity
            }, status=400)
        
        # Check if reservation already exists
        if StockReservation.objects.filter(order_id=order_id).exists():
            return JsonResponse({'error': 'Order already has stock reservation'}, status=400)
        
        # Create reservation (expires in 30 minutes)
        expires_at = timezone.now() + timedelta(minutes=30)
        reservation = StockReservation.objects.create(
            product=product,
            quantity=quantity,
            order_id=order_id,
            expires_at=expires_at
        )
        
        # Update available stock
        Product.objects.filter(id=product_id).update(
            stock_quantity=F('stock_quantity') - quantity
        )
        
        # Create stock movement record
        StockMovement.objects.create(
            product=product,
            movement_type='RESERVED',
            quantity=quantity,
            reference_id=order_id,
            notes=f"Reserved for order {order_id}",
            created_by=request.user if request.user.is_authenticated else None
        )
        
        product.refresh_from_db()
        
        return JsonResponse({
            'message': 'Stock reserved successfully',
            'reservation_id': str(reservation.id),
            'product_id': str(product.id),
            'reserved_quantity': quantity,
            'remaining_stock': product.stock_quantity,
            'expires_at': expires_at.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid quantity'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@transaction.atomic
def confirm_reservation(request):
    """Confirm stock reservation (convert to final sale)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({'error': 'Order ID is required'}, status=400)
        
        reservation = get_object_or_404(StockReservation, order_id=order_id)
        
        # Check if reservation has expired
        if timezone.now() > reservation.expires_at:
            return JsonResponse({'error': 'Reservation has expired'}, status=400)
        
        # Create final stock movement
        StockMovement.objects.create(
            product=reservation.product,
            movement_type='OUT',
            quantity=reservation.quantity,
            reference_id=order_id,
            notes=f"Confirmed sale for order {order_id}",
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Delete the reservation
        reservation.delete()
        
        return JsonResponse({
            'message': 'Stock reservation confirmed',
            'order_id': order_id,
            'quantity': reservation.quantity,
            'product_id': str(reservation.product.id)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@transaction.atomic
def release_reservation(request):
    """Release stock reservation (return stock to available)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({'error': 'Order ID is required'}, status=400)
        
        reservation = get_object_or_404(StockReservation, order_id=order_id)
        
        # Return stock to available
        Product.objects.filter(id=reservation.product.id).update(
            stock_quantity=F('stock_quantity') + reservation.quantity
        )
        
        # Create stock movement record
        StockMovement.objects.create(
            product=reservation.product,
            movement_type='RELEASED',
            quantity=reservation.quantity,
            reference_id=order_id,
            notes=f"Released reservation for order {order_id}",
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Delete the reservation
        reservation.delete()
        
        return JsonResponse({
            'message': 'Stock reservation released',
            'order_id': order_id,
            'quantity': reservation.quantity,
            'product_id': str(reservation.product.id)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def stock_movements(request, product_id):
    """Get stock movement history for a product"""
    product = get_object_or_404(Product, id=product_id)
    movements = StockMovement.objects.filter(product=product)[:50]  # Last 50 movements
    
    data = []
    for movement in movements:
        data.append({
            'id': str(movement.id),
            'movement_type': movement.movement_type,
            'quantity': movement.quantity,
            'reference_id': movement.reference_id,
            'notes': movement.notes,
            'created_at': movement.created_at.isoformat(),
            'created_by': movement.created_by.username if movement.created_by else None,
        })
    
    return JsonResponse({
        'product_id': str(product.id),
        'product_name': product.name,
        'movements': data
    })


def cleanup_expired_reservations(request):
    """Cleanup expired reservations (admin endpoint)"""
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    expired_reservations = StockReservation.objects.filter(expires_at__lt=timezone.now())
    count = 0
    
    for reservation in expired_reservations:
        with transaction.atomic():
            # Return stock to available
            Product.objects.filter(id=reservation.product.id).update(
                stock_quantity=F('stock_quantity') + reservation.quantity
            )
            
            # Create stock movement record
            StockMovement.objects.create(
                product=reservation.product,
                movement_type='RELEASED',
                quantity=reservation.quantity,
                reference_id=reservation.order_id,
                notes=f"Auto-released expired reservation for order {reservation.order_id}"
            )
            
            reservation.delete()
            count += 1
    
    return JsonResponse({
        'message': f'Cleaned up {count} expired reservations',
        'count': count
    })