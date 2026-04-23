from django.contrib import admin

from blog.models import Post, Category, Profile, Like, Comment, CustomUser


# Register your models here.
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "is_staff", "is_active"]

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "content"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    dict_display = ["user", "interested_in"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["user", "post", "is_approved", "created_at", "content"]
    list_filter = ["is_approved", "created_at"]
    search_fields = ["content", "user__username", "post__title"]
    actions = ["approve_comments"]

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)


# admin.site.register(Like)
# class 