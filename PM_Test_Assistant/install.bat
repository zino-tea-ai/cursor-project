@echo off
chcp 65001 >nul
echo 正在安装依赖...
cd /d "%~dp0"
pip install -r requirements.txt
echo.
echo 安装完成！
pause
