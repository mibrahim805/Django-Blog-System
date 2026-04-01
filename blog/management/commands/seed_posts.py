import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from blog.models import Category, CustomUser, Post


DEFAULT_CATEGORY_NAMES = [
	"Technology",
	"Health",
	"Travel",
	"Education",
	"Food",
	"Business",
	"Sports",
	"Lifestyle",
	"Entertainment",
	"Science",
]


class Command(BaseCommand):
	help = "Seed categories and posts with mixed category assignments"

	def add_arguments(self, parser):
		parser.add_argument("--categories", type=int, default=10, help="Number of categories to ensure")
		parser.add_argument("--posts", type=int, default=100, help="Number of posts to create")
		parser.add_argument(
			"--seed", type=int, default=42, help="Random seed for deterministic sample data"
		)

	@transaction.atomic
	def handle(self, *args, **options):
		categories_target = max(1, options["categories"])
		posts_target = max(1, options["posts"])
		random.seed(options["seed"])

		author, _ = CustomUser.objects.get_or_create(
			username="seed_author",
			defaults={"email": "seed_author@example.com"},
		)
		if not author.has_usable_password():
			author.set_unusable_password()
			author.save(update_fields=["password"])

		created_categories = self._ensure_categories(categories_target)
		categories = list(Category.objects.order_by("id")[:categories_target])

		created_posts = self._create_posts(posts_target, author, categories)

		self.stdout.write(self.style.SUCCESS("Seeding completed."))
		self.stdout.write(f"Categories available for seeding: {len(categories)}")
		self.stdout.write(f"Categories newly created: {created_categories}")
		self.stdout.write(f"Posts newly created: {created_posts}")

	def _ensure_categories(self, categories_target):
		created = 0

		for name in DEFAULT_CATEGORY_NAMES:
			if Category.objects.count() >= categories_target:
				break
			_, was_created = Category.objects.get_or_create(name=name)
			if was_created:
				created += 1

		sequence = 1
		while Category.objects.count() < categories_target:
			extra_name = f"Category {sequence}"
			sequence += 1
			_, was_created = Category.objects.get_or_create(name=extra_name)
			if was_created:
				created += 1

		return created

	def _create_posts(self, posts_target, author, categories):
		created = 0
		topic_lines = [
			"Key ideas and practical takeaways.",
			"Common mistakes and how to avoid them.",
			"A short guide with actionable steps.",
			"Current trends and what they mean.",
			"Tools and techniques worth trying.",
		]

		for index in range(1, posts_target + 1):
			primary_category = random.choice(categories)
			title = f"Sample Post {index:03d} - {primary_category.name}"
			content = (
				f"This is generated sample content for {primary_category.name}. "
				f"Post number {index} created at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}. "
				f"{random.choice(topic_lines)}"
			)

			post = Post.objects.create(
				title=title,
				content=content,
				author=author,
				is_published=True,
			)

			# Assign only one category per post
			post.category.add(primary_category)
			primary_category.posts.add(post)

			created += 1

		return created

