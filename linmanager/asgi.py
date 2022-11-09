"""
ASGI config for linmanager project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

import chat.routing
import online_video.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linmanager.settings')


def get_all_ws_router():
    routers = []
    routers.extend(chat.routing.websocket_urlpatterns)
    routers.extend(online_video.routing.websocket_urlpatterns)
    return routers


application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(get_all_ws_router()))
        ),
        # Just HTTP for now. (We can add other protocols later.)
    }
)
