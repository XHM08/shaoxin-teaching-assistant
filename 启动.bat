@echo off
chcp 65001 >nul
title 「邵新」辅助教育系统
cd /d "%~dp0"

rem 判据必须是「能不能真跑」，不是「找不找得到」。
rem where python 在没装 Python 的 Win10/11 上照样命中 Microsoft Store 的
rem python.exe 别名桩（AppData\Local\Microsoft\WindowsApps 下那个），
rem 拿它当判据的后果是：检查通过 → 其实打开的是应用商店 → 端口永远不通。
rem 而且光看退出码也不够：有些 Windows/AppInstaller 版本的桩返回 0
rem （2026-10-06 团队反馈的那台机器就是），会把"跑起来了"误判成通过。所以这里看输出：
rem 只有真打印出主版本号 3 才算数（顺带挡掉 Python 2）。
set "PY大版本="
for /f "delims=" %%V in ('python -c "import sys;print(sys.version_info[0])" 2^>nul') do set "PY大版本=%%V"
if not "%PY大版本%"=="3" goto NOPY

rem 端口从 配置.json 读，启动器跟着配置走。
rem 原来这里兜底 8765（2026-10-23 评审 P1-1）：配置坏掉时它会去错端口找服务，
rem 表现成「起不来 / 端口被占」，真因看不见。现在拿不到就报错退出。
set "PORT="
for /f "delims=" %%P in ('python "脚本\取端口.py" 2^>nul') do set "PORT=%%P"
if not defined PORT (
  echo.
  echo   取不到服务端口：脚本\取端口.py 没给出数字。
  echo   通常是 地基\配置.py 或 配置.json 有问题。手敲这句能看到原始报错：
  echo       python 脚本\取端口.py
  echo.
  pause
  exit /b 1
)


if not exist "本地服务.py" (
  echo.
  echo   找不到「本地服务.py」。
  echo   本文件和「本地服务.py」必须放在同一个文件夹（也就是 样本\ ）里，
  echo   单独把本文件挪出去是用不了的。
  echo.
  pause
  exit /b 1
)

rem 版本号从 地基/版本.py 读，不在这里写死。
rem 写死就多出一个「版本号的更新点」，两边迟早对不上（开发日志 D-15；
rem 改这次之前正是：网页写 0.5、MCP 自报写 1.0）。
rem 这一句要调 python，所以必须放在上面那句 Python 检查之后：
rem 否则 python 是应用商店的别名桩时，这一句会把商店弹出来。
rem 它还必须放在端口检查之前：「已经有一个在跑」那一支同样要显示版本号。
set "VER="
for /f "delims=" %%V in ('python -c "from 地基 import 版本;print(版本.版本号)"') do set "VER=%%V"
if not defined VER set "VER=（读不出来）"

rem 起服务之前先探一次端口：已经有人在听 = 上一个实例还活着。
rem 不能等起来之后再探：那种探法分不清「我这次起的」和「早就有一个」，
rem 会立刻判成功并打开浏览器，而实际跑的是上一次的代码
rem （能力只在启动时加载，这个坑本项目已经栽过一轮）。
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

rem 计数用 goto 循环，不用 for / if(...) 块：
rem %N% 在 goto 循环里每次执行都会重新展开，所以这里不需要延迟展开；
rem 一旦有人把它挪进 ( ) 块，就必须改成 !N! 并开 enabledelayedexpansion。
set /a N=0
:WAIT
rem 等一秒的写法用 ping 而不是 timeout：
rem · timeout 在 stdin 被重定向时直接报「Input redirection is not supported」退出，
rem   一下也不等：循环会在几百毫秒里刷完，变成「探了 15 次但其实没等待」，
rem   服务只是慢一点起也会被判成失败（实测过）。
rem · 外部命令一律写全路径：项目在 Git Bash 的 PATH 下调试时 /usr/bin 排在 System32 前面，
rem   直接写命令名会命中 MSYS 的同名程序（GNU timeout 不认 /t，会一直刷 invalid time interval）。
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
echo   这个程序要用 Python 3 跑，但这台电脑上跑不起来：
echo   要么没装，要么只装了个「应用商店别名」（那个运行起来只会打开商店）。
echo   刚才如果弹出了一个「应用商店」窗口，那就是这个原因。
echo.
echo   怎么办：
echo     1. 去 python.org 下载 Python 3，装的时候务必勾上 Add python.exe to PATH
echo     2. 若本来装过 Python，只是被那个「别名桩」挡住了：
echo        设置 → 应用 → 高级应用设置 → 应用执行别名 → 把 python.exe / python3.exe 关掉
echo     3. 做完再双击本文件（这会儿程序还没起来，没有页面可以点）
echo.
pause
exit /b 1

:PORTBUSY
rem 端口上已经有人在听。先分辨是不是「我们自己」的服务：
rem   是自己 → 直接把页面打开（老师想做的本来就是打开邵新）；
rem   不是自己 → 才报错让人去处理。
rem 以前这里是一律硬退，后果很实在：只要这台电脑上已经有一个邵新在跑，
rem 再双击本文件就打不开，而且连欢迎界面都不出现。因为欢迎界面在这之后。
rem （2026-09-17 开发团队就是这么被挡住的，占着端口的正是开发机自己留下的一个验证用服务。）
python -c "import urllib.request as u,sys;sys.exit(0 if '邵新' in u.urlopen('http://127.0.0.1:%PORT%/',timeout=3).read().decode('utf-8','ignore') else 1)" >nul 2>nul
if errorlevel 1 goto OCCUPIED

echo.
echo  ========================================
echo    「邵新」辅助教育系统 v%VER%（内测）欢迎您的使用；
echo    创作者：JSON喵  
echo  ========================================
echo.
echo  这台电脑上已经有一个「邵新」在跑着了。直接把页面给你打开。
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
