import uuid
from django.db import models
from django.conf import settings


class TopUp(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.amount) + ' ' + str(self.user.email)


class TopUpLog(models.Model):
    topup = models.ForeignKey(TopUp, on_delete=models.CASCADE)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.message) + ' ' + str(self.topup.amount)

