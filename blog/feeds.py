from django.contrib.syndication.views import Feed
from django.urls import reverse
from .models import Post


class LatestPostsFeed(Feed):
    title = "My Blog Latest Posts"
    link = "/feed/"
    description = "Latest posts from my blog"

    def items(self):
        return Post.objects.filter(is_published=True).order_by('-created_at')[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.content

    def item_link(self, item):
        return reverse('blog:post_detail', args=[item.id])
