from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('create/', views.create_order, name='create_order'),
    path('<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('<uuid:order_id>/history/', views.order_status_history, name='order_history'),
    path('user/orders/', views.user_orders, name='user_orders'),
    path('payment/process/', views.process_payment, name='process_payment'),
    path('cancel/', views.cancel_order, name='cancel_order'),
    path('admin/update-status/', views.update_order_status, name='update_status'),
]