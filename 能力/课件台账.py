
import os
import time

from 地基 import 配置, 注册表


def 课件清单():
    目录 = 配置.取目录("课件输出")
    if not os.path.isdir(目录):
        return []
    条目 = []
    for 文件名 in sorted(os.listdir(目录)):
        路径 = os.path.join(目录, 文件名)
        if not os.path.isfile(路径) or not 文件名.endswith(".pptx"):
            continue
        if 文件名.startswith("_"):
            continue
        条目.append({
            "课件文件": 文件名,
            "大小(字节)": os.path.getsize(路径),
            "生成时间": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(路径))),
        })
    return 条目


def 处理列表():
    条目 = 课件清单()
    return {
        "提示": "共 " + str(len(条目)) + " 份课件。",
        "条目": 条目,
        "正文": "" if 条目 else "还没有生成过课件。",
    }


注册表.登记(
    代号="课件台账",
    标题="课件台账",
    说明="查看已经生成过的课件文件",
    参数=[],
    处理函数=处理列表,
)
