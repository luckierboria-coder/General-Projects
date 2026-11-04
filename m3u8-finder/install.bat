@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/3] 安装 Python 依赖...
python -m pip install -U playwright imageio-ffmpeg
if errorlevel 1 goto :error
echo [2/3] 安装 Chromium 浏览器...
python -m playwright install chromium
if errorlevel 1 goto :error
echo [3/3] 完成，请双击 run.bat 启动。
pause
exit /b 0
:error
echo 安装失败，请检查网络、代理和 Python 版本。
pause
exit /b 1
