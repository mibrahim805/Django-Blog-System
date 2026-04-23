# import Category
# from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from ckeditor_uploader.fields import RichTextUploadingField

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = RichTextUploadingField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)
    category = models.ManyToManyField("Category", blank=True)

    def __str__(self):
        return self.title
    
    def get_like_count(self):
        return self.like_set.filter(comment__isnull=True).count()

    @property
    def approved_comments(self):
        return self.comments.filter(is_approved=True).select_related("user").order_by("created_at")

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.content
    
    def get_like_count(self):
        return self.like_set.filter(post__isnull=True).count()

class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post', 'comment')

    def __str__(self):
        return str(self.user)

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications_sent')


    def __str__(self):
        return self.message


class Category(models.Model):
    name = models.CharField(max_length=200)
    posts = models.ManyToManyField(Post, related_name='categories', blank=True)


    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    interested_in = models.ManyToManyField(Category, related_name='interested_users')
    not_interested_posts = models.ManyToManyField(Post, related_name='user_not_interested_posts')
    saved_posts = models.ManyToManyField(Post, related_name='saved_posts')

    def __str__(self):
        return str(self.interested_in.all())

class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following_users')
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followed_by_users')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('follower', 'following')
    
    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class NotInterestedPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="not_interested_entries")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="not_interested_entries")
    reason = models.TextField(max_length=400)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} not interested in {self.post.title}"


class SavedPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_posts")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="saved_by_users")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("user", "post")
        ordering = ["-created_at"]
    def __str__(self):
        return f"{self.user.username} saved {self.post.title}"