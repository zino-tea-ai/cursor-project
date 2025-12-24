@echo off
chcp 65001 >nul
echo ================================================
echo 清理残留文件
echo ================================================
echo.

cd /d "C:\Users\WIN\Desktop\Cursor Project"

echo 删除 V1 主目录 (PM_Screenshot_Tool)...
rmdir /s /q "PM_Screenshot_Tool" 2>nul

echo 删除 pm-tool-v2 残留...
rmdir /s /q "pm-tool-v2" 2>nul

echo 删除 nul 文件...
del /f /q "nul" 2>nul
del /f /q "pm-tools\v2\nul" 2>nul
del /f /q "poe2-tools\pob-plus\nul" 2>nul

echo 删除重组脚本...
del /f /q "reorganize_workspace.py" 2>nul

echo.
echo ================================================
echo 清理完成！
echo ================================================
echo.
echo 最终结构:
echo   pm-tools/v2/     - PM 工具 V2
echo   vitaflow/        - VitaFlow 产品
echo   poe2-tools/      - POE2 工具
echo   docs/yc/         - YC 文档
echo   templates/       - 代码模板
echo   scripts/         - 独立脚本
echo.
pause

