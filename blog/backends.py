from django.contrib.auth.backends import ModelBackend

from blog.models import CustomUser


class EmailOrUsernameBackend(ModelBackend):
    """Allow authentication with either username or email in the username field."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get(CustomUser.USERNAME_FIELD)
        if not identifier or not password:
            return None

        user = (
            CustomUser.objects.filter(username__iexact=identifier).first()
            or CustomUser.objects.filter(email__iexact=identifier).first()
        )
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

