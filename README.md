# Investment Lead System

`investment_lead_system` 是一个基于 FastAPI + Jinja2 的招商线索 Web 系统，面向“产业链节点 -> 原始新闻 -> AI 穿透分析 -> 结果导出”的业务流程，提供可视化操作界面、任务状态查看、原始新闻采集控制与 CSV/Excel 导出能力。

该仓库主要聚焦 Web 端交付，适合本地源码运行、交接给同事使用，或进一步打包为 Windows 可执行程序。

## 项目亮点

- 以网页形式完成产业链 Excel 上传、参数配置、任务启动与结果查看
- 默认按“原始新闻 CSV -> AI 穿透分析”的两阶段流程产出招商线索
- 支持在页面中启动、继续、停止原始新闻采集任务
- 支持导出标准化招商线索结果为 `CSV` / `Excel`
- 兼容 Windows 源码运行与 PyInstaller 打包分发
- 输出字段与既有招商线索结构保持一致，便于后续入库或人工研判

## 系统流程

```text
产业链 Excel
    ↓
解析工作表和节点
    ↓
原始新闻采集（可选，通过外部 crawl_raw_news.py）
    ↓
读取 raw_news_leads.csv
    ↓
DeepSeek API 穿透分析
    ↓
线索结果展示 / 导出 CSV / 导出 Excel
```

## 主要功能

### 1. 产业链配置

- 上传产业链 Excel 文件
- 自动识别工作表名称作为产业链名称
- 基于配置的落商地名称、落商地 ID、节点集合执行分析任务

### 2. 原始新闻采集联动

- 页面内可启动原始新闻采集任务
- 支持登录完成继续、停止采集、查看采集日志
- 自动轮询采集状态并显示阶段变化

说明：

- 当前 Web 项目中的“原始新闻采集”按钮依赖外部脚本 `crawl_raw_news.py`
- `main.py` 会优先在当前工作目录、上级目录或应用目录中查找该脚本
- 如果你将本仓库单独发布为独立仓库，需要把 `crawl_raw_news.py` 放到可被程序发现的位置，或者在 README / 交付说明中明确此依赖

### 3. AI 穿透分析

- 默认新闻源为 `raw_news_csv`
- 读取 `raw_news_leads.csv` 或 `raw_news.csv`
- 对新闻标题、摘要、关键事件、涉及企业等字段进行结构化穿透
- 输出企业全称、投资信息、产品情况、推荐理由、链条节点等字段

### 4. 结果导出

- 支持通过接口导出 `CSV`
- 支持通过接口导出 `Excel`
- 导出字段顺序已经标准化，便于后续对接数据库或人工筛选

## 技术栈

- 后端：FastAPI
- 模板：Jinja2
- 前端：原生页面 + 静态 JS / CSS
- 数据处理：Pandas、OpenPyXL
- 采集联动：Selenium
- 数据库：PyMySQL
- 打包：PyInstaller

## 目录结构

```text
investment_lead_system/
├─ main.py                       # FastAPI 入口，接口、页面、任务控制
├─ crawler_engine.py             # 原始新闻读取、AI 分析、结果导出
├─ requirements.txt              # Python 依赖
├─ run_config.example.json       # 配置模板
├─ setup_windows.bat             # 首次安装脚本
├─ start_windows.bat             # 启动脚本
├─ pyinstaller_build_onedir.bat  # 目录版打包
├─ pyinstaller_build_onefile.bat # 单文件版打包
├─ templates/
│  └─ index.html                 # 主页面模板
├─ static/
│  ├─ css/
│  └─ js/
├─ README.md
└─ 操作文档.md
```

## 环境要求

- Windows 10 / 11
- Python 3.10+
- 可访问 DeepSeek API 的网络环境
- 如需网页内原始新闻采集，需要可用浏览器环境和外部 `crawl_raw_news.py`

## 配置说明

项目默认通过 `run_config.json` 或环境变量读取 DeepSeek 配置。推荐使用模板文件复制生成本地配置：

```powershell
Copy-Item .\run_config.example.json .\run_config.json
```

`run_config.json` 示例字段：

- `deepseek_api_key`
- `deepseek_api_base_url`
- `deepseek_model`
- `deepseek_timeout_seconds`

注意：

- `run_config.json` 属于本地私有配置，不要提交到 GitHub
- 若设置了环境变量，则环境变量优先级高于本地 JSON 配置

## 快速开始

### 1. 安装依赖

在项目目录执行：

```powershell
.\setup_windows.bat
```

该脚本会自动：

- 创建 `.venv`
- 安装 `requirements.txt`
- 在不存在时生成 `run_config.json`

### 2. 填写配置

打开 `run_config.json`，填写你自己的 DeepSeek 配置：

- `deepseek_api_key`
- `deepseek_api_base_url`
- `deepseek_model`

### 3. 启动系统

```powershell
.\start_windows.bat
```

默认访问地址：

```text
http://127.0.0.1:8888
```

### 4. 页面使用流程

1. 上传产业链 Excel
2. 配置落商地名称、ID 和节点
3. 如需采集原始新闻，点击“爬取原始新闻”
4. 登录完成后继续采集，等待生成原始新闻结果
5. 点击“启动智能挖掘”
6. 查看状态、日志和线索结果
7. 导出 CSV 或 Excel

## 接口一览

核心接口包括：

- `POST /api/upload_excel`：上传并解析产业链 Excel
- `POST /api/config`：更新落商地与节点配置
- `POST /api/start_task`：启动智能挖掘任务
- `POST /api/stop_task`：停止智能挖掘任务
- `GET /api/status`：查询任务状态和日志
- `POST /api/raw_news/start`：启动原始新闻采集
- `POST /api/raw_news/continue`：登录完成后继续采集
- `POST /api/raw_news/stop`：停止原始新闻采集
- `GET /api/raw_news/status`：查询原始新闻采集状态
- `GET /api/leads`：获取线索结果
- `GET /api/export_leads?format=csv`：导出 CSV
- `GET /api/export_leads?format=xlsx`：导出 Excel

## 导出字段

当前导出的线索字段主要包括：

- `chain_name`
- `node_name`
- `chain_ids`
- `node_ids`
- `chain_node`
- `region_name`
- `clue_name`
- `investment_amount`
- `land_requirement`
- `investment_layout`
- `content`
- `company_name`
- `product_details`
- `company_intro`
- `company_customers`
- `company_revenue`
- `shareholder_background`
- `investment_plan_docs`
- `public_sentiment_link`
- `publish_date`
- `registration_place`
- `recommend_reason`

## 打包与分发

项目内已提供两种 PyInstaller 打包脚本：

- `pyinstaller_build_onedir.bat`
- `pyinstaller_build_onefile.bat`

适用场景：

- `onedir`：适合同事本地使用，启动更稳定
- `onefile`：适合单文件分发，首次启动相对较慢

注意：

- 若打包后仍要使用网页内“原始新闻采集”按钮，需要额外考虑 Selenium 和外部脚本依赖
- 当前程序在 PyInstaller 模式下对内部拉起 Selenium 采集有限制，建议源码模式下执行采集流程

## 适合提交到 GitHub 的内容

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
- 任意本地导出的 `csv/xlsx/zip`

## 已知限制

- 原始新闻采集功能依赖外部 `crawl_raw_news.py`
- PyInstaller 版本不适合作为完整 Selenium 采集入口
- 运行环境默认偏向 Windows
- 若 API Key、网络环境或新闻源不可用，智能挖掘结果会受影响

## 相关文档

- 详细操作说明：`操作文档.md`
- 配置模板：`run_config.example.json`
- 启动脚本：`start_windows.bat`
- 安装脚本：`setup_windows.bat`
