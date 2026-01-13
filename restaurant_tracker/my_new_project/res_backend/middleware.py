"""
Middleware to log all incoming requests for debugging
"""
import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    """Log all incoming HTTP requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log the request
        print(f"\n{'='*60}")
        print(f"DEBUG: Incoming Request")
        print(f"  Method: {request.method}")
        print(f"  Path: {request.path}")
        print(f"  Full URL: {request.build_absolute_uri()}")
        print(f"  Remote Address: {request.META.get('REMOTE_ADDR', 'N/A')}")
        print(f"  HTTP Host: {request.META.get('HTTP_HOST', 'N/A')}")
        print(f"  User Agent: {request.META.get('HTTP_USER_AGENT', 'N/A')}")
        print(f"  GET params: {dict(request.GET)}")
        print(f"{'='*60}\n")
        
        response = self.get_response(request)
        
        # Log the response
        print(f"DEBUG: Response Status: {response.status_code}")
        print(f"{'='*60}\n")
        
        return response

