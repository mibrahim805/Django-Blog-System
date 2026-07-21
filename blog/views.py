from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from ckeditor_uploader.views import upload
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from BlogSystem2 import settings

from .filters import PostFilter
from .forms import CommentForm, InterestForm, PostCreateForm, RegistrationForm
from .models import (
    Category,
    Comment,
    CustomUser,
    Follow,
    Like,
    Notification,
    NotInterestedPost,
    Post,
    Profile,
    SavedPost,
)


@login_required
def custom_upload(request):
    return upload(request)


def create_and_push_notification(*, user, post, sender, message):
    notification = Notification.objects.create(
        user=user, post=post, sender=sender, message=message
    )
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {
            "type": "send_notification",
            "message": message,
            "notification_id": notification.id,
        },
    )
    return notification


def build_profile_context(profile_user, current_user=None):
    from blog.models import Follow

    profile, _ = Profile.objects.get_or_create(user=profile_user)
    recent_posts = (
        Post.objects.filter(author=profile_user, is_published=True)
        .select_related("author")
        .prefetch_related("categories")
        .order_by("-created_at")[:6]
    )
    followers = CustomUser.objects.filter(
        following_users__following=profile_user
    ).distinct()
    following = CustomUser.objects.filter(
        followed_by_users__follower=profile_user
    ).distinct()

    is_following = False
    if current_user and current_user.is_authenticated:
        is_following = Follow.objects.filter(
            follower=current_user, following=profile_user
        ).exists()

    not_interested_entries = (
        NotInterestedPost.objects.filter(user=profile_user)
        .select_related("post", "post__author")
        .order_by("-created_at")
    )
    return {
        "profile_user": profile_user,
        "profile": profile,
        "user_posts": Post.objects.filter(
            author=profile_user, is_published=True
        ).count(),
        "user_likes": Like.objects.filter(
            post__author=profile_user, comment__isnull=True
        ).count(),
        "user_comments": Comment.objects.filter(user=profile_user).count(),
        "interests": profile.interested_in.all(),
        "recent_posts": recent_posts,
        "followers": followers,
        "following": following,
        "followers_count": followers.count(),
        "following_count": following.count(),
        "is_following": is_following,
        "followers_list": Follow.objects.filter(following=profile_user).select_related(
            "follower"
        ),
        "following_list": Follow.objects.filter(follower=profile_user).select_related(
            "following"
        ),
        "not_interested_entries": not_interested_entries,
        "not_interested_count": not_interested_entries.count(),
    }


def build_comment_tree(comments):
    """Attach ordered children to each comment and return only root comments."""
    comment_list = list(comments)
    comments_by_id = {comment.id: comment for comment in comment_list}
    roots = []

    for comment in comment_list:
        comment.display_replies = []

    for comment in comment_list:
        parent = comments_by_id.get(comment.parent_comment_id)
        if parent is not None and parent.post_id == comment.post_id:
            parent.display_replies.append(comment)
        else:
            roots.append(comment)

    return roots


def prepare_posts_with_comment_trees(posts):
    """Materialize posts and attach their full comment trees without N+1 queries."""
    post_list = list(posts)
    comments_by_post = {post.id: [] for post in post_list}
    comments = (
        Comment.objects.filter(post_id__in=comments_by_post)
        .select_related("user")
        .order_by("created_at", "id")
    )

    for comment in comments:
        comments_by_post[comment.post_id].append(comment)

    for post in post_list:
        post_comments = comments_by_post[post.id]
        post.comment_count = len(post_comments)
        post.comment_tree = build_comment_tree(post_comments)

    return post_list


def user_register_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("blog:home")
    else:
        form = RegistrationForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def post_list_view(request):
    hidden_post_ids = NotInterestedPost.objects.filter(user=request.user).values_list(
        "post_id", flat=True
    )
    queryset = (
        Post.objects.filter(is_published=True)
        .exclude(id__in=hidden_post_ids)
        .order_by("-created_at")
    )
    filter = PostFilter(request.GET, queryset=queryset)
    posts = prepare_posts_with_comment_trees(filter.qs)

    all_categories = Category.objects.order_by("name")
    selected_category_ids = []
    for category_id in request.GET.getlist("categories"):
        if not category_id or category_id == "all":
            continue
        try:
            selected_category_ids.append(int(category_id))
        except (TypeError, ValueError):
            continue
    liked_posts = Like.objects.filter(
        user=request.user, comment__isnull=True
    ).values_list("post_id", flat=True)
    liked_comments = Like.objects.filter(
        user=request.user, post__isnull=True, comment__isnull=False
    ).values_list("comment_id", flat=True)
    saved_posts = SavedPost.objects.filter(user=request.user).values_list(
        "post_id", flat=True
    )
    context = {
        "posts": posts,
        "filter": filter,
        "all_categories": all_categories,
        "selected_category_ids": selected_category_ids,
        "liked_post_ids": list(liked_posts),
        "liked_comment_ids": list(liked_comments),
        "saved_post_ids": list(saved_posts),
        "not_interested_form": NotInterestedPost.objects.filter(user=request.user),
    }
    return render(request, "post/post_list.html", context)


# @login_required
def send_email(request, post):
    users = CustomUser.objects.filter(
        is_active=True,
        following_users__following=request.user,
        followed_by_users__follower=request.user,
    ).exclude(id=request.user.id)
    for user in users:
        subject = f"New Post Published: {post.title}"
        message = f"Dear {user.username},\n\nWe are pleased to inform you that a new post has been published on our website by {request.user.username}.\n\nTitle: {post.title}\n\nBest regards,\nThe Blog Team"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])


@login_required
def post_create_view(request):
    if request.method == "POST":
        # print("form valid")
        form = PostCreateForm(request.POST, request.FILES)
        if form.is_valid():
            print("form valid")
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()

            selected_categories = form.cleaned_data.get("category")
            if selected_categories is not None:
                post.categories.set(selected_categories)
            if post.is_published:
                send_email(request, post)
                users = CustomUser.objects.exclude(id=request.user.id)
                for user in users:
                    create_and_push_notification(
                        user=user,
                        post=post,
                        sender=request.user,
                        message=f"{request.user.username} published a new post.",
                    )
            return redirect("blog:my_posts")
    else:
        form = PostCreateForm()
    return render(request, "post/post_create.html", {"form": form})


@login_required
def post_update_view(request, pk):
    post = Post.objects.get(id=pk)
    if request.method == "POST":
        form = PostCreateForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            selected_categories = form.cleaned_data.get("category")
            if selected_categories is not None:
                post.categories.set(selected_categories)
            if post.is_published:
                users = CustomUser.objects.exclude(id=request.user.id)
                for user in users:
                    create_and_push_notification(
                        user=user,
                        post=post,
                        sender=request.user,
                        message=f"{request.user.username} updated a post.",
                    )
            return redirect("blog:my_posts")
    else:
        form = PostCreateForm(instance=post)
    return render(request, "post/post_create.html", {"form": form, "post": post})


@login_required
def post_detail_view(request, pk):
    post = Post.objects.get(id=pk)
    comments = list(
        Comment.objects.filter(post=post).select_related("user").order_by("created_at")
    )
    comment_tree = build_comment_tree(comments)
    liked_comment_ids = Like.objects.filter(
        user=request.user,
        post__isnull=True,
        comment__post=post,
    ).values_list("comment_id", flat=True)
    return render(
        request,
        "post/post_detail.html",
        {
            "post": post,
            "comments": comments,
            "comment_tree": comment_tree,
            "comment_count": len(comments),
            "liked_comment_ids": list(liked_comment_ids),
        },
    )


@login_required
def post_delete_view(request, pk):
    post = Post.objects.get(id=pk)
    post.delete()
    return redirect("blog:my_posts")


@login_required
def comment_createView(request, post_id):
    post = Post.objects.get(id=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.is_approved = False
            comment.save()
            if post.author != request.user:
                create_and_push_notification(
                    user=post.author,
                    post=post,
                    sender=request.user,
                    message=f"{request.user.username} commented on your post.",
                )

            if request.headers.get(
                "X-Requested-With"
            ) == "XMLHttpRequest" or request.POST.get("ajax"):
                return JsonResponse(
                    {
                        "success": True,
                        "comment_id": comment.id,
                        "message": "Comment posted successfully",
                    }
                )
            return redirect("blog:home")


@login_required
def comment_edit_view(request, comment_id):
    if request.method == "POST":
        comment = get_object_or_404(Comment, id=comment_id, user=request.user)
        new_content = request.POST.get("content")
        if new_content:
            comment.content = new_content
            comment.save()
            return redirect("blog:home")


@login_required
@require_POST
def comment_delete_view(request, comment_id):
    is_ajax = request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest" or request.POST.get("ajax")
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    post_id = comment.post_id
    deleted_comment_id = comment.id
    comment.delete()

    if is_ajax:
        return JsonResponse(
            {
                "success": True,
                "comment_id": deleted_comment_id,
                "post_id": post_id,
                "post_comment_count": Comment.objects.filter(post_id=post_id).count(),
            }
        )

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("blog:home")


@login_required
@require_POST
def comment_like_view(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    like, created = Like.objects.get_or_create(
        user=request.user,
        comment=comment,
        defaults={"post": None},
    )
    if created:
        is_liked = True
        if comment.user != request.user:
            create_and_push_notification(
                user=comment.user,
                post=comment.post,
                sender=request.user,
                message=f"{request.user.username} liked your comment.",
            )
    else:
        like.delete()
        is_liked = False

    like_count = Like.objects.filter(
        comment=comment,
        post__isnull=True,
    ).count()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.POST.get(
        "ajax"
    ):
        return JsonResponse(
            {
                "success": True,
                "is_liked": is_liked,
                "like_count": like_count,
            }
        )
    return redirect("blog:home")


@login_required
@require_POST
def comment_reply_view(request, comment_id):
    parent_comment = get_object_or_404(Comment, id=comment_id)
    form = CommentForm(request.POST)
    is_ajax = request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest" or request.POST.get("ajax")

    if not form.is_valid():
        if is_ajax:
            return JsonResponse(
                {"success": False, "errors": form.errors.get_json_data()}, status=400
            )
        return redirect("blog:post_detail", pk=parent_comment.post_id)

    comment = form.save(commit=False)
    comment.user = request.user
    comment.post = parent_comment.post
    comment.parent_comment = parent_comment
    comment.save()

    if parent_comment.user != request.user:
        create_and_push_notification(
            user=parent_comment.user,
            post=parent_comment.post,
            sender=request.user,
            message=f"{request.user.username} replied to your comment.",
        )

    if is_ajax:
        comment.display_replies = []
        html = render_to_string(
            "comments/_thread_node.html",
            {"comment": comment, "liked_comment_ids": []},
            request=request,
        )
        return JsonResponse(
            {
                "success": True,
                "comment_id": comment.id,
                "parent_id": parent_comment.id,
                "post_id": parent_comment.post_id,
                "reply_count": parent_comment.replies.count(),
                "post_comment_count": parent_comment.post.comments.count(),
                "html": html,
                "message": "Reply posted successfully",
            }
        )
    return redirect("blog:post_detail", pk=parent_comment.post_id)


@login_required
@require_POST
def like_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(
        user=request.user,
        post=post,
        comment=None,
    )
    if created:
        is_liked = True
        if post.author != request.user:
            create_and_push_notification(
                user=post.author,
                post=post,
                sender=request.user,
                message=f"{request.user.username} liked your post.",
            )
    else:
        like.delete()
        is_liked = False

    like_count = Like.objects.filter(post=post, comment__isnull=True).count()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.POST.get(
        "ajax"
    ):
        return JsonResponse(
            {
                "success": True,
                "is_liked": is_liked,
                "like_count": like_count,
            }
        )
    return redirect("blog:home")


@login_required
def notifications_list_view(request):
    new_notifications = Notification.objects.filter(
        user=request.user, is_read=False
    ).order_by("-created_at")
    old_notifications = Notification.objects.filter(
        user=request.user, is_read=True
    ).order_by("-created_at")
    return render(
        request,
        "notifications/list.html",
        {
            "new_notifications": new_notifications,
            "old_notifications": old_notifications,
        },
    )


@login_required
def unread_notifications_count_view(request):
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"unread_count": unread_count})


@login_required
def mark_as_read_view(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    notification.is_read = True
    notification.save()
    return redirect("blog:notifications_list")


@login_required
def mark_all_as_read_view(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("blog:notifications_list")


@login_required
def select_interest_view(request):
    if request.method == "Post":
        form = InterestForm(request.POST)
        if form.is_valid():
            interests = form.cleaned_data["interests"]
            profile = request.user.profile
            profile.interested_in.set(interests)
            return redirect("blog:home")
    else:
        form = InterestForm({"interests": request.user.profile.interested_in.all()})
    return render(request, "interest/select_interest.html", {"form": form})


@login_required
def my_posts_view(request):
    posts = prepare_posts_with_comment_trees(
        Post.objects.filter(author=request.user).order_by("-created_at")
    )
    liked_comment_ids = Like.objects.filter(
        user=request.user,
        post__isnull=True,
        comment__post__in=posts,
    ).values_list("comment_id", flat=True)
    return render(
        request,
        "post/my_posts.html",
        {"posts": posts, "liked_comment_ids": list(liked_comment_ids)},
    )


@login_required
def my_profile_view(request):
    context = build_profile_context(request.user, request.user)
    return render(request, "profile/my_profile.html", context)


@login_required
def other_user_profile_view(request, user_id):
    other_user = get_object_or_404(CustomUser, id=user_id)
    context = build_profile_context(other_user, request.user)
    context["other_user"] = other_user
    context["is_own_profile"] = other_user == request.user
    return render(request, "profile/other_profile.html", context)


@login_required
def user_follow_view(request, user_id):
    follower = request.user
    following = get_object_or_404(CustomUser, id=user_id)
    follow = Follow.objects.filter(follower=follower, following=following).first()
    if follow:
        follow.delete()
    else:
        Follow.objects.create(follower=follower, following=following)
        if following != request.user:
            create_and_push_notification(
                user=following,
                post=None,
                sender=request.user,
                message=f"{request.user.username} started following you.",
            )
            if request.headers.get(
                "X-Requested-With"
            ) == "XMLHttpRequest" or request.POST.get("ajax"):
                return JsonResponse(
                    {"success": True, "message": "User followed successfully"}
                )
    return redirect("blog:other_profile", user_id=user_id)


@login_required
def follower_list_view(request, user_id):
    profile_user = get_object_or_404(CustomUser, id=user_id)
    followers = CustomUser.objects.filter(
        following_users__following=profile_user
    ).distinct()
    return render(
        request,
        "profile/followers_list.html",
        {"profile_user": profile_user, "followers": followers},
    )


@login_required
def following_list_view(request, user_id):
    profile_user = get_object_or_404(CustomUser, id=user_id)
    following = CustomUser.objects.filter(
        followed_by_users__follower=profile_user
    ).distinct()
    return render(
        request,
        "profile/following_list.html",
        {"profile_user": profile_user, "following": following},
    )


@login_required
def not_interested_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    NotInterestedPost.objects.create(user=request.user, post=post)
    return redirect("blog:home")


@login_required
def not_interested_post_list_view(request):
    posts = NotInterestedPost.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "post/not_interested_posts.html", {"posts": posts})


@login_required
def save_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    SavedPost.objects.create(user=request.user, post=post)
    is_saved = True
    message = "Post saved to your list."
    if request.method != "POST":
        return redirect("blog:home")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True, "is_saved": is_saved, "message": message})
    return redirect("blog:home")


@login_required
def saved_post_list_view(request):
    saved_posts = SavedPost.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "post/saved_posts.html", {"saved_posts": saved_posts})


@login_required
def friends_list_view(request):
    following = CustomUser.objects.filter(
        followed_by_users__follower=request.user
    ).distinct()
    followers = CustomUser.objects.filter(
        following_users__following=request.user
    ).distinct()
    friends = following.intersection(followers)
    return render(request, "profile/friends_list.html", {"friends": friends})


@login_required
def category_list_view(request):
    categories = Category.objects.order_by("name")
    return render(request, "category/category_list.html", {"categories": categories})


@login_required
def news_feed_view(request):
    posts = prepare_posts_with_comment_trees(
        Post.objects.filter(is_published=True, categories__name="news")
        .exclude(
            id__in=NotInterestedPost.objects.filter(user=request.user).values_list(
                "post_id", flat=True
            )
        )
        .order_by("-created_at")
    )
    liked_comment_ids = Like.objects.filter(
        user=request.user, post__isnull=True, comment__isnull=False
    ).values_list("comment_id", flat=True)
    return render(
        request,
        "post/post_list.html",
        {"posts": posts, "liked_comment_ids": list(liked_comment_ids)},
    )


def filter_by_category_view(request):
    query = request.GET.get("q", "").strip()
    posts = Post.objects.filter(is_published=True)
    if query:
        posts = posts.filter(categories__name__icontains=query)
    posts = prepare_posts_with_comment_trees(posts.order_by("-created_at"))
    liked_comment_ids = []
    if request.user.is_authenticated:
        liked_comment_ids = list(
            Like.objects.filter(
                user=request.user, post__isnull=True, comment__isnull=False
            ).values_list("comment_id", flat=True)
        )
    return render(
        request,
        "post/post_list.html",
        {"posts": posts, "query": query, "liked_comment_ids": liked_comment_ids},
    )
