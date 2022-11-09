from django.urls import re_path

from online_video import consumers

websocket_urlpatterns = [
    re_path(r"ws/download/(?P<file_id>\w+)/$", consumers.DownloadConsumer.as_asgi()),
]
