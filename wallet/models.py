import uuid
from django.db import models
from django.contrib.auth.models import User


class TopUp(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.amount) + ' ' + str(self.user.email)
