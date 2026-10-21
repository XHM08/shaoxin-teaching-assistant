
import io
import json
import os
import shutil
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 审计, 配置

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 行们(路径):
    if not os.path.isfile(路径):
        return []
    with io.open(路径, encoding="utf-8") as 文件:
        return [x for x in 文件.read().splitlines() if x.strip()]


def 接管(目录, 上限MB=10.0, 开=True):
    审计.配置.取目录 = lambda 名: 目录
    审计.配置.读取 = lambda: ({"审计": {"上限MB": 上限MB}} if 开 else {"审计": False})
    if 审计.配置.取目录("日志") != 目录:
        raise RuntimeError("配置替换没生效：审计内部用的不是同一个 配置 模块对象，"
                           "再跑下去会写进真实 日志/，中止")


def 主():
    原取目录, 原读取 = 配置.取目录, 配置.读取
    原记录 = list(审计.最近记录)
    临时们 = []
    try:
        记("① 默认阈值是 20 MB（读常量，不读可能被改过的配置）",
           审计.默认上限MB == 20.0, 审计.默认上限MB)

        甲 = tempfile.mkdtemp(prefix="审计不轮转-")
        临时们.append(甲)
        接管(甲, 10.0)
        记("② 替换生效：审计确实在用临时目录", 审计.配置.取目录("日志") == 甲)
        记("③ 配置里的 上限MB 生效", 审计.取上限MB() == 10.0, 审计.取上限MB())
        for 序 in range(5):
            审计.记一笔("自检", {"序": 序})
        主甲 = os.path.join(甲, "审计.jsonl")
        记("④ 反向验：没到阈值不轮转（不是一写就换文件）",
           not os.path.isdir(os.path.join(甲, "_备份")) and len(行们(主甲)) == 5,
           "主文件 %d 行" % len(行们(主甲)))

        乙 = tempfile.mkdtemp(prefix="审计轮转-")
        临时们.append(乙)
        接管(乙, 0.0005)
        for 序 in range(12):
            审计.记一笔("自检", {"序": 序})
        主乙 = os.path.join(乙, "审计.jsonl")
        备份目录 = os.path.join(乙, "_备份")
        备份们 = sorted(os.listdir(备份目录)) if os.path.isdir(备份目录) else []
        备份行数 = sum(len(行们(os.path.join(备份目录, 名))) for 名 in 备份们)
        记("⑤ 超过阈值会轮转：备份目录里有文件且有内容",
           len(备份们) >= 1 and 备份行数 >= 1, "备份 %d 个 / %d 行" % (len(备份们), 备份行数))
        记("⑥ 历史一行不少（备份 ≥1 行，且备份 + 当前 = 写过的 12 条）",
           备份行数 >= 1 and 备份行数 + len(行们(主乙)) == 12,
           "%d + %d" % (备份行数, len(行们(主乙))))
        记("⑦ 当前文件还在写（轮转没把写入一起停掉）", len(行们(主乙)) >= 1, len(行们(主乙)))

        坏行 = []
        for 名 in 备份们:
            for 行 in 行们(os.path.join(备份目录, 名)):
                try:
                    json.loads(行)
                except json.JSONDecodeError:
                    坏行.append((名, 行[:40]))
        记("⑧ 备份里每一行都是合法 JSON", not 坏行, 坏行[:2])

        记("⑨ 备份文件名带时间戳且是 .jsonl",
           all(名.startswith("审计.") and 名.endswith(".jsonl") for 名 in 备份们), 备份们[:2])


        丙 = tempfile.mkdtemp(prefix="审计重名-")
        临时们.append(丙)
        待轮 = os.path.join(丙, "审计.jsonl")
        with io.open(待轮, "w", encoding="utf-8") as 文件:
            文件.write('{"a": 1}\n')
        路1 = 审计.轮转(待轮, 丙)
        with io.open(待轮, "w", encoding="utf-8") as 文件:
            文件.write('{"a": 2}\n')
        路2 = 审计.轮转(待轮, 丙)
        记("⑩ 同一秒内连轮两次，得到两个不同备份且都有内容",
           路1 != 路2 and os.path.getsize(路1) > 0 and os.path.getsize(路2) > 0, (路1, 路2))
        记("⑪ 轮转后原文件不在了（不是「轮转完还留着旧内容」）", not os.path.exists(待轮))

        尾巴 = 审计.读日志尾巴(50)
        记("⑫ 读日志尾巴只读当前文件，不把备份算进来",
           len(尾巴) == len(行们(主乙)), "%d vs %d" % (len(尾巴), len(行们(主乙))))

        丁 = tempfile.mkdtemp(prefix="审计关-")
        临时们.append(丁)
        接管(丁, 10.0, 开=False)
        审计.记一笔("自检关")
        记("⑬ 审计关掉时一个文件都不写",
           not os.path.exists(os.path.join(丁, "审计.jsonl")), os.listdir(丁))
    except Exception as 错:
        记("检查本身跑完了", False, "%s: %s" % (type(错).__name__, 错))
    finally:
        配置.取目录, 配置.读取 = 原取目录, 原读取
        审计.最近记录[:] = 原记录
        for 目 in 临时们:
            shutil.rmtree(目, ignore_errors=True)

    print()
    print("全部 %d 项通过" % 条数 if not 失败 else "通过 %d / 共 %d" % (条数 - len(失败), 条数))
    return 0 if not 失败 else 1


if __name__ == "__main__":
    sys.exit(主())
