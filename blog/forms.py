from django import forms
from django.contrib.auth.forms import UserCreationForm

from blog.models import Comment, Post, Category, CustomUser


class RegistrationForm(UserCreationForm):
    class Meta:
        model=CustomUser
        fields=["username" ,"email","password1","password2"]

class PostCreateForm(forms.ModelForm):
    class Meta:
        model=Post
        fields=["title","content", "is_published","category"]

class CommentForm(forms.ModelForm):
    class Meta:
        model=Comment
        fields=["content"]

class CategoryCreateForm(forms.ModelForm):
    class Meta:
        model=Category
        fields=["name"]

class InterestForm(forms.Form):
    interests = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )