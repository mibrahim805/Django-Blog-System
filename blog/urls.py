from django.urls import path
from blog.views import *

app_name = 'blog'
urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='register'),
    path('post/create/', PostCreateView.as_view(), name='post-create'),
    path('post_list/', PostListView.as_view(), name='home'),
]
