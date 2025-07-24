import uuid, json, hashlib
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse

TTL = 60 * 60  # 1 jam


class IdempotencyMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Mengecualikan path admin
        if request.path.startswith(reverse('admin:index')):
            return None

        if request.method != 'POST':
            return None

        key = request.headers.get('Idempotency-Key') or request.POST.get('_idempotency_key')
        if not key:
            return JsonResponse({'error': 'Idempotency-Key required'}, status=400)

        cache_key = f"idmp:{request.method}:{request.path}:{key}"
        cached = cache.get(cache_key)
        if cached:
            body, status = cached
            return HttpResponse(body, status=status, content_type='application/json')

        response = view_func(request, *view_args, **view_kwargs)

        if 200 <= response.status_code < 400:
            cache.set(cache_key, (response.content.decode(), response.status_code), TTL)
        return response
