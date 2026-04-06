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
    path('post/<int:post_id>/not-interested/', MarkNotInterestedView.as_view(), name='mark_not_interested'),
    path('post/<int:post_id>/like/', LikeView.as_view(), name='like_post'),
    path('notifications/', notifications_list, name='notifications_list'),
    path('mark_read/<int:notification_id>/', MarkReadView.as_view(), name='mark_read'),
    path('mark_all_read/', MarkAllReadView.as_view(), name='mark_all_read'),
    path('notifications/unread-count/', notifications_unread_count, name='notifications_unread_count'),
    path('interests/', SelectInterestsView.as_view(), name='interests'),
    path('my_posts/', MyPostsView.as_view(), name='my_posts'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/<int:user_id>/', OtherUserProfileView.as_view(), name='other_profile'),
    path('profile/<int:user_id>/follow/', FollowUserView.as_view(), name='follow_user'),
    path('profile/<int:user_id>/followers/', FollowerListView.as_view(), name='followers_list'),
    path('profile/<int:user_id>/following/', FollowingListView.as_view(), name='following_list'),
    path('update_post/<int:pk>/', PostUpdateView.as_view(), name='update_post'),
    path('delete_post/<int:pk>/', PostDeleteView.as_view(), name='delete_post'),
    path('comment/<int:comment_id>/like/', CommentLikeView.as_view(), name='comment_like'),
    path('comment/<int:comment_id>/delete/', CommentDeleteView.as_view(), name='comment_delete'),
    path('comment/<int:comment_id>/update/', CommentUpdateView.as_view(), name='comment_update'),
    path('comment/<int:comment_id>/reply/', CommentReplyView.as_view(), name='comment_reply'),
]

