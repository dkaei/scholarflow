from .models import Notification


def unread_notifications(request):
    if not request.user.is_authenticated:
        return {"notif_unread_count": 0}
    return {
        "notif_unread_count": Notification.objects.filter(user=request.user, is_read=False).count(),
    }
