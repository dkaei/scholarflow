from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    response = render(request, "notifications/list.html", {"notifications": notifications})
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@login_required
def notification_open(request, pk: int):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect(notification.link or "/")


@login_required
@require_POST
def notification_delete(request, pk: int):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()
    return redirect("notification-list")
