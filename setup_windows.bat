@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo [1/4] 检查 Python...
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo 未检测到 python/py，请先安装 Python 3.10+ 并勾选 Add to PATH。
    pause
    exit /b 1
  )
)

echo [2/4] 创建虚拟环境 .venv（如已存在将跳过）...
if not exist ".venv\\Scripts\\python.exe" (
  where py >nul 2>nul
  if errorlevel 0 (
    py -3.10 -m venv .venv
  ) else (
    python -m venv .venv
  )
)

echo [3/4] 安装依赖...
call ".venv\\Scripts\\activate.bat"
python -m pip install -U pip
pip install -r requirements.txt

echo [4/4] 生成本地配置 run_config.json（如不存在）...
if not exist "run_config.json" (
  copy /y "run_config.example.json" "run_config.json" >nul
  echo 已生成 run_config.json，请编辑填写 deepseek_api_key 后再启动。
) else (
  echo 已存在 run_config.json，跳过生成。
)

echo 完成。
pause
