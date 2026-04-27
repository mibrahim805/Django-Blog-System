from blog.views import user_register_view, post_create_view, post_list_view, comment_createView, not_interested_view, \
    like_view, notifications_list_view, mark_as_read_view, mark_all_as_read_view, unread_notifications_count_view, \
    select_interest_view, my_posts_view, my_profile_view, other_user_profile_view, user_follow_view, follower_list_view, \
    following_list_view, post_update_view, post_delete_view, comment_like_view, comment_delete_view, comment_edit_view, \
    comment_reply_view, save_post_view, saved_post_list_view, friends_list_view, category_list_view
from django.contrib.auth.views import LoginView
from django.contrib.auth import views as auth_views
from django.urls import path
from blog.old_views import *

app_name = 'blog'
urlpatterns = [
    path('register/',user_register_view, name='register'),
    path('', LoginView.as_view(), name='login'),
    path('create_post/', post_create_view, name='create_post'),
    path('post_list/', post_list_view, name='home'),
    path('post/<int:post_id>/comment/', comment_createView, name='create_comment'),
    path('post/<int:post_id>/not-interested/', not_interested_view, name='mark_not_interested'),
    path('post/<int:post_id>/like/', like_view, name='like_post'),
    path('notifications/',notifications_list_view, name='notifications_list'),
    path('mark_read/<int:notification_id>/', mark_as_read_view, name='mark_read'),
    path('mark_all_read/', mark_all_as_read_view, name='mark_all_read'),
    path('notifications/unread-count/', unread_notifications_count_view, name='notifications_unread_count'),
    path('interests/',select_interest_view, name='interests'),
    path('my_posts/', my_posts_view, name='my_posts'),
    path('profile/', my_profile_view, name='profile'),
    path('profile/<int:user_id>/', other_user_profile_view, name='other_profile'),
    path('profile/<int:user_id>/follow/', user_follow_view, name='follow_user'),
    path('profile/<int:user_id>/followers/', follower_list_view, name='followers_list'),
    path('profile/<int:user_id>/following/',following_list_view, name='following_list'),
    path('update_post/<int:pk>/', post_update_view, name='update_post'),
    path('delete_post/<int:pk>/', post_delete_view, name='delete_post'),
    path('comment/<int:comment_id>/like/', comment_like_view, name='comment_like'),
    path('comment/<int:comment_id>/delete/', comment_delete_view, name='comment_delete'),
    path('comment/<int:comment_id>/update/', comment_edit_view, name='comment_update'),
    path('comment/<int:comment_id>/reply/', comment_reply_view, name='comment_reply'),
    path("password-reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path('post/<int:post_id>/save/', save_post_view, name='save_post'),
    path('saved_posts/', saved_post_list_view, name='saved_posts'),
    path('friends/', friends_list_view, name='friends_list'),
    path('categories/', category_list_view, name='category_list'),
]