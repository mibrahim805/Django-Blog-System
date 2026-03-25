from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from blog.forms import RegistrationForm, PostCreateForm, CommentForm
from blog.models import Post, Notification, Comment, Like


class UserRegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("home")


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "post/post_list.html"
    context_object_name = "posts"
    ordering = ["-created_at"]
    def get_queryset(self):
        return Post.objects.filter(is_published=True)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostCreateForm
    template_name = "post/post_create.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)

        if form.instance.is_published:
            users = User.objects.exclude(id=self.request.user.id)

            notifications = [Notification(user=user, post=form.instance, sender=self.request.user, message=f"{self.request.user.username} published a new post.") for user in users]
            Notification.objects.bulk_create(notifications)
        return response

class CommentCreateView(LoginRequiredMixin,CreateView):
    model = Comment
    form_class = CommentForm
    template_name = "comments/comment_create.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        post_id = self.kwargs.get("post_id")
        form.instance.post_id = post_id
        form.instance.user = self.request.user
        response = super().form_valid(form)

        post = Post.objects.get(id=post_id)
        if post.author != self.request.user:
            Notification.objects.create(user=post.author, post=post, sender=self.request.user, message=f"{self.request.user.username} commented on your post.")
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
                Notification.objects.create(user=post.author, post=post, sender=request.user, message=f"{request.user.username} liked your post.")
        return redirect("home")
