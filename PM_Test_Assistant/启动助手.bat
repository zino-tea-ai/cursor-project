@echo off
chcp 65001 >nul
echo 正在启动 PM测试助手...
cd /d "%~dp0"
python main.py
pause
