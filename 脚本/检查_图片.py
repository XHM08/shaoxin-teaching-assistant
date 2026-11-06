
import io
import os
import shutil
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 图片

问卷目录 = os.environ.get("QUESTIONNAIRE_DIR", "")

失败 = []
条数 = 0
跳过 = []


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 记跳过(名, 说明=""):
    global 条数
    条数 += 1
    跳过.append(名)
    print("  … " + 名 + "（跳过：" + 说明 + "）")


def 造图(路, 尺寸=(2736, 3648), 朝向=None, 内容="问卷照片占位"):
    from PIL import Image
    图 = Image.new("RGB", 尺寸, (240, 236, 228))
    for 行 in range(0, 尺寸[1], 40):
        for 列 in range(0, 尺寸[0], 7):
            图.putpixel((列, 行), (40, 40, 60))
    if 朝向 is not None:
        信息 = 图.getexif()
        信息[274] = 朝向
        图.save(路, "JPEG", quality=92, exif=信息)
    else:
        图.save(路, "JPEG", quality=92)


def 主():
    临时 = tempfile.mkdtemp(prefix="图片-")
    try:
        记("① 阈值符合经验：长边 1600、质量 85、最短边长 100",
           图片.长边上限 == 1600 and 图片.JPEG质量 == 85 and 图片.最短边长 == 100,
           (图片.长边上限, 图片.JPEG质量, 图片.最短边长))

        源 = os.path.join(临时, "大.jpg")
        造图(源)
        目标 = os.path.join(临时, "出", "大.jpg")
        果 = 图片.预处理(源, 目标)
        记("② 大图被处理了", 果["ok"] and 果["已处理"], 果.get("错误"))
        记("③ 长边 ≤ 1600", max(果["新尺寸"]) <= 图片.长边上限, 果["新尺寸"])
        记("④ 体积明显变小且 ≤ 300 KB",
           果["新字节"] <= 300 * 1024 and 果["新字节"] < 果["原字节"], 果["新字节"])
        比原 = 果["原尺寸"][0] / float(果["原尺寸"][1])
        比新 = 果["新尺寸"][0] / float(果["新尺寸"][1])
        记("⑤ 长宽比与原图一致（误差 < 0.005）", abs(比原 - 比新) < 0.005, (比原, 比新))

        小源 = os.path.join(临时, "小.jpg")
        造图(小源, 尺寸=(800, 1000))
        小目标 = os.path.join(临时, "出", "小.jpg")
        果2 = 图片.预处理(小源, 小目标)
        同 = open(小源, "rb").read() == open(小目标, "rb").read()
        记("⑥ 不需要处理的小图：直接复制、字节一致、标记为未处理",
           果2["ok"] and not 果2["已处理"] and 同, (果2["已处理"], 同))

        旋源 = os.path.join(临时, "旋.jpg")
        造图(旋源, 尺寸=(1200, 1600), 朝向=6)
        旋目标 = os.path.join(临时, "出", "旋.jpg")
        果3 = 图片.预处理(旋源, 旋目标)
        记("⑦ EXIF 转正：输出宽高互换（1200×1600 → 1600×1200），且标记为已处理",
           果3["ok"] and 果3["已处理"] and 果3["原尺寸"] == (1200, 1600)
           and 果3["新尺寸"] == (1600, 1200), (果3["原尺寸"], 果3["新尺寸"]))

        for 参数名, 值, 说 in (("长边", 0, "长边 0"), ("长边", -5, "长边负数"), ("质量", 10, "质量 10")):
            坏 = os.path.join(临时, "坏参.jpg")
            果4 = 图片.预处理(源, 坏, **{参数名: 值})
            记("⑧ %s 被拒，且中文说明（不产出一张 1 像素的图）" % 说,
               (not 果4["ok"]) and ("长边" in 果4["错误"] or "质量" in 果4["错误"]), 果4["错误"])

        假 = os.path.join(临时, "其实是文本.jpg")
        io.open(假, "w", encoding="utf-8").write("我不是图片")
        果5 = 图片.预处理(假, os.path.join(临时, "出", "假.jpg"))
        记("⑨ 打不开的图给中文原因，不抛英文 traceback",
           (not 果5["ok"]) and "打不开" in 果5["错误"], 果5["错误"])

        批 = os.path.join(临时, "批")
        os.makedirs(批, exist_ok=True)
        造图(os.path.join(批, "a.jpg"), 尺寸=(600, 800))
        造图(os.path.join(批, "a.png"), 尺寸=(600, 800))
        os.rename(os.path.join(批, "a.png"), os.path.join(批, "a2.png"))
        同批 = os.path.join(临时, "批2")
        os.makedirs(同批, exist_ok=True)
        造图(os.path.join(同批, "撞.jpg"), 尺寸=(600, 800))
        造图(os.path.join(同批, "撞.png"), 尺寸=(600, 800))
        出1 = 图片.批量(批, os.path.join(临时, "批出"))
        记("⑩ 批量正常：两个都出，png 也认", len(出1["清单"]) == 2 and all(x["ok"] for x in 出1["清单"]),
           [x.get("文件名") for x in 出1["清单"]])
        出2 = 图片.批量(同批, os.path.join(临时, "批出2"))
        记("⑪ 同名不同扩展名：直接报错，不静默覆盖", bool(出2["错误"]), 出2)
        出3 = 图片.批量(os.path.join(临时, "不存在的目录"), os.path.join(临时, "批出3"))
        记("⑫ 源目录不存在：中文说明", "不存在" in 出3["错误"], 出3["错误"])
        io.open(os.path.join(批, "扫描.heic"), "w").write("x")
        出4 = 图片.批量(批, os.path.join(临时, "批出4"))
        记("⑬ 不支持的格式出现在「跳过」里，不静默消失",
           "扫描.heic" in 出4["跳过"], 出4["跳过"])

        if os.path.isdir(问卷目录):
            真 = sorted(名 for 名 in os.listdir(问卷目录) if 名.lower().endswith((".jpg", ".jpeg")))
            if 真:
                真源 = os.path.join(问卷目录, 真[0])
                真目标 = os.path.join(临时, "真.jpg")
                果6 = 图片.预处理(真源, 真目标)
                记("⑭ 真实问卷照片：长边 ≤1600、≤300 KB、比例不变",
                   果6["ok"] and max(果6["新尺寸"]) <= 1600 and 果6["新字节"] <= 300 * 1024
                   and abs(果6["原尺寸"][0] / 果6["原尺寸"][1] - 果6["新尺寸"][0] / 果6["新尺寸"][1]) < 0.005,
                   (果6["原尺寸"], 果6["新尺寸"], 果6["新字节"]))
            else:
                记跳过("⑭ 真实问卷照片", "目录里没有 jpg")
        else:
            记跳过("⑭ 真实问卷照片", "问卷目录不在")
    except Exception as 错:
        记("检查本身跑完了", False, "%s: %s" % (type(错).__name__, 错))
    finally:
        shutil.rmtree(临时, ignore_errors=True)

    print()
    print("全部 %d 项通过" % (条数 - len(跳过)) if not 失败 else "通过 %d / 共 %d（跳过 %d）"
          % (条数 - len(失败) - len(跳过), 条数, len(跳过)))
    return 0 if not 失败 else 1


if __name__ == "__main__":
    sys.exit(主())
