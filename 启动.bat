@echo off
chcp 65001 >nul
title 「邵新」辅助教育系统
cd /d "%~dp0"

set "PY大版本="
for /f "delims=" %%V in ('python -c "import sys;print(sys.version_info[0])" 2^>nul') do set "PY大版本=%%V"
if not "%PY大版本%"=="3" goto NOPY

set "PORT="
for /f "delims=" %%P in ('python "脚本\取端口.py" 2^>nul') do set "PORT=%%P"
if not defined PORT set "PORT=8765"


if not exist "本地服务.py" (
  echo.
  echo   找不到「本地服务.py」。
  echo   本文件和「本地服务.py」必须放在同一个文件夹（也就是 样本\ ）里，
  echo   单独把本文件挪出去是用不了的。
  echo.
  pause
  exit /b 1
)

set "VER="
for /f "delims=" %%V in ('python -c "from 地基 import 版本;print(版本.版本号)"') do set "VER=%%V"
if not defined VER set "VER=（读不出来）"

"%SystemRoot%\System32\netstat.exe" -an | "%SystemRoot%\System32\findstr.exe" ":%PORT%" | "%SystemRoot%\System32\findstr.exe" "LISTENING" >nul
if not errorlevel 1 goto PORTBUSY

echo.
echo  ========================================
echo    「邵新」辅助教育系统 v%VER%（内测）欢迎您的使用；
echo    创作者：JSON喵  
echo    ========================================
echo.
echo  正在启动本地服务...

start "「邵新」辅助教育系统-服务" /min python 本地服务.py

set /a N=0
:WAIT
"%SystemRoot%\System32\ping.exe" -n 2 127.0.0.1 >nul
set /a N+=1
"%SystemRoot%\System32\netstat.exe" -an | "%SystemRoot%\System32\findstr.exe" ":%PORT%" | "%SystemRoot%\System32\findstr.exe" "LISTENING" >nul
if not errorlevel 1 goto OK
if %N% lss 15 goto WAIT
goto NOSTART

:NOPY
echo.
echo  ========================================
echo    没有可用的 Python 3
echo  ========================================
echo.
echo   这个程序要用 Python 3 跑，但这台电脑上跑不起来 ——
echo   要么没装，要么只装了个「应用商店别名」（那个运行起来只会打开商店）。
echo   刚才如果弹出了一个「应用商店」窗口，那就是这个原因。
echo.
echo   怎么办：
echo     1. 去 python.org 下载 Python 3，装的时候务必勾上 Add python.exe to PATH
echo     2. 若本来装过 Python，只是被那个「别名桩」挡住了：
echo        设置 → 应用 → 高级应用设置 → 应用执行别名 → 把 python.exe / python3.exe 关掉
echo     3. 做完**再双击本文件**（这会儿程序还没起来，没有页面可以点）
echo.
pause
exit /b 1

:PORTBUSY
python -c "import urllib.request as u,sys;sys.exit(0 if '邵新' in u.urlopen('http://127.0.0.1:%PORT%/',timeout=3).read().decode('utf-8','ignore') else 1)" >nul 2>nul
if errorlevel 1 goto OCCUPIED

echo.
echo  ========================================
echo    「邵新」辅助教育系统 v%VER%（内测）欢迎您的使用；
echo    创作者：JSON喵  
echo  ========================================
echo.
echo  这台电脑上已经有一个「邵新」在跑着了 —— 直接把页面给你打开。
echo.
echo  · 若刚更新过程序：请先关掉旧的那个，再重新双击本文件。
echo      旧的在任务栏里，是最小化的「邵新 辅助教育系统-服务」窗口。
echo.
start "" http://127.0.0.1:%PORT%
pause
exit /b 0

:OCCUPIED
echo.
echo  端口 %PORT% 被别的程序占着了（不是邵新自己的服务）。
echo.
echo  怎么办：
echo    · 先把可能占着它的程序关掉（比如另一个 python 程序、别的本地服务），
echo      然后重新双击本文件；
echo    · 实在找不到是哪个程序占的，重启一次电脑最省事。
echo.
pause
exit /b 1

:NOSTART
echo.
echo  服务没起来（等了 15 秒，那个端口一直没人听）。
echo.
echo  去任务栏点开那个最小化的「邵新 辅助教育系统-服务」窗口，
echo  里面有一行报错原文，照它查：
echo    · 说「绑不上」     → 端口被别的程序占了
echo    · 说「找不到模块」 → Python 里缺依赖，照报错那句 pip install 装上
echo    · 窗口一闪就没了   → Python 本身有问题，回到上面重装一次
echo.
pause
exit /b 1

:OK
start "" http://127.0.0.1:%PORT%

echo.
echo  浏览器已打开：http://127.0.0.1:%PORT%
echo.
echo  · 若页面打不开，等两秒刷新一次
echo  · 停止服务：关闭那个最小化的「服务」窗口
echo.
echo  材料目录：材料\   技能包：技能包\   课件：课件输出\
echo.
pause
