from django.urls import path
from . import views


urlpatterns = [
    path('', views.topup_form, name='topup_form'),
    path('submit/', views.topup_submit, name='topup_submit'),
]
