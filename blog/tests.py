from django.test import TestCase
from django.urls import reverse

from blog.models import Comment, CustomUser, Like, Notification, Post, SavedPost


class PostEngagementTests(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user(
            username="author", email="author@example.com", password="pass12345"
        )
        self.user = CustomUser.objects.create_user(
            username="reader", email="reader@example.com", password="pass12345"
        )
        self.post = Post.objects.create(
            title="Post 1", content="Body", author=self.author, is_published=True
        )
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

        first = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(
            first.json(),
            {"success": True, "is_liked": True, "like_count": 1},
        )
        self.assertTrue(Like.objects.filter(user=self.user, post=self.post).exists())

        second = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(
            second.json(),
            {"success": True, "is_liked": False, "like_count": 0},
        )
        self.assertFalse(Like.objects.filter(user=self.user, post=self.post).exists())

    def test_post_like_requires_post(self):
        self.client.login(username="reader", password="pass12345")
        url = reverse("blog:like_post", kwargs={"post_id": self.post.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(Like.objects.filter(user=self.user, post=self.post).exists())

    def test_post_like_state_and_count_are_rendered(self):
        Like.objects.create(user=self.user, post=self.post)
        self.client.login(username="reader", password="pass12345")

        response = self.client.get(reverse("blog:home"))

        self.assertContains(response, f'id="like-btn-{self.post.id}"')
        self.assertContains(response, 'aria-pressed="true"')
        self.assertContains(response, ">Liked</span>")
        self.assertContains(response, f'id="post-like-count-{self.post.id}">1</span>')

    def test_user_can_like_and_unlike_comment_via_ajax(self):
        self.client.login(username="reader", password="pass12345")
        url = reverse(
            "blog:comment_like", kwargs={"comment_id": self.approved_comment.id}
        )

        first = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(
            first.json(),
            {"success": True, "is_liked": True, "like_count": 1},
        )
        self.assertTrue(
            Like.objects.filter(
                user=self.user,
                comment=self.approved_comment,
                post__isnull=True,
            ).exists()
        )

        second = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            second.json(),
            {"success": True, "is_liked": False, "like_count": 0},
        )
        self.assertFalse(
            Like.objects.filter(user=self.user, comment=self.approved_comment).exists()
        )

    def test_comment_like_requires_post(self):
        self.client.login(username="reader", password="pass12345")
        url = reverse(
            "blog:comment_like", kwargs={"comment_id": self.approved_comment.id}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(
            Like.objects.filter(user=self.user, comment=self.approved_comment).exists()
        )

    def test_comment_like_state_is_rendered_on_feed_and_detail(self):
        Like.objects.create(user=self.user, comment=self.approved_comment)
        self.client.login(username="reader", password="pass12345")

        for url in (
            reverse("blog:home"),
            reverse("blog:post_detail", kwargs={"pk": self.post.id}),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response, f'id="comment-like-{self.approved_comment.id}"'
                )
                self.assertContains(response, 'aria-pressed="true"')
                self.assertContains(response, ">Liked</span>")
                self.assertContains(
                    response,
                    f'id="comment-like-count-{self.approved_comment.id}"',
                )

    def test_comment_like_notifies_the_comment_author(self):
        self.client.login(username="author", password="pass12345")
        url = reverse(
            "blog:comment_like", kwargs={"comment_id": self.approved_comment.id}
        )

        self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                sender=self.author,
                post=self.post,
                message__contains="liked your comment",
            ).exists()
        )

    def test_reply_is_saved_under_its_parent_and_returns_thread_html(self):
        self.client.login(username="author", password="pass12345")
        url = reverse(
            "blog:comment_reply", kwargs={"comment_id": self.approved_comment.id}
        )

        response = self.client.post(
            url,
            {"content": "Nested response"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        reply = Comment.objects.get(id=payload["comment_id"])
        self.assertEqual(reply.parent_comment, self.approved_comment)
        self.assertEqual(reply.post, self.post)
        self.assertEqual(payload["parent_id"], self.approved_comment.id)
        self.assertEqual(payload["reply_count"], 1)
        self.assertEqual(payload["post_comment_count"], 3)
        self.assertIn("Nested response", payload["html"])
        self.assertIn(f'id="comment-{reply.id}"', payload["html"])

    def test_nested_replies_render_under_their_own_parent(self):
        first_reply = Comment.objects.create(
            post=self.post,
            user=self.author,
            content="First nested reply",
            parent_comment=self.approved_comment,
        )
        second_reply = Comment.objects.create(
            post=self.post,
            user=self.user,
            content="Second nested reply",
            parent_comment=first_reply,
        )
        self.client.login(username="reader", password="pass12345")

        response = self.client.get(reverse("blog:home"))

        self.assertEqual(response.status_code, 200)
        rendered_post = next(
            post for post in response.context["posts"] if post.id == self.post.id
        )
        self.assertEqual(
            [comment.id for comment in rendered_post.comment_tree],
            [self.approved_comment.id, self.pending_comment.id],
        )
        tree_root = rendered_post.comment_tree[0]
        self.assertEqual(tree_root.display_replies[0].id, first_reply.id)
        self.assertEqual(
            tree_root.display_replies[0].display_replies[0].id,
            second_reply.id,
        )
        self.assertContains(response, "View 1 reply", count=2)
        self.assertContains(response, f'id="comment-replies-{first_reply.id}"')
        self.assertContains(response, "Second nested reply")

    def test_reply_endpoint_requires_post(self):
        self.client.login(username="reader", password="pass12345")
        url = reverse(
            "blog:comment_reply", kwargs={"comment_id": self.approved_comment.id}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.approved_comment.replies.count(), 0)

    def test_comment_delete_redirects_cleanly_to_the_current_page(self):
        reply = Comment.objects.create(
            post=self.post,
            user=self.author,
            content="Child reply",
            parent_comment=self.approved_comment,
        )
        self.client.login(username="reader", password="pass12345")
        url = reverse(
            "blog:comment_delete", kwargs={"comment_id": self.approved_comment.id}
        )
        next_url = reverse("blog:post_detail", kwargs={"pk": self.post.id})

        response = self.client.post(url, {"next": next_url})

        self.assertRedirects(response, next_url)
        self.assertFalse(
            Comment.objects.filter(id__in=[self.approved_comment.id, reply.id]).exists()
        )

    def test_comment_delete_returns_a_complete_ajax_response(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            content="Delete through AJAX",
        )
        self.client.login(username="reader", password="pass12345")
        url = reverse("blog:comment_delete", kwargs={"comment_id": comment.id})

        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "success": True,
                "comment_id": comment.id,
                "post_id": self.post.id,
                "post_comment_count": 2,
            },
        )
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())

    def test_comment_delete_requires_post(self):
        self.client.login(username="reader", password="pass12345")
        url = reverse(
            "blog:comment_delete", kwargs={"comment_id": self.approved_comment.id}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Comment.objects.filter(id=self.approved_comment.id).exists())

    def test_user_can_comment_on_post(self):
        self.client.login(username="reader", password="pass12345")
        url = reverse("blog:create_comment", kwargs={"post_id": self.post.id})

        response = self.client.post(url, {"content": "Nice post"})

        self.assertRedirects(response, reverse("blog:home"))
        self.assertTrue(
            Comment.objects.filter(
                post=self.post, user=self.user, content="Nice post"
            ).exists()
        )

    def test_all_comments_show_on_home_feed(self):
        self.client.login(username="reader", password="pass12345")
        response = self.client.get(reverse("blog:home"))

        self.assertContains(response, "Approved comment")
        self.assertContains(response, "Pending comment")
        self.assertContains(response, "2 comments")
        self.assertContains(response, f'id="comments-toggle-{self.post.id}"')
        self.assertContains(
            response,
            f'aria-controls="comments-section-{self.post.id}"',
        )
        self.assertContains(
            response,
            f'id="comment-composer-toggle-{self.post.id}"',
        )

    def test_all_comments_show_on_my_posts_page(self):
        self.client.login(username="author", password="pass12345")
        response = self.client.get(reverse("blog:my_posts"))

        self.assertContains(response, "Approved comment")
        self.assertContains(response, "Pending comment")

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
        self.client.get(
            reverse(
                "blog:mark_read",
                kwargs={"notification_id": Notification.objects.first().id},
            )
        )
        count_response_after_open = self.client.get(
            reverse("blog:notifications_unread_count")
        )
        self.assertEqual(count_response_after_open.json()["unread_count"], 0)

    def test_user_can_save_and_unsave_post_via_ajax(self):
        self.client.login(username="reader", password="pass12345")
        url = reverse("blog:save_post", kwargs={"post_id": self.post.id})

        first = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["success"])
        self.assertTrue(first.json()["is_saved"])
        self.assertTrue(
            SavedPost.objects.filter(user=self.user, post=self.post).exists()
        )

        second = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["success"])
        self.assertFalse(second.json()["is_saved"])
        self.assertFalse(
            SavedPost.objects.filter(user=self.user, post=self.post).exists()
        )

    def test_saved_posts_page_shows_saved_post(self):
        SavedPost.objects.create(user=self.user, post=self.post)
        self.client.login(username="reader", password="pass12345")

        response = self.client.get(reverse("blog:saved_posts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.post.title)


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
        self.assertTrue(
            self.client.login(username="reader2@example.com", password="pass12345")
        )
