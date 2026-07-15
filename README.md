# Investment Lead System

这是一个基于 FastAPI 的招商线索 Web 系统，用于在网页中完成原始新闻采集控制、智能穿透分析和结果导出。

## 功能概览

- 上传产业链 Excel，按节点执行招商线索挖掘
- 调用 DeepSeek API 对原始新闻进行穿透分析
- 在页面中启动、继续、停止原始新闻采集任务
- 导出招商线索结果为 CSV / Excel
- 支持 Windows 下源码运行和 PyInstaller 打包分发

## 目录结构

```text
investment_lead_system/
├─ main.py                      # FastAPI 入口
├─ crawler_engine.py            # 原始新闻 -> 线索分析引擎
├─ requirements.txt             # 依赖列表
├─ run_config.example.json      # 配置模板
├─ setup_windows.bat            # 初始化环境
├─ start_windows.bat            # 启动服务
├─ pyinstaller_build_onedir.bat # 目录版打包
├─ pyinstaller_build_onefile.bat# 单文件版打包
├─ templates/
├─ static/
└─ 操作文档.md
```

## 环境要求

- Windows 10 / 11
- Python 3.10+
- 可访问 DeepSeek API 的网络环境

## 快速开始

### 1. 安装依赖

```powershell
.\setup_windows.bat
```

### 2. 配置 API

将 `run_config.example.json` 复制为 `run_config.json`，然后填写你自己的：

- `deepseek_api_key`
- `deepseek_api_base_url`
- `deepseek_model`

注意：`run_config.json` 不要提交到 GitHub。

### 3. 启动系统

```powershell
.\start_windows.bat
```

启动后访问：

```text
http://127.0.0.1:8888
```

## 打包

目录中已提供两个打包脚本：

- `pyinstaller_build_onedir.bat`
- `pyinstaller_build_onefile.bat`

分别用于生成目录版和单文件版 Windows 可执行程序。

## 建议提交到 GitHub 的内容

- `main.py`
- `crawler_engine.py`
- `templates/`
- `static/`
- `requirements.txt`
- `run_config.example.json`
- `setup_windows.bat`
- `start_windows.bat`
- `pyinstaller_build_onedir.bat`
- `pyinstaller_build_onefile.bat`
- `README.md`
- `操作文档.md`

## 不建议提交的内容

- `run_config.json`
- `.venv/`
- `.venv_build/`
- `uploads/`
- `build/`
- `dist/`
- `.idea/`
- `__pycache__/`

更详细的使用说明请查看 `操作文档.md`。

