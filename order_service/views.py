from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
import json
import requests
from decimal import Decimal

from .models import Order, OrderItem, OrderStatusHistory, PaymentRecord


def create_order(request):
    """Create a new order with multiple items"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        shipping_address = data.get('shipping_address', '')
        notes = data.get('notes', '')
        
        if not items:
            return JsonResponse({'error': 'Order must contain at least one item'}, status=400)
        
        if not shipping_address:
            return JsonResponse({'error': 'Shipping address is required'}, status=400)
        
        with transaction.atomic():
            # Create the order
            order = Order.objects.create(
                customer=request.user,
                shipping_address=shipping_address,
                notes=notes
            )
            
            total_amount = Decimal('0.00')
            
            # Process each item
            for item_data in items:
                product_id = item_data.get('product_id')
                quantity = int(item_data.get('quantity', 0))
                
                if quantity <= 0:
                    raise ValueError(f"Invalid quantity for product {product_id}")
                
                # Call inventory service to get product details and reserve stock
                # In a real microservices setup, this would be an HTTP call
                # For now, we'll simulate the interaction
                
                # TODO: Replace with actual HTTP call to inventory service
                # For demo purposes, we'll create a simplified version
                
                # Simulate product data (in real scenario, this comes from inventory service)
                product_name = f"Product {product_id}"
                unit_price = Decimal('10.00')  # This should come from inventory service
                
                # Reserve stock (this should be an HTTP call to inventory service)
                try:
                    # reservation_response = requests.post(
                    #     'http://inventory-service/stock/reserve/',
                    #     json={
                    #         'product_id': product_id,
                    #         'quantity': quantity,
                    #         'order_id': str(order.id)
                    #     }
                    # )
                    # if reservation_response.status_code != 200:
                    #     raise Exception(f"Failed to reserve stock for product {product_id}")
                    pass  # Placeholder for stock reservation
                except Exception as e:
                    raise Exception(f"Stock reservation failed: {str(e)}")
                
                # Create order item
                subtotal = unit_price * quantity
                OrderItem.objects.create(
                    order=order,
                    product_id=product_id,
                    product_name=product_name,
                    unit_price=unit_price,
                    quantity=quantity,
                    subtotal=subtotal
                )
                
                total_amount += subtotal
            
            # Update order total
            order.total_amount = total_amount
            order.save()
            
            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                from_status='',
                to_status='PENDING',
                notes='Order created',
                changed_by=request.user
            )
            
            return JsonResponse({
                'message': 'Order created successfully',
                'order_id': str(order.id),
                'total_amount': str(order.total_amount),
                'status': order.status,
                'created_at': order.created_at.isoformat()
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Order creation failed: {str(e)}'}, status=500)


def order_detail(request, order_id):
    """Get order details with items"""
    order = get_object_or_404(Order, id=order_id)
    
    # Check if user has access to this order
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if order.customer != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    items = []
    for item in order.items.all():
        items.append({
            'product_id': str(item.product_id),
            'product_name': item.product_name,
            'unit_price': str(item.unit_price),
            'quantity': item.quantity,
            'subtotal': str(item.subtotal)
        })
    
    return JsonResponse({
        'order_id': str(order.id),
        'customer': order.customer.username,
        'status': order.status,
        'total_amount': str(order.total_amount),
        'shipping_address': order.shipping_address,
        'notes': order.notes,
        'items': items,
        'created_at': order.created_at.isoformat(),
        'updated_at': order.updated_at.isoformat()
    })


def user_orders(request):
    """Get orders for the authenticated user"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    orders = Order.objects.filter(customer=request.user)
    
    data = []
    for order in orders:
        data.append({
            'order_id': str(order.id),
            'status': order.status,
            'total_amount': str(order.total_amount),
            'item_count': order.items.count(),
            'created_at': order.created_at.isoformat()
        })
    
    return JsonResponse({'orders': data})


@transaction.atomic
def process_payment(request):
    """Process payment for an order using wallet"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({'error': 'Order ID is required'}, status=400)
        
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user owns this order
        if order.customer != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Check order status
        if order.status != 'PENDING':
            return JsonResponse({'error': f'Cannot pay for order with status: {order.status}'}, status=400)
        
        # Check if user has sufficient balance
        User = get_user_model()
        user = User.objects.select_for_update().get(id=request.user.id)
        
        if user.balance < order.total_amount:
            return JsonResponse({
                'error': 'Insufficient balance',
                'required': str(order.total_amount),
                'available': str(user.balance)
            }, status=400)
        
        # Create payment record
        payment = PaymentRecord.objects.create(
            order=order,
            payment_type='WALLET',
            amount=order.total_amount,
            status='PENDING'
        )
        
        try:
            # Deduct from user wallet
            user.balance = F('balance') - order.total_amount
            user.save(update_fields=['balance'])
            user.refresh_from_db()
            
            # Update payment status
            payment.status = 'COMPLETED'
            payment.transaction_id = f"wallet_payment_{payment.id}"
            payment.save()
            
            # Update order status
            old_status = order.status
            order.status = 'CONFIRMED'
            order.save()
            
            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                from_status=old_status,
                to_status='CONFIRMED',
                notes=f'Payment completed via wallet. Payment ID: {payment.id}',
                changed_by=request.user
            )
            
            # TODO: Confirm stock reservations in inventory service
            # requests.post('http://inventory-service/stock/confirm/', 
            #              json={'order_id': str(order.id)})
            
            return JsonResponse({
                'message': 'Payment processed successfully',
                'order_id': str(order.id),
                'payment_id': str(payment.id),
                'amount_paid': str(order.total_amount),
                'new_balance': str(user.balance),
                'order_status': order.status
            })
            
        except Exception as e:
            # If payment fails, mark payment as failed
            payment.status = 'FAILED'
            payment.notes = str(e)
            payment.save()
            raise e
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Payment failed: {str(e)}'}, status=500)


@transaction.atomic
def cancel_order(request):
    """Cancel an order and process refund if needed"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        reason = data.get('reason', 'Customer cancellation')
        
        if not order_id:
            return JsonResponse({'error': 'Order ID is required'}, status=400)
        
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user owns this order or is staff
        if order.customer != request.user and not request.user.is_staff:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Check if order can be cancelled
        if order.status in ['DELIVERED', 'CANCELLED', 'REFUNDED']:
            return JsonResponse({'error': f'Cannot cancel order with status: {order.status}'}, status=400)
        
        old_status = order.status
        needs_refund = order.status in ['CONFIRMED', 'PROCESSING', 'SHIPPED']
        
        # Process refund if payment was made
        if needs_refund:
            completed_payments = order.payments.filter(payment_type='WALLET', status='COMPLETED')
            total_refund = completed_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            if total_refund > 0:
                # Create refund payment record
                refund_payment = PaymentRecord.objects.create(
                    order=order,
                    payment_type='REFUND',
                    amount=total_refund,
                    status='PENDING'
                )
                
                try:
                    # Refund to user wallet
                    User = get_user_model()
                    User.objects.filter(id=order.customer.id).update(
                        balance=F('balance') + total_refund
                    )
                    
                    refund_payment.status = 'COMPLETED'
                    refund_payment.transaction_id = f"wallet_refund_{refund_payment.id}"
                    refund_payment.save()
                    
                except Exception as e:
                    refund_payment.status = 'FAILED'
                    refund_payment.notes = str(e)
                    refund_payment.save()
                    raise Exception(f"Refund failed: {str(e)}")
        
        # Update order status
        order.status = 'CANCELLED'
        order.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status='CANCELLED',
            notes=f'Order cancelled. Reason: {reason}',
            changed_by=request.user
        )
        
        # TODO: Release stock reservations in inventory service
        # requests.post('http://inventory-service/stock/release/', 
        #              json={'order_id': str(order.id)})
        
        response_data = {
            'message': 'Order cancelled successfully',
            'order_id': str(order.id),
            'status': order.status
        }
        
        if needs_refund:
            completed_payments = order.payments.filter(payment_type='WALLET', status='COMPLETED')
            total_refund = completed_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            response_data['refund_amount'] = str(total_refund)
        
        return JsonResponse(response_data)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Cancellation failed: {str(e)}'}, status=500)


@transaction.atomic
def update_order_status(request):
    """Update order status (admin/staff only)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Staff access required'}, status=403)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        if not order_id or not new_status:
            return JsonResponse({'error': 'Order ID and status are required'}, status=400)
        
        order = get_object_or_404(Order, id=order_id)
        
        # Validate status transition
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'error': f'Invalid status: {new_status}'}, status=400)
        
        old_status = order.status
        
        if old_status == new_status:
            return JsonResponse({'error': 'Order already has this status'}, status=400)
        
        # Update order status
        order.status = new_status
        order.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status=new_status,
            notes=notes,
            changed_by=request.user
        )
        
        return JsonResponse({
            'message': 'Order status updated successfully',
            'order_id': str(order.id),
            'old_status': old_status,
            'new_status': new_status
        })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Status update failed: {str(e)}'}, status=500)


def order_status_history(request, order_id):
    """Get order status change history"""
    order = get_object_or_404(Order, id=order_id)
    
    # Check access
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if order.customer != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    history = order.status_history.all()
    
    data = []
    for entry in history:
        data.append({
            'from_status': entry.from_status,
            'to_status': entry.to_status,
            'notes': entry.notes,
            'changed_by': entry.changed_by.username if entry.changed_by else None,
            'created_at': entry.created_at.isoformat()
        })
    
    return JsonResponse({
        'order_id': str(order.id),
        'history': data
    })