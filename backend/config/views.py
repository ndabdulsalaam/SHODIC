from django.http import JsonResponse, HttpResponseRedirect

def health_check(request):
    """
    Lightweight endpoint for keep-alive pingers and health monitoring.
    """
    return JsonResponse({"status": "ok"})


def root_redirect(request):
    """
    Redirect the root URL based on domain:
    - api.* or localhost → /admin/
    - everything else (fildah.com) → /home/
    """
    host = request.get_host().split(':')[0]  # strip port e.g. 127.0.0.1:8000
    if host.startswith('api.') or host in ('127.0.0.1', 'localhost'):
        return HttpResponseRedirect('/admin/')
    return HttpResponseRedirect('/home/')
