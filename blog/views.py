from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from blog.forms import RegistrationForm, PostCreateForm, CommentForm
from blog.models import Post, Notification, Comment, Like


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


class UserRegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("blog:home")


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "post/post_list.html"
    context_object_name = "posts"
    ordering = ["-created_at"]

    def get_queryset(self):
        return Post.objects.select_related("author").filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        liked_post_ids = Like.objects.filter(user=self.request.user).values_list("post_id", flat=True)
        context["liked_post_ids"] = set(liked_post_ids)
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
            users = User.objects.exclude(id=self.request.user.id)
            for user in users:
                create_and_push_notification(user=user,post=form.instance,sender=self.request.user,message=f"{self.request.user.username} published a new post.",)
        return response

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

