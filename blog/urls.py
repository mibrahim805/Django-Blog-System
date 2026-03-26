from django.contrib.auth.views import LoginView
from django.urls import path
from blog.views import *

app_name = 'blog'
urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='register'),
    path('', LoginView.as_view(), name='login'),
    path('create_post/', PostCreateView.as_view(), name='create_post'),
    path('post_list/', PostListView.as_view(), name='home'),
    path('post/<int:post_id>/comment/', CommentCreateView.as_view(), name='create_comment'),
    path('post/<int:post_id>/like/', LikeView.as_view(), name='like_post'),
    path('notifications/', notifications_list, name='notifications_list'),
    path('mark_read/<int:notification_id>/"', MarkReadView.as_view(), name='mark_read'),
    path('mark_all_read/', MarkAllReadView.as_view(), name='mark_all_read'),
    path('notifications/unread-count/', notifications_unread_count, name='notifications_unread_count'),
]
