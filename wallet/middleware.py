from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.db import transaction
import json


class IdempotencyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip idempotency check for admin and GET requests
        # Don't skip for test client to allow idempotency testing
        if (request.path.startswith('/admin/') or 
            request.method != 'POST'):
            return None
            
        # Get idempotency key from various sources
        idempotency_key = (
            request.META.get('HTTP_IDEMPOTENCY_KEY') or
            request.POST.get('_idempotency_key')
        )
        
        # For JSON requests, try to parse the body
        if not idempotency_key and request.content_type == 'application/json':
            try:
                body = json.loads(request.body.decode('utf-8'))
                idempotency_key = body.get('_idempotency_key')
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        
        if not idempotency_key:
            return JsonResponse({'error': 'Idempotency-Key required'}, status=400)
        
        # Check cache for existing response
        cache_key = f"idmp:{request.method}:{request.path}:{idempotency_key}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return JsonResponse(cached_response)
        
        # Store key for later use
        request.idempotency_key = idempotency_key
        return None
    
    def process_response(self, request, response):
        # Cache successful responses
        if (hasattr(request, 'idempotency_key') and 
            response.status_code == 200 and 
            response.get('Content-Type', '').startswith('application/json')):
            
            cache_key = f"idmp:{request.method}:{request.path}:{request.idempotency_key}"
            try:
                response_data = json.loads(response.content.decode('utf-8'))
                cache.set(cache_key, response_data, 3600)  # 1 hour TTL
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        
        return response


class AtomicRequestMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip atomic for GET requests
        if request.method == 'GET':
            return None
            
        with transaction.atomic():
            return view_func(request, *view_args, **view_kwargs)