
import json
import os
import queue
import threading
import time
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
from tkinter import simpledialog

地址 = "http://127.0.0.1:8765"
轮询间隔毫秒 = 2000
请求超时 = 5
回应超时 = 60


class 窗口:
    def __init__(self):
        self.根 = tk.Tk()
        self.根.title("课堂留言 · 邵新")
        self.根.attributes("-topmost", True)
        self.根.geometry("400x470+40+40")
        self.根.minsize(320, 260)

        tk.Label(self.根, text="课上接一句话（按下面的键）", anchor="w",
                 font=("Microsoft YaHei", 11, "bold")).pack(fill="x", padx=10, pady=(8, 2))
        self.状态 = tk.Label(self.根, text="正在连邵新服务…", anchor="w", fg="#6b7280",
                          font=("Microsoft YaHei", 9))
        self.状态.pack(fill="x", padx=10)

        self.列表 = tk.Text(self.根, wrap="word", font=("Microsoft YaHei", 10),
                          background="#fbfcfe", relief="flat")
        self.列表.pack(fill="both", expand=True, padx=10, pady=6)
        self.列表.configure(state="disabled")

        条 = tk.Frame(self.根)
        条.pack(fill="x", padx=10, pady=(0, 10))
        self.接键 = tk.Button(条, text="接受学生发言（按一下）", command=self.接受学生发言,
                             background="#1b4f9c", foreground="white",
                             font=("Microsoft YaHei", 10, "bold"), relief="flat",
                             padx=10, pady=6)
        self.接键.pack(side="left")
        tk.Button(条, text="清屏", command=self.清屏).pack(side="left", padx=6)
        tk.Button(条, text="现在刷新", command=self.催一下).pack(side="left")

        self.已看到 = 0
        self.队 = queue.Queue()
        self.要停 = False
        self.忙 = False
        self.粘住 = False
        self.连不上 = False
        self.出错 = False
        self.根.protocol("WM_DELETE_WINDOW", self.关)
        自检秒数 = os.environ.get("WINDOW_SELFTEST_SECONDS")
        if 自检秒数:
            try:
                self.根.after(int(float(自检秒数) * 1000), self.关)
            except ValueError:
                pass
        self.根.after(200, self.收队)
        threading.Thread(target=self.轮询, daemon=True).start()

    def 轮询(self):
        while not self.要停:
            self.取()
            time.sleep(轮询间隔毫秒 / 1000.0)

    def 取(self):
        try:
            请求 = urllib.request.Request(地址 + urllib.parse.quote("/api/取留言")
                                     + "?since=%d" % self.已看到)
            with urllib.request.urlopen(请求, timeout=请求超时) as 响应:
                数据 = json.loads(响应.read().decode("utf-8"))
            self.队.put(("留言", 数据))
        except Exception as 异常:
            self.队.put(("错", type(异常).__name__ + "：" + str(异常)[:60]))

    def 发一条(self, 路径, 体, 超时=请求超时):
        请求 = urllib.request.Request(地址 + urllib.parse.quote(路径),
                       data=json.dumps(体, ensure_ascii=False).encode("utf-8"),
                       headers={"Content-Type": "application/json", "Origin": 地址})
        try:
            with urllib.request.urlopen(请求, timeout=超时) as 响应:
                return json.loads(响应.read().decode("utf-8"))
        except urllib.error.HTTPError as 异常:
            try:
                详情 = json.loads(异常.read().decode("utf-8")).get("错误", "")
            except Exception:
                详情 = ""
            raise RuntimeError(详情 or ("服务回了 " + str(异常.code)))

    def 接受学生发言(self):
        谁 = simpledialog.askstring("接受学生发言", "谁说的？（可以不填）", parent=self.根)
        if 谁 is None:
            return
        话 = simpledialog.askstring("接受学生发言", "学生说了什么？", parent=self.根)
        if 话 is None or not 话.strip():
            return
        self.忙 = True
        self.粘住 = False
        self.接键.configure(state="disabled", text="正在让邵新回应…")
        self.状态.configure(text="已收到，正在让邵新回应…", fg="#6b7280")
        threading.Thread(target=self.递交, args=(谁, 话), daemon=True).start()

    def 递交(self, 谁, 话):
        try:
            记 = self.发一条("/api/记留言", {"谁": 谁, "内容": 话, "来源": "窗口"})
            回 = self.发一条("/api/课堂回应", {"序号": 记.get("序号")}, 超时=回应超时)
            self.队.put(("提示", "邵新回应：" + str(回.get("回答") or "")[:40]))
        except Exception as 异常:
            self.队.put(("提示", "没成：" + str(异常)[:70], True))
        finally:
            self.队.put(("复位", ""))

    def 收队(self):
        try:
            while True:
                类, 数据, *其余 = self.队.get_nowait()
                坏消息 = bool(其余 and 其余[0])
                if 类 == "留言":
                    self.画(数据)
                elif 类 == "错":
                    self.连不上 = True
                    self.状态.configure(text="连不上邵新服务（" + 数据 + "）：先双击 启动.bat",
                                     fg="#a32020")
                elif 类 == "提示":
                    self.状态.configure(text=数据, fg=("#a32020" if 坏消息 else "#14663a"))
                    self.粘住 = True
                    self.根.after(15000, self.解粘)
                elif 类 == "清掉了":
                    self.列表.configure(state="normal")
                    self.列表.delete("1.0", "end")
                    self.列表.configure(state="disabled")
                    self.已看到 = 0
                elif 类 == "复位":
                    self.忙 = False
                    self.接键.configure(state="normal", text="接受学生发言（按一下）")
                    self.催一下()
        except queue.Empty:
            pass
        except Exception as 异常:
            try:
                self.出错 = True
                self.状态.configure(text="窗口刷新出错了（" + type(异常).__name__ + "："
                                     + str(异常)[:50] + "）", fg="#a32020")
            except Exception:
                pass
        finally:
            if not self.要停:
                self.根.after(200, self.收队)

    def 画(self, 数据):
        self.连不上 = False
        self.出错 = False
        新的 = 数据.get("留言") or []
        共 = int(数据.get("共") or 0)
        丢过 = int(数据.get("丢过") or 0)
        if 新的:
            self.列表.configure(state="normal")
            for 一条 in 新的:
                来源 = 一条.get("来源") or "窗口"
                self.列表.insert("1.0", "%s  %s（%s）\n%s\n\n"
                               % (一条.get("时间", ""), 一条.get("谁", ""), 来源,
                                  一条.get("内容", "")))
            self.列表.configure(state="disabled")
            self.已看到 = max(self.已看到, max(int(x.get("序号") or 0) for x in 新的))
        提示 = "服务在跑；共 %d 条" % 共
        if 丢过:
            提示 += "（有 %d 条太久没看已被丢掉）" % 丢过
        if not (self.忙 or self.粘住 or self.连不上 or self.出错):
            self.状态.configure(text=提示, fg="#6b7280")

    def 催一下(self):
        threading.Thread(target=self.取, daemon=True).start()

    def 解粘(self):
        self.粘住 = False

    def 清屏(self):
        threading.Thread(target=self._清屏, daemon=True).start()

    def _清屏(self):
        try:
            self.发一条("/api/清留言", {})
        except Exception as 异常:
            self.队.put(("提示", "清屏没成：" + str(异常)[:60] + "（窗口里这些先留着）", True))
            return
        self.队.put(("清掉了", ""))

    def 关(self):
        self.要停 = True
        self.根.destroy()

    def 跑(self):
        self.根.mainloop()


if __name__ == "__main__":
    窗口().跑()
