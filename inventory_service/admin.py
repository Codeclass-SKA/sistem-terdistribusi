from django.contrib import admin
from .models import Product, StockMovement, StockReservation


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock_quantity', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'quantity', 'reference_id', 'created_at', 'created_by']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['product__name', 'reference_id', 'notes']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['product', 'created_by']


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'order_id', 'expires_at', 'created_at']
    list_filter = ['expires_at', 'created_at']
    search_fields = ['product__name', 'order_id']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['product']