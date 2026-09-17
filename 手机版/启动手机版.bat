@echo off
chcp 65001 >nul
title 「邵新」辅助教育系统 · 手机版
cd /d "%~dp0"

set "PROJ=%~dp0..\样本"
if not exist "%PROJ%\本地服务.py" (
  echo.
  echo   找不到：%PROJ%\本地服务.py
  echo.
  echo   「手机版」要和「样本」放在同一层里（都在桌面上），不要单独挪走。
  echo.
  pause
  exit /b 1
)

python -c "import sys;sys.exit(0 if sys.version_info[0] == 3 else 1)" >nul 2>nul
if errorlevel 1 (
  echo.
  echo   没有可用的 Python 3
  echo.
  echo   要么没装，要么只装了个「应用商店别名」（那个运行起来只会打开商店）。
  echo   刚才如果弹出了「应用商店」窗口，那就是这个原因。
  echo.
  echo   做法：去 python.org 装 Python 3，装的时候务必勾上 Add python.exe to PATH，
  echo   装完**再双击本文件**。
  echo.
  pause
  exit /b 1
)

set SHAOXIN_HOST=0.0.0.0

echo.
echo  ========================================
echo    「邵新」辅助教育系统 · 手机版
echo  ========================================
echo.
echo  用法：
echo    1. 手机连上跟这台电脑**同一个 Wi-Fi**
echo    2. 看下面打印出来的「手机打开」那一行，把整个地址输进手机浏览器
echo    3. 一定要带上 ?t= 后面那一串，否则打不开
echo.
echo  停止：关闭这个窗口，或者按 Ctrl+C
echo.
echo  手机打不开怎么办：多半是 Windows 防火墙拦了 Python 的入站连接。
echo  ⚠ 如果你的 Wi-Fi 被 Windows 当成「公用网络」（很常见），
echo    只勾「专用」那一列是没用的 —— 这一点写错了会白折腾半天。
echo    正确做法写在同目录的「说明.md」里。
echo.

cd /d "%PROJ%"
python 本地服务.py

echo.
echo  服务已停止。
pause
