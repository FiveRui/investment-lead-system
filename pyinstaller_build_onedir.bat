@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo [1/4] 创建打包专用虚拟环境 .venv_build（如已存在将跳过）...
if not exist ".venv_build\\Scripts\\python.exe" (
  python -m venv .venv_build
)

echo [2/4] 安装依赖（最小化环境，避免打进无关大库）...
call ".venv_build\\Scripts\\activate.bat"
python -m pip install -U pip
pip install -r requirements.txt
pip install -U pyinstaller

echo [3/4] 开始打包（目录版 onedir）...
pyinstaller --noconfirm --clean ^
  --name investment_lead_system_web ^
  --distpath "..\\release\\pyinstaller\\dist" ^
  --workpath "..\\release\\pyinstaller\\build" ^
  --specpath "..\\release\\pyinstaller" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "run_config.example.json;." ^
  --add-data "操作文档.md;." ^
  main.py

echo [4/4] 打包完成。dist 目录：..\\release\\pyinstaller\\dist\\investment_lead_system_web
pause
