from django.shortcuts import render
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from .models import TopUp, TopUpLog
from django.contrib.auth import get_user_model

import uuid


def topup_form(request):
    return render(request, 'wallet/topup.html', {'uuid': uuid.uuid4()})


@transaction.atomic
def topup_submit(request):
    amount = int(request.POST.get('amount', 0))
    if amount <= 0:
        return JsonResponse({'error': 'invalid amount'}, status=400)

    User = get_user_model()
    user = User.objects.first()  # Ambil user pertama yang ada
    if not user:
        return JsonResponse({'error': 'no user available'}, status=400)

    # Mulai transaksi
    topup = TopUp.objects.create(user=user, amount=amount)

    # Catat log
    TopUpLog.objects.create(topup=topup, message=f"Top-up of {amount} for user {user.username}")

    # Perbarui saldo user menggunakan F() expression
    user.balance = F('balance') + amount
    user.save(update_fields=['balance'])

    # Refresh dari database untuk mendapatkan nilai terkini
    user.refresh_from_db()

    return JsonResponse({'detail': 'topup ok', 'amount': amount, 'new_balance': user.balance})
