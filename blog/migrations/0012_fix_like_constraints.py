from django.db import migrations, models


def clean_invalid_and_duplicate_likes(apps, schema_editor):
    Like = apps.get_model("blog", "Like")
    database = schema_editor.connection.alias
    likes = Like.objects.using(database)

    # A like targets a post or a comment, never both. Existing rows that target
    # both are treated as comment likes because a comment already identifies its post.
    likes.filter(post__isnull=False, comment__isnull=False).update(post=None)
    likes.filter(post__isnull=True, comment__isnull=True).delete()

    for target_field in ("post_id", "comment_id"):
        duplicate_groups = (
            likes.exclude(**{target_field: None})
            .values("user_id", target_field)
            .annotate(total=models.Count("id"))
            .filter(total__gt=1)
        )
        for group in duplicate_groups.iterator():
            duplicate_ids = list(
                likes.filter(
                    user_id=group["user_id"],
                    **{target_field: group[target_field]},
                )
                .order_by("id")
                .values_list("id", flat=True)[1:]
            )
            likes.filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0011_alter_notification_post"),
    ]

    operations = [
        migrations.RunPython(
            clean_invalid_and_duplicate_likes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterUniqueTogether(
            name="like",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="like",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("comment__isnull", True), ("post__isnull", False))
                    | models.Q(("comment__isnull", False), ("post__isnull", True))
                ),
                name="blog_like_one_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="like",
            constraint=models.UniqueConstraint(
                condition=models.Q(("comment__isnull", True), ("post__isnull", False)),
                fields=("user", "post"),
                name="unique_user_post_like",
            ),
        ),
        migrations.AddConstraint(
            model_name="like",
            constraint=models.UniqueConstraint(
                condition=models.Q(("comment__isnull", False), ("post__isnull", True)),
                fields=("user", "comment"),
                name="unique_user_comment_like",
            ),
        ),
    ]
