"""
Temporary diagnostic view – DELETE after debugging static files.
Visit /debug-static/ to see WhiteNoise + static-file state on Render.
"""
import os
from pathlib import Path
from django.http import JsonResponse
from django.conf import settings


def debug_static_view(request):
    static_root = str(settings.STATIC_ROOT)
    data = {
        "DEBUG": settings.DEBUG,
        "STATIC_URL": settings.STATIC_URL,
        "STATIC_ROOT": static_root,
        "STATIC_ROOT_exists": os.path.exists(static_root),
        "STORAGES": settings.STORAGES,
        "WHITENOISE_USE_FINDERS": getattr(settings, "WHITENOISE_USE_FINDERS", "NOT SET"),
        "WHITENOISE_MANIFEST_STRICT": getattr(settings, "WHITENOISE_MANIFEST_STRICT", "NOT SET"),
        "MIDDLEWARE": settings.MIDDLEWARE,
    }

    # Check what's actually in STATIC_ROOT
    if os.path.exists(static_root):
        root_contents = os.listdir(static_root)
        data["STATIC_ROOT_contents"] = root_contents
        # Check if admin dir exists
        admin_dir = os.path.join(static_root, "admin")
        if os.path.exists(admin_dir):
            data["admin_dir_exists"] = True
            admin_css = os.path.join(admin_dir, "css")
            if os.path.exists(admin_css):
                data["admin_css_files"] = os.listdir(admin_css)[:10]
        else:
            data["admin_dir_exists"] = False
        # Check manifest
        manifest = os.path.join(static_root, "staticfiles.json")
        data["manifest_exists"] = os.path.exists(manifest)
        if os.path.exists(manifest):
            data["manifest_size_bytes"] = os.path.getsize(manifest)
    else:
        data["STATIC_ROOT_contents"] = "DIRECTORY DOES NOT EXIST"

    # Check CWD and BASE_DIR
    data["CWD"] = os.getcwd()
    data["BASE_DIR"] = str(settings.BASE_DIR)

    # Check WhiteNoise internals
    try:
        from whitenoise.middleware import WhiteNoiseMiddleware
        data["whitenoise_imported"] = True
    except ImportError:
        data["whitenoise_imported"] = False

    return JsonResponse(data, json_dumps_params={"indent": 2})
