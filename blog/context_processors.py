from blog.models import Notification, Category


def notifications_badge(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    else:
        unread_count = 0
    return {"unread_notifications_count": unread_count}


def navbar_context(request):
    """Provide categories and selected category IDs for navbar filter"""
    all_categories = Category.objects.all().order_by("name")
    
    # Get selected categories from request
    selected_category_ids = []
    if request.GET:
        selected_category_ids = [int(id) for id in request.GET.getlist("categories") if id and id != "all"]
    
    return {
        "all_categories": all_categories,
        "selected_category_ids": selected_category_ids,
    }


