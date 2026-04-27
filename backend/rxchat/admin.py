from django.contrib import admin, messages
from django.core.management import call_command
from django.http import HttpRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import path, reverse

from rxchat.ingestion.nafdac_scraper import NAFDAC_CATEGORIES
from rxchat.ingestion.source_status import source_status_rows
from rxchat.ingestion.update_checker import check_all_sources

from .models import (
    Conversation,
    DrugChunk,
    IngestionLog,
    Message,
    RawSourceData,
    ScrapeProgress,
    SourceFileUpload,
)


class MessageInline(admin.TabularInline):
    model = Message
    readonly_fields = ['id', 'role', 'content', 'created_at']
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'session_key', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['title']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role', 'short_content', 'created_at']
    list_filter = ['role', 'created_at']

    def short_content(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    short_content.short_description = 'Content'


def can_run_ingestion(user) -> bool:
    return bool(user.is_active and (user.is_superuser or (user.is_staff and user.has_perm("rxchat.can_run_ingestion"))))


def ingestion_admin_view(request: HttpRequest):
    if not can_run_ingestion(request.user):
        return HttpResponseForbidden("You do not have permission to run ingestion tasks.")

    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            if action == "check_sources":
                check_all_sources()
                messages.success(request, "Source status checked.")
            elif action == "upload_source_file":
                source = request.POST.get("source", "")
                file = request.FILES.get("file")
                if not source or not file:
                    raise ValueError("Choose a source and file to upload.")
                upload = SourceFileUpload.objects.create(
                    source=source,
                    file=file,
                    description=request.POST.get("description", ""),
                )
                _queue_task("ingest_drugs", "--source", source)
                messages.success(request, f"Uploaded {upload.file.name}. Processing task queued.")
            elif action == "setup_schedules":
                _queue_task("setup_ingestion_schedules")
                messages.success(request, "Task queued - check Django Q task results.")
            else:
                command_args = _command_args_for_action(action, request)
                _queue_task(*command_args)
                messages.success(request, "Task queued - check Django Q successful or failed tasks for results.")
        except Exception as exc:
            messages.error(request, f"Could not queue task: {exc}")
        return redirect(reverse("admin:rxchat_ingestion"))

    context = {
        **admin.site.each_context(request),
        "title": "Data Ingestion",
        "categories": NAFDAC_CATEGORIES,
        "source_rows": source_status_rows(),
        "manual_sources": [
            ("neml", "NEML"),
            ("nhia_stg", "NHIA STG"),
            ("who", "WHO EML"),
            ("nnmda", "NNMDA"),
            ("emdex", "EMDEX"),
        ],
    }
    return render(request, "admin/rxchat/ingestion.html", context)


def _queue_task(*command_args: str) -> None:
    try:
        from django_q.tasks import async_task  # noqa: PLC0415
    except ImportError:
        # Local fallback keeps the admin usable before django-q2 is installed.
        call_command(*command_args)
        return
    async_task("django.core.management.call_command", *command_args)


def _command_args_for_action(action: str, request: HttpRequest) -> tuple[str, ...]:
    mapping = {
        "scrape_nafdac_full": ("scrape_nafdac",),
        "scrape_nafdac_resume": ("scrape_nafdac", "--resume"),
        "pull_openfda_curated": ("pull_openfda", "--curated"),
        "pull_openfda_full": ("pull_openfda",),
        "ingest_all": ("ingest_drugs", "--all"),
    }
    if action == "scrape_nafdac_category":
        category = request.POST.get("category")
        if not category:
            raise ValueError("Choose a NAFDAC category.")
        return ("scrape_nafdac", "--category", category, "--resume")
    if action not in mapping:
        raise ValueError("Unknown ingestion action.")
    return mapping[action]


_original_get_urls = admin.site.get_urls


def _get_urls():
    custom = [
        path("rxchat/ingestion/", admin.site.admin_view(ingestion_admin_view), name="rxchat_ingestion"),
    ]
    return custom + _original_get_urls()


admin.site.get_urls = _get_urls


@admin.register(RawSourceData)
class RawSourceDataAdmin(admin.ModelAdmin):
    list_display = ["source", "source_id", "file_name", "created_at", "updated_at"]
    list_filter = ["source", "created_at", "updated_at"]
    search_fields = ["source_id", "file_name", "raw_data"]
    readonly_fields = ["created_at", "updated_at"]

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()


@admin.register(DrugChunk)
class DrugChunkAdmin(admin.ModelAdmin):
    list_display = ["raw_source", "chunk_index", "source", "text_preview", "qdrant_point_id", "embedded_at"]
    list_filter = ["raw_source__source", "embedded_at", "created_at"]
    search_fields = ["text", "metadata", "raw_source__source_id"]
    readonly_fields = ["created_at", "updated_at", "embedded_at"]

    def source(self, obj):
        return obj.raw_source.source

    def text_preview(self, obj):
        return obj.text[:120] + "..." if len(obj.text) > 120 else obj.text


@admin.register(SourceFileUpload)
class SourceFileUploadAdmin(admin.ModelAdmin):
    list_display = ["source", "file", "processed", "uploaded_at"]
    list_filter = ["source", "processed", "uploaded_at"]
    search_fields = ["file", "description"]
    actions = ["process_uploads"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change or obj.processed:
            return
        _queue_task("ingest_drugs", "--source", obj.source)
        self.message_user(
            request,
            "Upload saved. Processing task queued - check Django Q task results.",
            messages.SUCCESS,
        )

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()

    @admin.action(description="Process selected uploads")
    def process_uploads(self, request, queryset):
        sources = sorted(set(queryset.values_list("source", flat=True)))
        for source in sources:
            _queue_task("ingest_drugs", "--source", source)
        self.message_user(request, f"Queued processing for {len(sources)} source(s).", messages.SUCCESS)


@admin.register(IngestionLog)
class IngestionLogAdmin(admin.ModelAdmin):
    list_display = ["source", "action", "status", "created_at"]
    list_filter = ["source", "action", "status", "created_at"]
    search_fields = ["details"]
    readonly_fields = ["source", "action", "status", "details", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ScrapeProgress)
class ScrapeProgressAdmin(admin.ModelAdmin):
    list_display = ["source", "last_run", "updated_at"]
    list_filter = ["source", "last_run", "updated_at"]
    readonly_fields = ["source", "progress_data", "last_run", "updated_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
