@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

if not exist ".venv\\Scripts\\python.exe" (
  echo 未检测到 .venv，请先运行 setup_windows.bat。
  pause
  exit /b 1
)

if not exist "run_config.json" (
  echo 未检测到 run_config.json，请先运行 setup_windows.bat 并填写 deepseek_api_key。
  pause
  exit /b 1
)

call ".venv\\Scripts\\activate.bat"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo 启动服务: http://127.0.0.1:8888
echo 关闭窗口或按 Ctrl+C 停止
python -m uvicorn main:app --host 127.0.0.1 --port 8888
