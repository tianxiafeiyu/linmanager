from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, StreamingHttpResponse
from django.template import loader

from online_video.utils import m3u8


def index(request):
    return render(request, 'online_video/download.html')


def download(request):
    if request.method == 'POST':
        try:
            link = request.POST['cnm']
        except Exception:
            return HttpResponse('params error!')

        # 调用下载方法，生产临时文件，文件输出到指定路径
        print(link)
        result = m3u8.download(link, "video")
        if result:
            return HttpResponse('download success!')
        else:
            return HttpResponse('download failed!')
    else:
        return HttpResponse('method error!')


def ws_message(message):
    # ASGI WebSocket packet-received and send-packet message types
    # both have a "text" key for their textual data.
    message.reply_channel.send({
        "text": message.content['text'],
    })
