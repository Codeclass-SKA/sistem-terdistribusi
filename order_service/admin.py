from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory, PaymentRecord


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'customer__username', 'customer__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['customer']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'quantity', 'unit_price', 'subtotal']
    list_filter = ['order__status', 'order__created_at']
    search_fields = ['product_name', 'order__id']
    readonly_fields = ['id']
    raw_id_fields = ['order']


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'from_status', 'to_status', 'changed_by', 'created_at']
    list_filter = ['from_status', 'to_status', 'created_at']
    search_fields = ['order__id', 'notes']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['order', 'changed_by']


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ['order', 'payment_type', 'amount', 'status', 'created_at']
    list_filter = ['payment_type', 'status', 'created_at']
    search_fields = ['order__id', 'transaction_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['order']