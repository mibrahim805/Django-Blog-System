from django.core.cache import cache

from blog.models import Category, Notification


def notifications_badge(request):
    if request.user.is_authenticated:
        # Cache the unread count for 30 seconds to avoid frequent DB queries
        cache_key = f"unread_notifications_{request.user.id}"
        unread_count = cache.get(cache_key)
        if unread_count is None:
            unread_count = Notification.objects.filter(
                user=request.user, is_read=False
            ).count()
            cache.set(cache_key, unread_count, 30)
    else:
        unread_count = 0
    return {"unread_notifications_count": unread_count}


def navbar_context(request):
    """Provide categories and selected category IDs for navbar filter"""
    # Cache categories for 1 hour to avoid frequent DB queries
    cache_key = "all_categories_navbar"
    all_categories = cache.get(cache_key)
    if all_categories is None:
        all_categories = list(Category.objects.all().order_by("name"))
        cache.set(cache_key, all_categories, 3600)

    # Get selected categories from request
    selected_category_ids = []
    if request.GET:
        selected_category_ids = [
            int(id) for id in request.GET.getlist("categories") if id and id != "all"
        ]

    return {
        "all_categories": all_categories,
        "selected_category_ids": selected_category_ids,
    }
