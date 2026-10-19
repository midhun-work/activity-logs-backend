"""The logs API (read only).

  GET logs/?page=&page_size=&from=YYYY-MM-DD&to=YYYY-MM-DD&tenant=&action=&model=&user_type=&q=
      a page of entries, newest first. `q` matches the user's name or phone, the description, the
      record's label (e.g. its phone) or the record id. Answers {results, total, page, pages, page_size}.
  GET logs/<id>/   one entry, with its old and new values.
  GET logs/meta/   the choices for the filters: actions, tenants and models seen in the log.

Who may call it comes from settings (LOGS["PERMISSION_CLASSES"]).
"""
from datetime import datetime, time, timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from . import conf
from .models import ActivityLog
from .serializers import ActivityLogDetailSerializer, ActivityLogListSerializer


def _day(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _number(value, default):
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


def _logs():
    return ActivityLog.objects.using(conf.get("DATABASE"))


class LogPermissionMixin:
    def get_permissions(self):
        return [permission() for permission in conf.permission_classes()]


class ActivityLogListView(LogPermissionMixin, APIView):
    def get(self, request):
        params = request.query_params
        rows = _logs().defer("old_data", "new_data")

        tz = timezone.get_current_timezone()
        start, end = _day(params.get("from")), _day(params.get("to"))
        if start:
            rows = rows.filter(created_at__gte=timezone.make_aware(datetime.combine(start, time.min), tz))
        if end:
            rows = rows.filter(created_at__lt=timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz))
        for name in ("tenant", "action", "model", "user_type"):
            value = (params.get(name) or "").strip()
            if value:
                rows = rows.filter(**{name: value})
        q = (params.get("q") or "").strip()
        if q:
            rows = rows.filter(
                Q(user_name__icontains=q) | Q(user_phone__icontains=q) | Q(description__icontains=q) | Q(object_label__icontains=q) | Q(object_id=q)
            )

        size = min(_number(params.get("page_size"), conf.get("PAGE_SIZE")), conf.get("MAX_PAGE_SIZE"))
        total = rows.count()
        pages = max(-(-total // size), 1)
        page = min(_number(params.get("page"), 1), pages)
        found = rows.order_by("-created_at", "-id")[(page - 1) * size : page * size]
        return Response(
            {
                "results": ActivityLogListSerializer(found, many=True).data,
                "total": total,
                "page": page,
                "pages": pages,
                "page_size": size,
            }
        )


class ActivityLogDetailView(LogPermissionMixin, APIView):
    def get(self, request, pk):
        return Response(ActivityLogDetailSerializer(get_object_or_404(_logs(), pk=pk)).data)


class ActivityLogMetaView(LogPermissionMixin, APIView):
    def get(self, request):
        logs = _logs().order_by()
        return Response(
            {
                "actions": [{"value": value, "label": label} for value, label in ActivityLog.Action.choices],
                "tenants": sorted(t for t in logs.values_list("tenant", flat=True).distinct() if t),
                "models": sorted(m for m in logs.values_list("model", flat=True).distinct() if m),
                "user_types": sorted(u for u in logs.values_list("user_type", flat=True).distinct() if u),
            }
        )
