from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/<uuid:product_id>/', views.product_detail, name='product_detail'),
    path('products/<uuid:product_id>/movements/', views.stock_movements, name='stock_movements'),
    path('stock/add/', views.add_stock, name='add_stock'),
    path('stock/reserve/', views.reserve_stock, name='reserve_stock'),
    path('stock/confirm/', views.confirm_reservation, name='confirm_reservation'),
    path('stock/release/', views.release_reservation, name='release_reservation'),
    path('admin/cleanup-expired/', views.cleanup_expired_reservations, name='cleanup_expired'),
]