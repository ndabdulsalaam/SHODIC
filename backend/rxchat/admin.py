import json

from django.contrib import admin, messages
from django.core.management import call_command
from django.http import HttpRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from rxchat.ingestion.nafdac_scraper import NAFDAC_CATEGORIES
from rxchat.ingestion.source_status import source_status_rows
from rxchat.ingestion.update_checker import check_all_sources

from .models import (
    CleanData,
    Conversation,
    DrugChunk,
    Message,
    RawData,
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
    return bool(
        user.is_active
        and (user.is_superuser or (user.is_staff and user.has_perm("rxchat.can_run_ingestion")))
    )


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
                upload = RawData.objects.create(
                    source=source,
                    file=file,
                    description=request.POST.get("description", ""),
                )
                _queue_task("parse_data", "--source", source)
                messages.success(
                    request,
                    f"Uploaded {upload.file.name}. "
                    "Parse task queued — review CleanData records, then run 'ingest_drugs'.",
                )
            elif action == "parse_all":
                _queue_task("parse_data", "--all")
                messages.success(request, "parse_data --all queued.")
            elif action == "seed_qdrant":
                _queue_task("seed_qdrant")
                messages.success(request, "seed_qdrant queued.")
            elif action == "setup_schedules":
                _queue_task("setup_ingestion_schedules")
                messages.success(request, "Task queued — check Django Q task results.")
            else:
                command_args = _command_args_for_action(action, request)
                _queue_task(*command_args)
                messages.success(request, "Task queued — check Django Q successful or failed tasks for results.")
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


# ---------------------------------------------------------------------------
# RawData admin
# ---------------------------------------------------------------------------

@admin.register(RawData)
class RawDataAdmin(admin.ModelAdmin):
    list_display = ["source", "file", "description", "uploaded_at"]
    list_filter = ["source", "uploaded_at"]
    search_fields = ["file", "description"]
    readonly_fields = ["uploaded_at"]

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()


# ---------------------------------------------------------------------------
# CleanData admin — two-step review
# ---------------------------------------------------------------------------

@admin.register(CleanData)
class CleanDataAdmin(admin.ModelAdmin):
    list_display = ["source", "source_id", "status_badge", "file_name", "updated_at"]
    list_filter = ["source", "status", "updated_at"]
    search_fields = ["source_id", "file_name", "raw_text"]
    readonly_fields = ["source", "source_id", "file_name", "raw_id", "status", "created_at", "updated_at", "json_preview"]
    fields = [
        "source", "source_id", "file_name", "raw",
        "status", "created_at", "updated_at",
        "raw_text",
        "json_preview",
        "data",
    ]
    actions = ["accept_selected", "reset_to_draft"]

    def get_readonly_fields(self, request, obj=None):
        ro = list(self.readonly_fields)
        if obj and obj.status != CleanData.STATUS_DRAFT:
            ro.append("raw_text")
        return ro

    def status_badge(self, obj):
        colours = {
            CleanData.STATUS_DRAFT: "#888",
            CleanData.STATUS_ACCEPTED: "#0a0",
            CleanData.STATUS_CHUNKED: "#00a",
        }
        colour = colours.get(obj.status, "#888")
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colour,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def json_preview(self, obj):
        """Read-only pretty-printed JSON preview of what Accept will produce."""
        from rxchat.models import _text_to_json  # noqa: PLC0415
        if obj.status == CleanData.STATUS_DRAFT and obj.raw_text:
            preview = _text_to_json(obj.source, obj.raw_text)
        else:
            preview = obj.data or {}
        return format_html(
            '<pre style="max-height:400px;overflow:auto;background:#f5f5f5;padding:8px">{}</pre>',
            json.dumps(preview, indent=2, ensure_ascii=False),
        )
    json_preview.short_description = "JSON Preview (auto-generated)"

    @admin.action(description="✅ Accept selected — convert raw_text → JSON")
    def accept_selected(self, request, queryset):
        accepted = 0
        for obj in queryset.filter(status=CleanData.STATUS_DRAFT):
            obj.accept()
            accepted += 1
        self.message_user(
            request,
            f"{accepted} record(s) accepted. Run 'ingest_drugs' to create chunks.",
            messages.SUCCESS,
        )

    @admin.action(description="↩️ Reset to draft — clear JSON, re-edit raw_text")
    def reset_to_draft(self, request, queryset):
        reset = 0
        for obj in queryset:
            obj.reset_to_draft()
            reset += 1
        self.message_user(request, f"{reset} record(s) reset to draft.", messages.SUCCESS)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()


# ---------------------------------------------------------------------------
# DrugChunk admin
# ---------------------------------------------------------------------------

@admin.register(DrugChunk)
class DrugChunkAdmin(admin.ModelAdmin):
    list_display = ["clean_data", "chunk_index", "source", "text_preview", "qdrant_point_id", "embedded_at"]
    list_filter = ["clean_data__source", "embedded_at", "created_at"]
    search_fields = ["text", "metadata", "clean_data__source_id"]
    readonly_fields = ["created_at", "updated_at", "embedded_at"]

    def source(self, obj):
        return obj.clean_data.source

    def text_preview(self, obj):
        return obj.text[:120] + "..." if len(obj.text) > 120 else obj.text
