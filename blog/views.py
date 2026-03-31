from urllib import response

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, FormView, UpdateView, DeleteView
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from twisted.names.client import query

from blog.forms import RegistrationForm, PostCreateForm, CommentForm, InterestForm, CategoryCreateForm
from blog.models import Post, Notification, Comment, Like, Profile, Category




class UserRegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("blog:interests")

    def form_valid(self, form):
        response = super().form_valid(form)

        Profile.objects.create(user=self.object)

        return response

class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "post/post_list.html"
    context_object_name = "posts"
    ordering = ["-created_at"]


    def get_queryset(self):
        user = self.request.user
        profile, created = Profile.objects.get_or_create(user=user)
        interests = profile.interested_in.all()
        queryset = Post.objects.filter(is_published=True)

        if interests.exists():
            queryset = queryset.filter(categories__in=interests).distinct()
        return queryset



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
            users = User.objects.exclude(id=self.request.user.id)
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


class SelectInterestsView(FormView):
    template_name = "interest/select_interest.html"
    form_class = InterestForm
    success_url = reverse_lazy("blog:home")

    def form_valid(self, form):
        interests = form.cleaned_data['interests']

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