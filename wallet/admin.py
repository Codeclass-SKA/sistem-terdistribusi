from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import TopUp


User = get_user_model()

admin.site.register(TopUp)
admin.site.register(User)
