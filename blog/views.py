from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, FormView, UpdateView, DeleteView
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django_filters.views import FilterView

from blog.filters import PostFilter
from blog.forms import RegistrationForm, PostCreateForm, CommentForm, InterestForm, NotInterestedReasonForm
from blog.models import Post, Notification, Comment, Like, Profile, Category, CustomUser, NotInterestedPost


def create_and_push_notification(*, user, post, sender, message):
    notification = Notification.objects.create(user=user, post=post, sender=sender, message=message)
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {
            "type": "send_notification",
            "message": message,
            "notification_id": notification.id,
        }
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
    
    # Get followers and following using correct related names
    followers = CustomUser.objects.filter(following_users__following=profile_user).distinct()
    following = CustomUser.objects.filter(following_users__follower=profile_user).distinct()
    
    is_following = False
    if current_user and current_user.is_authenticated:
        is_following = Follow.objects.filter(follower=current_user, following=profile_user).exists()

    not_interested_entries = (
        NotInterestedPost.objects.filter(user=profile_user)
        .select_related("post", "post__author")
        .order_by("-created_at")
    )

    return {
        "profile_user": profile_user,
        "profile": profile,
        "user_posts": Post.objects.filter(author=profile_user, is_published=True).count(),
        "user_likes": Like.objects.filter(post__author=profile_user, comment__isnull=True).count(),
        "user_comments": Comment.objects.filter(user=profile_user).count(),
        "interests": profile.interested_in.all(),
        "recent_posts": recent_posts,
        "followers": followers,
        "following": following,
        "followers_count": followers.count(),
        "following_count": following.count(),
        "is_following": is_following,
        "followers_list":Follow.objects.filter(following=profile_user).select_related("follower"),
        "following_list":Follow.objects.filter(follower=profile_user).select_related("following"),
        "not_interested_entries": not_interested_entries,
        "not_interested_count": not_interested_entries.count(),
    }


class UserRegisterView(CreateView):
    model = CustomUser
    form_class = RegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("blog:interests")

    def form_valid(self, form):
        response = super().form_valid(form)

        Profile.objects.create(user=self.object)

        return response
#
# class PostListView(LoginRequiredMixin, ListView):
#     model = Post
#     template_name = "post/post_list.html"
#     context_object_name = "posts"
#     ordering = ["-created_at"]
#
#     def get_selected_category(self):
#         selected_category = []
#         for value in self.request.GET.getlist("categories"):
#             try:
#                 selected_category.append(value)
#             except (TypeError, ValueError):
#                 continue
#         return list(Category.objects.filter(id__in=selected_category).values_list("id", flat=True))
#
#     def get_queryset(self):
#         queryset = Post.objects.filter(is_published=True)
#
#         selected_categories = self.get_selected_category()
#
#         if selected_categories:
#             queryset = queryset.filter(category_id__in=selected_categories)
#
#         return queryset
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context["all_categories"] = Category.objects.order_by("name")
#
#         context["selected_category_ids"] = self.get_selected_category()
#         return context



class PostListView(LoginRequiredMixin, FilterView):
    model = Post
    template_name = "post/post_list.html"
    context_object_name = "posts"
    ordering = ["-created_at"]
    filterset_class = PostFilter

    def get_queryset(self):
        hidden_post_ids = NotInterestedPost.objects.filter(user=self.request.user).values_list("post_id", flat=True)
        return (
            Post.objects.filter(is_published=True)
            .exclude(id__in=hidden_post_ids)
            .select_related("author")
            .prefetch_related("categories", "comments", "comments__user")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_categories"] = Category.objects.order_by("name")

        selected_category_ids = []
        for category_id in self.request.GET.getlist("categories"):
            if not category_id or category_id == "all":
                continue
            try:
                selected_category_ids.append(int(category_id))
            except (TypeError, ValueError):
                continue
        context["selected_category_ids"] = selected_category_ids

        liked_posts = Like.objects.filter(user=self.request.user, comment__isnull=True).values_list("post_id", flat=True)
        context["liked_post_ids"] = list(liked_posts)

        liked_comments = Like.objects.filter(user=self.request.user, comment__isnull=False).values_list("comment_id", flat=True)
        context["liked_comment_ids"] = list(liked_comments)
        context["not_interested_form"] = NotInterestedReasonForm()

        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostCreateForm
    template_name = "post/post_create.html"
    success_url = reverse_lazy("blog:home")

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)

        if form.instance.is_published:
            print("is_published")
            users = CustomUser.objects.exclude(id=self.request.user.id)
            for user in users:
                create_and_push_notification(user=user,post=form.instance,sender=self.request.user,message=f"{self.request.user.username} published a new post.",)
        return response

class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostCreateForm
    template_name = "post/post_create.html"
    success_url = reverse_lazy("blog:home")

    def form_valid(self, form):
        form.instance.author = self.request.user
        response= super().form_valid(form)
        if form.instance.is_published:
            print("is_published")
            users = CustomUser.objects.exclude(id=self.request.user.id)
            for user in users:
                create_and_push_notification(user=user,post=form.instance,sender=self.request.user,message=f"{self.request.user.username} published a new post.",)
        return response



class PostDeleteView(LoginRequiredMixin,DeleteView):
    model=Post
    template_name = "post/delete_post.html"
    success_url=reverse_lazy("blog:my_posts")


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = "comments/comment_create.html"
    success_url = reverse_lazy("blog:home")

    def form_valid(self, form):
        post_id = self.kwargs.get("post_id")
        form.instance.post_id = post_id
        form.instance.user = self.request.user
        response = super().form_valid(form)

        post = get_object_or_404(Post, id=post_id)
        if post.author != self.request.user:
            create_and_push_notification(user=post.author,post=post,sender=self.request.user,message=f"{self.request.user.username} commented on your post.",)
        return response


class LikeView(LoginRequiredMixin,View):
    def post(self, request, post_id):
        post =  get_object_or_404(Post, id=post_id)
        like = Like.objects.filter(user=request.user, post=post).first()

        if like:
            like.delete()
        else:
            Like.objects.create(user=request.user, post=post)
            if post.author != request.user:
                create_and_push_notification(user=post.author,post=post,sender=request.user,message=f"{request.user.username} liked your post.",)
        return redirect("blog:home")


@login_required
def notifications_list(request):
    new_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by("-created_at")
    old_notifications = Notification.objects.filter(user=request.user, is_read=True).order_by("-created_at")

    return render(request, "notifications/list.html", {"new_notifications": new_notifications,"old_notifications": old_notifications,})




@login_required
def notifications_unread_count(request):
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"unread_count": unread_count})


class MarkReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notification_id = kwargs.get("notification_id")
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return redirect("blog:notifications_list")


class MarkAllReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect("blog:notifications_list")


class SelectInterestsView(LoginRequiredMixin, FormView):
    template_name = "interest/select_interest.html"
    form_class = InterestForm
    success_url = reverse_lazy("blog:home")

    def form_valid(self, form):
        interests = form.cleaned_data["interests"]
        profile = self.request.user.profile
        profile.interested_in.set(interests)
        return super().form_valid(form)

class MyPostsView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "post/my_posts.html"
    context_object_name = "posts"

    def get_queryset(self):
        user = self.request.user
        queryset = Post.objects.filter(author=user).order_by("-created_at")
        print("USER:", self.request.user)
        print("POSTS:", queryset)
        return queryset


class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        context = build_profile_context(request.user, request.user)
        context["user"] = request.user
        return render(request, "profile/my_profile.html", context)



class CommentLikeView(LoginRequiredMixin, View):
    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)
        like = Like.objects.filter(user=request.user, comment=comment).first()

        if like:
            like.delete()
        else:
            Like.objects.create(user=request.user, comment=comment)
            if comment.user != request.user:
                create_and_push_notification(user=comment.user,post=comment.post,sender=request.user,message=f"{request.user.username} liked your comment.",)
        return redirect("blog:home")


class CommentReplyView(LoginRequiredMixin, View):
    # def get(self, request, comment_id):
    #     comment = get_object_or_404(Comment, id=comment_id)
    #     return render(request, 'comments/comment_reply.html', {'comment': comment})

    def post(self, request, comment_id):
        parent_comment = get_object_or_404(Comment, id=comment_id)
        content = request.POST.get("content")
        if content:
            reply_comment = Comment.objects.create(
                post=parent_comment.post,
                user=request.user,
                content=content
            )
            if parent_comment.user != request.user:
                create_and_push_notification(user=parent_comment.user,post=parent_comment.post,sender=request.user,message=f"{request.user.username} replied to your comment.",)
        return redirect("blog:home")


class CommentDeleteView(LoginRequiredMixin, View):
    # def get(self, request, comment_id):
    #     comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    #     return render(request, 'comments/comment_delete.html', {'comment': comment})

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id, user=request.user)
        comment.delete()
        return redirect("blog:home")

class CommentUpdateView(LoginRequiredMixin, View):
    # def get(self, request, comment_id):
    #     comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    #     return render(request, 'comments/comment_edit.html', {'comment': comment})

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id, user=request.user)
        new_content = request.POST.get("content")
        if new_content and new_content.strip():
            comment.content = new_content.strip()
            comment.save()
        return redirect("blog:home")


class OtherUserProfileView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        other_user = get_object_or_404(CustomUser, id=user_id)
        context = build_profile_context(other_user, request.user)
        context["other_user"] = other_user
        context["is_own_profile"] = other_user == request.user
        return render(request, "profile/other_profile.html", context)


class FollowUserView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        from blog.models import Follow
        follower = request.user
        following = get_object_or_404(CustomUser, id=user_id)
        
        # Check if already following
        follow_relation = Follow.objects.filter(follower=follower, following=following).first()
        
        if follow_relation:
            follow_relation.delete()
        else:
            Follow.objects.create(follower=follower, following=following)
        
        # Redirect back to the profile
        return redirect("blog:other_profile", user_id=user_id)


class FollowerListView(LoginRequiredMixin,View):
    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        followers = CustomUser.objects.filter(following_users__following=user).distinct()
        return render(request, "profile/followers_list.html", {"followers": followers, "profile_user": user})

class FollowingListView(LoginRequiredMixin,View):
    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        following = CustomUser.objects.filter(following_users__follower=user).distinct()
        return render(request, "profile/following_list.html", {"following": following, "profile_user": user})

class MarkNotInterestedView(LoginRequiredMixin, View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, is_published=True)
        form = NotInterestedReasonForm(request.POST)

        if not form.is_valid():
            return redirect("blog:home")

        reason = form.cleaned_data["reason"].strip()
        NotInterestedPost.objects.update_or_create(
            user=request.user,
            post=post,
            defaults={"reason": reason},
        )
        return redirect("blog:home")

class NotInterestedPostListView(LoginRequiredMixin,View):
    def get(self,request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        not_interested_posts = (
            NotInterestedPost.objects.filter(user=user)
            .select_related("post", "post__author")
            .order_by("-created_at")
        )
        return render(request, "post/not_interested_posts.html", {"not_interested_posts": not_interested_posts})


