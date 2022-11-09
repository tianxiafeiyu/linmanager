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
        file_id = m3u8.download(link, "video")
        if file_id:
            return render(request, "online_video/download_detail.html", {"file_id": file_id})
        else:
            return HttpResponse('download error!')
    else:
        return HttpResponse('method error!')
