@echo off
chcp 65001 >nul
title 给「邵新」装 WSL 里的 Ubuntu

net session >nul 2>&1
if errorlevel 1 (
  echo.
  echo  ========================================
  echo    需要管理员权限
  echo  ========================================
  echo.
  echo   关掉这个窗口，改成：
  echo     右键这个文件 →「以管理员身份运行」
  echo.
  pause
  exit /b 1
)

echo.
echo  ========================================
echo    正在给 WSL 装 Ubuntu
echo  ========================================
echo.
echo  会联网下载几百 MB，装完**必须重启电脑**。
echo  中途别关窗口。
echo.

wsl --install -d Ubuntu

echo.
echo  ----------------------------------------
echo  上面的命令跑完后：
echo    1. 重启电脑
echo    2. 打开「邵新」→ 环境配置 → 点刷新
echo       WSL 那一项会变成「已就绪」
echo    3. 桌面那个 wsl.exe 快捷方式，以后双击就进 Ubuntu
echo.
pause
