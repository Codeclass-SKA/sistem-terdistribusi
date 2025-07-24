import uuid
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import TopUp


def topup_form(request):
    return render(request, 'wallet/topup.html', {'uuid': uuid.uuid4()})


@csrf_exempt  # demo saja, prod pakai CSRF
def topup_submit(request):
    amount = int(request.POST.get('amount', 0))
    if amount <= 0:
        return JsonResponse({'error': 'invalid amount'}, status=400)
    TopUp.objects.create(user_id=1, amount=amount)  # hardcode user
    return JsonResponse({'detail': 'topup ok', 'amount': amount})