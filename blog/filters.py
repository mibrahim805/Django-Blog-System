import django_filters
from django import forms
from .models import Post, Category


class PostFilter(django_filters.FilterSet):
    categories = django_filters.ModelMultipleChoiceFilter(
        queryset=Category.objects.all(),
        field_name="categories",   # ManyToMany field in Post
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Post
        fields = ['categories']