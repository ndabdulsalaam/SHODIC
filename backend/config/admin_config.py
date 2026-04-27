"""
Fildah admin configuration.

The admin remains one global staff surface, but the header lets staff narrow
the index to a product view such as RxChat.
"""
from django.contrib import admin
from django.urls import NoReverseMatch, reverse


ADMIN_PROJECT_SESSION_KEY = "fildah_admin_project"
ADMIN_PROJECT_FIDLAH = "fildah"
ADMIN_PROJECT_RXCHAT = "rxchat"
ADMIN_PROJECTS = [
    {"slug": ADMIN_PROJECT_FIDLAH, "name": "Fildah"},
    {"slug": ADMIN_PROJECT_RXCHAT, "name": "RxChat"},
]
ADMIN_PRODUCT_APP_LABELS = {
    ADMIN_PROJECT_RXCHAT: {"rxchat"},
}


admin.site.site_header = "Fildah Administration"
admin.site.site_title = "Fildah Admin"
admin.site.index_title = "Dashboard"


_original_each_context = admin.site.each_context
_original_get_app_list = admin.site.get_app_list


def _admin_index_url(project_slug):
    try:
        return f"{reverse('admin:index')}?project={project_slug}"
    except NoReverseMatch:
        return f"/admin/?project={project_slug}"


def _selected_project(request):
    requested_project = request.GET.get("project")
    project_slugs = {project["slug"] for project in ADMIN_PROJECTS}

    if requested_project in project_slugs:
        request.session[ADMIN_PROJECT_SESSION_KEY] = requested_project
        return requested_project

    if request.path_info.startswith("/admin/rxchat/"):
        return ADMIN_PROJECT_RXCHAT

    session_project = request.session.get(ADMIN_PROJECT_SESSION_KEY)
    if session_project in project_slugs:
        return session_project

    return ADMIN_PROJECT_FIDLAH


def _project_choices(selected_project):
    return [
        {
            **project,
            "url": _admin_index_url(project["slug"]),
            "is_active": project["slug"] == selected_project,
        }
        for project in ADMIN_PROJECTS
    ]


def _user_can_run_rxchat_ingestion(request):
    user = request.user
    return bool(
        user.is_active
        and (user.is_superuser or (user.is_staff and user.has_perm("rxchat.can_run_ingestion")))
    )


def _rxchat_ingestion_url():
    try:
        return reverse("admin:rxchat_ingestion")
    except NoReverseMatch:
        return "/admin/rxchat/ingestion/"


def _append_rxchat_custom_links(app_list, request):
    if not _user_can_run_rxchat_ingestion(request):
        return app_list

    rxchat_app = next((app for app in app_list if app.get("app_label") == "rxchat"), None)
    if rxchat_app is None:
        rxchat_app = {
            "name": "RxChat",
            "app_label": "rxchat",
            "app_url": "/admin/rxchat/",
            "has_module_perms": True,
            "models": [],
        }
        app_list.append(rxchat_app)

    if any(model.get("object_name") == "RxChatIngestion" for model in rxchat_app["models"]):
        return app_list

    rxchat_app["models"].append({
        "name": "Data ingestion",
        "object_name": "RxChatIngestion",
        "perms": {"add": False, "change": True, "delete": False, "view": True},
        "admin_url": _rxchat_ingestion_url(),
        "add_url": None,
        "view_only": False,
    })
    return app_list


def fildah_each_context(request):
    context = _original_each_context(request)
    selected_project = _selected_project(request)
    context.update({
        "fildah_selected_project": selected_project,
        "fildah_admin_projects": _project_choices(selected_project),
    })
    return context


def fildah_get_app_list(request, app_label=None):
    app_list = _original_get_app_list(request, app_label)
    app_list = _append_rxchat_custom_links(app_list, request)

    selected_project = _selected_project(request)
    allowed_labels = ADMIN_PRODUCT_APP_LABELS.get(selected_project)
    if allowed_labels and app_label is None:
        app_list = [
            app
            for app in app_list
            if app.get("app_label") in allowed_labels
        ]

    return app_list


admin.site.each_context = fildah_each_context
admin.site.get_app_list = fildah_get_app_list
