from django.contrib import admin

from blog.models import Post, Category, Profile, Like, Comment


# Register your models here.


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "content"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    dict_display = ["user", "interested_in"]


admin.site.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["user", "comment"]


# admin.site.register(Like)
# class 