from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from blog.models import Comment, Like, Notification, Post


class PostEngagementTests(TestCase):
	def setUp(self):
		self.author = User.objects.create_user(username="author", password="pass12345")
		self.user = User.objects.create_user(username="reader", password="pass12345")
		self.post = Post.objects.create(title="Post 1", content="Body", author=self.author, is_published=True)

	def test_user_can_like_and_unlike_post(self):
		self.client.login(username="reader", password="pass12345")
		url = reverse("blog:like_post", kwargs={"post_id": self.post.id})

		self.client.post(url)
		self.assertTrue(Like.objects.filter(user=self.user, post=self.post).exists())

		self.client.post(url)
		self.assertFalse(Like.objects.filter(user=self.user, post=self.post).exists())

	def test_user_can_comment_on_post(self):
		self.client.login(username="reader", password="pass12345")
		url = reverse("blog:create_comment", kwargs={"post_id": self.post.id})

		response = self.client.post(url, {"content": "Nice post"})

		self.assertRedirects(response, reverse("blog:home"))
		self.assertTrue(Comment.objects.filter(post=self.post, user=self.user, content="Nice post").exists())

	def test_like_creates_notification_for_post_author(self):
		self.client.login(username="reader", password="pass12345")
		url = reverse("blog:like_post", kwargs={"post_id": self.post.id})
		self.client.post(url)

		notification_exists = Notification.objects.filter(
			user=self.author,
			post=self.post,
			sender=self.user,
			message__contains="liked your post",
		).exists()
		self.assertTrue(notification_exists)

	def test_unread_count_endpoint_and_mark_read_flow(self):
		Notification.objects.create(
			user=self.author,
			post=self.post,
			sender=self.user,
			message="reader liked your post.",
		)
		self.client.login(username="author", password="pass12345")

		count_response = self.client.get(reverse("blog:notifications_unread_count"))
		self.assertEqual(count_response.status_code, 200)
		self.assertEqual(count_response.json()["unread_count"], 1)

		self.client.get(reverse("blog:notifications_list"))
		count_response_after_open = self.client.get(reverse("blog:notifications_unread_count"))
		self.assertEqual(count_response_after_open.json()["unread_count"], 0)

