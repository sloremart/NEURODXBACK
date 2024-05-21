from django.http import HttpResponse

class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Permitir solicitudes preflight (OPTIONS) solo si es necesario
        if request.method == "OPTIONS" and "HTTP_ACCESS_CONTROL_REQUEST_METHOD" in request.META:
            requested_method = request.META["HTTP_ACCESS_CONTROL_REQUEST_METHOD"]
            if requested_method in ("DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"):
                response = HttpResponse()
                response["Content-Length"] = "0"
                response["Access-Control-Max-Age"] = "86400"  # 24 horas
        
        # Configurar los encabezados CORS en todas las respuestas
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "DELETE, GET, OPTIONS, PATCH, POST, PUT"
        response["Access-Control-Allow-Headers"] = "accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with"
        
        return response