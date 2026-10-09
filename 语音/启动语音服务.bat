@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY大版本="
for /f "delims=" %%V in ('python -c "import sys;print(sys.version_info[0])" 2^>nul') do set "PY大版本=%%V"
if not "%PY大版本%"=="3" (
  echo [语音] 这里的 python 跑不起来 —— 多半是没装，或只装了个「应用商店别名桩」。
  echo         刚才如果弹出了应用商店窗口，就是这个原因。
  echo         怎么办：先双击 启动.bat（它会告诉你怎么装 Python）；
  echo                 或者把 Python 装好并勾上 Add python.exe to PATH，再来双击本文件。
  pause
  exit /b 1
)

python "%~dp0启动语音服务.py"
echo.
pause
