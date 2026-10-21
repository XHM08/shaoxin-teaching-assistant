@echo off
chcp 65001 >nul
rem 双击外壳。真正的启动逻辑在 启动语音服务.py：
rem 为什么不在这个 bat 里解析路径：cmd 在 65001 代码页下 for /f 读文件会把行尾 CR
rem 一起塞进变量，症状是"文件明明在，bat 却说没装"。那边文件头写得更细。
rem 本文件要 UTF-8 无 BOM + CRLF，改它的时候别把编码改掉。
cd /d "%~dp0"

rem 判据同 启动.bat：看输出，不只看退出码。没装 Python 的 Win10/11 上，
rem `python` 会命中 WindowsApps 里的应用商店别名桩；它打印一句"Python was not found…"。
rem 有些版本的桩返回 0，只看退出码就会误判通过，于是弹出一个应用商店窗口、什么也没发生。
set "PY大版本="
for /f "delims=" %%V in ('python -c "import sys;print(sys.version_info[0])" 2^>nul') do set "PY大版本=%%V"
if not "%PY大版本%"=="3" (
  echo [语音] 这里的 python 跑不起来。多半是没装，或只装了个「应用商店别名桩」。
  echo         刚才如果弹出了应用商店窗口，就是这个原因。
  echo         怎么办：先双击 启动.bat（它会告诉你怎么装 Python）；
  echo                 或者把 Python 装好并勾上 Add python.exe to PATH，再来双击本文件。
  pause
  exit /b 1
)

python "%~dp0启动语音服务.py"
echo.
pause
