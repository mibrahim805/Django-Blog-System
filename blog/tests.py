from django.test import TestCase
from django.urls import reverse

from blog.models import Comment, Like, Notification, Post, CustomUser


class PostEngagementTests(TestCase):
	def setUp(self):
		self.author = CustomUser.objects.create_user(username="author", email="author@example.com", password="pass12345")
		self.user = CustomUser.objects.create_user(username="reader", email="reader@example.com", password="pass12345")
		self.post = Post.objects.create(title="Post 1", content="Body", author=self.author, is_published=True)
		self.approved_comment = Comment.objects.create(
			post=self.post,
			user=self.user,
			content="Approved comment",
			is_approved=True,
		)
		self.pending_comment = Comment.objects.create(
			post=self.post,
			user=self.user,
			content="Pending comment",
		)

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

	def test_only_approved_comments_show_on_home_feed(self):
		self.client.login(username="reader", password="pass12345")
		response = self.client.get(reverse("blog:home"))

		self.assertContains(response, "Approved comment")
		self.assertNotContains(response, "Pending comment")
		self.assertContains(response, "Show Comments (1)")
		self.assertContains(response, "All Comments (1)")

	def test_only_approved_comments_show_on_my_posts_page(self):
		self.client.login(username="author", password="pass12345")
		response = self.client.get(reverse("blog:my_posts"))

		self.assertContains(response, "Approved comment")
		self.assertNotContains(response, "Pending comment")

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
		self.client.get(reverse("blog:mark_read", kwargs={"notification_id": Notification.objects.first().id}))
		count_response_after_open = self.client.get(reverse("blog:notifications_unread_count"))
		self.assertEqual(count_response_after_open.json()["unread_count"], 0)


class AuthBackendTests(TestCase):
	def setUp(self):
		self.user = CustomUser.objects.create_user(
			username="reader2",
			email="reader2@example.com",
			password="pass12345",
		)

	def test_login_with_username(self):
		self.assertTrue(self.client.login(username="reader2", password="pass12345"))

	def test_login_with_email(self):
		self.assertTrue(self.client.login(username="reader2@example.com", password="pass12345"))


