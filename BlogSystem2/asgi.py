import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import blog.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BlogSystem2.settings")

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

# Create the ProtocolTypeRouter with proper sync handling
application = ProtocolTypeRouter(
    {
        # Django's ASGI application handles HTTP requests and automatically
        # runs them in sync context
        "http": django_asgi_app,
        # WebSocket consumers for real-time features
        "websocket": AuthMiddlewareStack(URLRouter(blog.routing.websocket_urlpatterns)),
    }
)
