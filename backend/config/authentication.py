from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    DRF's SessionAuthentication enforces CSRF even when views
    are decorated with @csrf_exempt. This subclass skips that check
    so our API endpoints work from a cross-origin frontend.
    """

    def enforce_csrf(self, request):
        return  # Skip CSRF — our API uses session cookies + CORS instead
