@echo off
chcp 65001 >nul
rem 课堂悬浮窗（老师桌面上的小窗）。UTF-8 无 BOM + CRLF，改它时别把编码改掉。
rem 它只是双击外壳：真正的逻辑在 课堂悬浮窗.py（标准库 Tkinter，不用装东西）。
rem 这个窗要一直置顶，所以上课前双击一次、开着别关；下课关掉即可。
cd /d "%~dp0"

rem 判据同 启动.bat：看输出，不只看退出码。没装 Python 的 Win10/11 上，
rem `python` 会命中 WindowsApps 里的应用商店别名桩；它打印一句"Python was not found…"。
rem 有些版本的桩返回 0，只看退出码就会误判通过，于是弹出一个应用商店窗口、什么也没发生。
set "PY大版本="
for /f "delims=" %%V in ('python -c "import sys;print(sys.version_info[0])" 2^>nul') do set "PY大版本=%%V"
if not "%PY大版本%"=="3" (
  echo [悬浮窗] 这里的 python 跑不起来。多半是没装，或只装了个「应用商店别名桩」。
  echo          刚才如果弹出了应用商店窗口，就是这个原因。
  echo          怎么办：先双击 启动.bat（它会告诉你怎么装 Python），装完回来再双击本文件。
  pause
  exit /b 1
)

python "%~dp0课堂悬浮窗.py"
echo.
pause
