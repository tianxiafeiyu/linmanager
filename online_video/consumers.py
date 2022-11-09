import asyncio
import json
import threading
import time

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from online_video.utils.m3u8 import PROGRESS_MAP


class DownloadConsumer(WebsocketConsumer):
    # websocket建立连接时执行方法
    def connect(self):
        self.file_id = self.scope['url_route']['kwargs']['file_id']
        # 将当前频道加入频道组
        async_to_sync(self.channel_layer.group_add)(
            self.file_id,
            self.channel_name
        )

        # 接受所有websocket请求
        self.accept()

        threading.Thread(target=self.post_msg).start()

    def post_msg(self):
        # 通过websocket发送消息到客户端
        print("start web")
        times = 0
        while True and times < 300:
            print(PROGRESS_MAP)
            progress = PROGRESS_MAP.get(self.file_id, None)
            if progress is None:
                break

            async_to_sync(self.channel_layer.group_send)(
                self.file_id,
                {
                    'type': 'system_message',
                    'message': progress
                }
            )

            times += 1
            time.sleep(1)
        print("stop web")
        async_to_sync(self.channel_layer.group_discard)(
            self.file_id,
            self.channel_name
        )
        self.close()

    def system_message(self, event):
        print(event)
        message = event['message']

        # Send message to WebSocket单发消息
        self.send(text_data=json.dumps({
            'message': '{:.2f}%'.format(message)
        }))
