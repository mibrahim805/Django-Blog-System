from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from blog.models import Post


class RegistrationForm(UserCreationForm):
    class Meta:
        model=User
        fields=["username" ,"email","password1","password2"]

class PostCreateForm(forms.ModelForm):
    class Meta:
        model=Post
        fields=["title","content"]

class CommentForm(forms.ModelForm):
    class Meta:
        model=Post
        fields=["content"]


