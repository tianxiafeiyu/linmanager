from django.shortcuts import render


def index(request):
    app_list = [
        {
            "index": "admin",
            "name": "系统管理",
        },
        {
            "index": "polls",
            "name": "投票系统",
        },
        {
            "index": "ov",
            "name": "在线视频下载",
        },
        {
            "index": "chat",
            "name": "聊天室",
        }
    ]

    tool_list = [
        {
            "index": "https://c.runoob.com/front-end/61/",
            "name": "菜鸟工具",
        }
    ]
    return render(request, 'index.html', {"app_list": app_list, "tool_list": tool_list})
