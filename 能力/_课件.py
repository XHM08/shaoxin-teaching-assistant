
import json
import os
import shutil
import time

from 地基 import 幻灯片, 大模型, 提示词, 课件, 技能包, 配置

最多配图 = 6


def 上下文表(上下文=None):
    上下文 = 上下文 if isinstance(上下文, dict) else {}
    上下文.setdefault("警告", [])
    上下文.setdefault("配图页", [])
    return 上下文


def 可配图(上限=最多配图):
    根 = 配置.取目录("材料")
    全部 = []
    if os.path.isdir(根):
        for 目录, 子目录们, 文件们 in os.walk(根):
            子目录们.sort()
            for 名 in sorted(文件们):
                if os.path.splitext(名)[1].lower() in 幻灯片.可插图后缀:
                    全部.append(os.path.relpath(os.path.join(目录, 名), 根).replace(os.sep, "/"))
    清单 = 全部[:上限]
    说明 = "" if len(全部) <= len(清单) else \
        "（材料/ 里一共有 %d 张图，这次只发前 %d 张；以这份清单为准）" % (len(全部), len(清单))
    return 清单, 说明


def 图片清单文字(清单, 说明=""):
    if not 清单:
        return '（材料/ 里还没有图片，这一课不用配图：所有页的 图 都填 ""）'
    行 = ["一共有 %d 张图可用，文件名要一个字不差地照抄下面这个写法：" % len(清单)]
    for 号, 名 in enumerate(清单, 1):
        行.append("  %d. %s" % (号, 名))
    if 说明:
        行.append(说明)
    return "\n".join(行)


def 能带图吗(服务商=None):
    try:
        名字, 条目 = 大模型.选服务商(大模型.读配置(), 服务商)
    except Exception:
        return False
    return 大模型.服务商支持图(条目)


def 无图说明():
    return '（这次没有附上任何图片，不要配图：每一页的 图 都填 ""）'


def 生成(技能包代号, 课题, 页数=8, 上下文=None, 服务商=None):
    上下文 = 上下文表(上下文)
    警告 = 上下文["警告"]
    清单, 说明 = 可配图()
    带图 = bool(清单) and 能带图吗(服务商)
    if 清单 and not 带图:
        警告.append("当前服务商没标「支持图片」（或配置不完整），这次只把图的名字告诉了模型，"
                  "它并没有真看见图：要让它看着图写讲稿，请在 服务商.json 里换成标了 "
                  '"支持图片": true 的视觉模型后重新生成')
    elif 清单:
        警告.append("这次随提示词发了 %d 张图给模型（是它自己看图写讲稿，不是发给别的什么人）"
                  % len(清单))

    提示词原文 = 提示词.填充(
        提示词.读取("课件生成"),
        技能包=技能包.读技能包全文(技能包代号),
        课题=课题,
        页数=str(页数).strip() or "8",
        图片清单=(图片清单文字(清单, 说明) if 带图 else 无图说明()),
        看图说明=("上面这些图已经附在提示词后面了，你能直接看到，请看着它们写讲稿。"
                if 带图 else
                "这次没有附上图片本身，你看不到图，所以不要把图里的内容写进讲稿，"
                '也不要配图（每一页的 图 都填 ""）。'),
    )
    if not 带图:
        return 课件.取出JSON(大模型.问(提示词原文, 服务商=服务商))

    根 = 配置.取目录("材料")
    带标签 = [("文件名：" + 名, os.path.join(根, 名)) for 名 in 清单]
    return 课件.取出JSON(大模型.问(提示词原文, 图=带标签, 服务商=服务商))


def 生成记录路径(课件路径):
    return str(课件路径) + ".生成记录.json"


def 记生成记录(课件路径):
    路径 = 生成记录路径(课件路径)
    try:
        with open(路径, "w", encoding="utf-8") as 文件:
            json.dump({"指纹": 课件.指纹(课件路径), "时刻": time.time()}, 文件,
                      ensure_ascii=False, indent=1)
    except OSError as 异常:
        raise RuntimeError("课件已经生成好了，但生成记录写不出去（" + type(异常).__name__
                         + "：" + str(异常)[:60] + "）。"
                         "不写这条记录，下次就会把你没改过的课件当成改过了。"
                         "所以这次不能默默放过。请检查 课件输出/ 是否可写。") from 异常


def 老师改过吗(课件路径):
    if not os.path.isfile(str(课件路径)):
        return False, "本来就没有这份文件"
    记录路径 = 生成记录路径(课件路径)
    if not os.path.isfile(记录路径):
        return True, "这份课件不是邵新生成的（没有生成记录）"
    try:
        with open(记录路径, "r", encoding="utf-8") as 文件:
            旧 = json.load(文件).get("指纹") or {}
    except Exception:
        return True, "生成记录读不出来"
    现在 = 课件.指纹(课件路径)
    if not 课件.指纹一样吗(旧, 现在):
        return True, "文件内容与我们生成的那版不一样了"
    return False, ""


def 备份成(课件路径):
    return 课件.备份成(课件路径)


def 保存pptx(数据, 技能包代号, 课题, 上下文=None):
    文件名 = 课件.安全文件名(技能包代号 + "-" + 课题) + ".pptx"
    输出目录 = 配置.取目录("课件输出")
    os.makedirs(输出目录, exist_ok=True)
    路径 = os.path.join(输出目录, 文件名)
    上下文 = 上下文表(上下文)

    改过, 为什么 = 老师改过吗(路径)
    if 改过:
        try:
            备份名 = 备份成(路径)
            上下文["警告"].append("这份课件不像是我们刚生成的那版（%s），"
                              "我先把现在这份存成 %s，再生成新的" % (为什么, 备份名))
        except Exception as 异常:
            raise RuntimeError("这份课件你改过（" + 为什么 + "），但要备份它时出错了（"
                             + type(异常).__name__ + "：" + str(异常)[:60]
                             + "）：为免把你的改动弄丢，这次先不生成。"
                             "你可以先把那份课件改名或挪走，再重试。") from 异常

    幻灯片.写出(数据, 路径, 上下文)
    记生成记录(路径)
    return 文件名
