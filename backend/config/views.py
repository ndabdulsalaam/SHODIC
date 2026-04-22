from django.http import JsonResponse

def health_check(request):
    """
    Lightweight endpoint for keep-alive pingers and health monitoring.
    """
    return JsonResponse({"status": "ok"})
