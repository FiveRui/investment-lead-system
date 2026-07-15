import os
import io
import json
from datetime import datetime
import sys
import subprocess
import threading

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil

# 导入爬虫引擎
from crawler_engine import CrawlerEngine

app = FastAPI(title="全自动招商情报系统")

# 配置静态文件和模板
RUNTIME_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.getcwd()
UPLOAD_DIR = os.path.join(WORK_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=os.path.join(RUNTIME_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(RUNTIME_DIR, "templates"))

# 全局爬虫引擎实例
crawler_engine = CrawlerEngine()

raw_news_lock = threading.Lock()
raw_news_proc = None
raw_news_logs = []
raw_news_state = {
    "is_running": False,
    "phase": "idle",
    "started_at": "",
    "exit_code": None,
    "script_path": "",
    "csv_path": "",
    "pid": None,
}

def _raw_news_log(line: str):
    s = str(line or "").rstrip("\r\n")
    if not s:
        return
    with raw_news_lock:
        raw_news_logs.append(s)
        if len(raw_news_logs) > 300:
            raw_news_logs.pop(0)
        if "按回车继续" in s or "确认已就绪" in s:
            raw_news_state["phase"] = "waiting_login"
        if "登录就绪" in s:
            raw_news_state["phase"] = "running"
        if "开始执行【全网招商舆情收集】" in s or "开始执行【全网招商舆情收集】广度挖掘任务" in s:
            raw_news_state["phase"] = "running"
        if "今日舆情新闻收集任务执行完毕" in s or "本次新增" in s:
            if raw_news_state.get("phase") not in ("waiting_login",):
                raw_news_state["phase"] = "running"

def _find_raw_news_script():
    candidates = [
        os.path.join(WORK_DIR, "crawl_raw_news.py"),
        os.path.join(os.path.dirname(APP_DIR), "crawl_raw_news.py"),
        os.path.join(APP_DIR, "crawl_raw_news.py"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return ""

def _raw_news_reader(proc: subprocess.Popen):
    try:
        for line in proc.stdout:
            _raw_news_log(line)
    except Exception:
        pass
    try:
        code = proc.wait(timeout=5)
    except Exception:
        code = None
    with raw_news_lock:
        raw_news_state["is_running"] = False
        raw_news_state["exit_code"] = code
        if code == 0:
            raw_news_state["phase"] = "done"
        elif raw_news_state.get("phase") != "idle":
            raw_news_state["phase"] = "error"

def _kill_process_tree(pid: int):
    try:
        subprocess.run(
            ["taskkill", "/PID", str(int(pid)), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    """主页面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/upload_excel")
async def upload_excel(file: UploadFile = File(...)):
    """上传产业链Excel并解析"""
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 解析Excel工作表名称作为产业链名称
    chains = crawler_engine.parse_excel_chains(file_path)
    
    return {"status": "success", "message": "上传并解析成功", "chains": chains, "file_name": file.filename}

@app.post("/api/config")
async def update_config(
    location_name: str = Form(...),
    location_id: str = Form(...),
    nodes: str = Form(...) # 逗号分隔的节点
):
    """更新落商地配置和节点配置"""
    crawler_engine.update_config({
        "location_name": location_name,
        "location_id": location_id,
        "nodes": [n.strip() for n in nodes.split(",") if n.strip()]
    })
    return {"status": "success", "message": "配置更新成功", "config": crawler_engine.config}

@app.post("/api/start_task")
async def start_task(background_tasks: BackgroundTasks):
    """启动全自动爬取和分析任务"""
    if crawler_engine.is_running:
        return {"status": "error", "message": "任务已经在运行中"}
    
    background_tasks.add_task(crawler_engine.run_task)
    return {"status": "success", "message": "任务已启动后台运行"}

@app.post("/api/stop_task")
async def stop_task():
    """停止任务"""
    if not crawler_engine.is_running:
        return {"status": "error", "message": "任务未在运行"}
    
    crawler_engine.stop_task()
    return {"status": "success", "message": "正在停止任务..."}

@app.get("/api/status")
async def get_status():
    """获取当前状态和日志"""
    return {
        "is_running": crawler_engine.is_running,
        "config": crawler_engine.config,
        "logs": crawler_engine.get_logs(),
        "stats": crawler_engine.stats
    }

@app.post("/api/raw_news/start")
async def start_raw_news():
    global raw_news_proc
    if getattr(sys, "frozen", False):
        return {"status": "error", "message": "当前为 PyInstaller 版，暂不支持在程序内部拉起 Selenium 采集。请使用源码版运行或单独运行 crawl_raw_news.py。"}
    with raw_news_lock:
        if raw_news_state.get("is_running"):
            return {"status": "error", "message": "原始新闻采集已在运行中"}
        raw_news_logs.clear()
        raw_news_state.update({"is_running": True, "phase": "starting", "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "exit_code": None})

    script_path = _find_raw_news_script()
    if not script_path:
        with raw_news_lock:
            raw_news_state.update({"is_running": False, "phase": "error"})
        return {"status": "error", "message": "未找到 crawl_raw_news.py，请把它放在项目根目录或当前运行目录下。"}

    csv_path = os.path.join(os.path.dirname(script_path), "raw_news_leads.csv")
    with raw_news_lock:
        raw_news_state["script_path"] = script_path
        raw_news_state["csv_path"] = csv_path

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["RAW_NEWS_RUN_ONCE"] = "1"
    env["RAW_NEWS_AUTO_CONTINUE"] = "1"

    try:
        raw_news_proc = subprocess.Popen(
            [sys.executable, "-u", script_path],
            cwd=os.path.dirname(script_path),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
    except Exception as e:
        with raw_news_lock:
            raw_news_state.update({"is_running": False, "phase": "error"})
        return {"status": "error", "message": f"启动失败：{e}"}

    with raw_news_lock:
        raw_news_state["pid"] = int(getattr(raw_news_proc, "pid", 0) or 0) or None

    t = threading.Thread(target=_raw_news_reader, args=(raw_news_proc,), daemon=True)
    t.start()
    with raw_news_lock:
        raw_news_state["phase"] = "waiting_login"
    _raw_news_log("已启动原始新闻采集进程。若弹出浏览器，请先完成 DeepSeek 登录，然后点击“登录完成继续”。")
    return {"status": "success", "message": "原始新闻采集已启动"}

@app.post("/api/raw_news/continue")
async def continue_raw_news():
    global raw_news_proc
    with raw_news_lock:
        if not raw_news_state.get("is_running") or raw_news_proc is None:
            return {"status": "error", "message": "原始新闻采集未在运行"}
        if raw_news_proc.poll() is not None:
            raw_news_state["is_running"] = False
            raw_news_state["phase"] = "error"
            return {"status": "error", "message": "采集进程已退出"}
        proc = raw_news_proc
    try:
        if proc.stdin:
            proc.stdin.write("\n")
            proc.stdin.flush()
        with raw_news_lock:
            raw_news_state["phase"] = "running"
        return {"status": "success", "message": "已发送继续信号"}
    except Exception as e:
        return {"status": "error", "message": f"发送失败：{e}"}

@app.post("/api/raw_news/stop")
async def stop_raw_news():
    global raw_news_proc
    with raw_news_lock:
        if not raw_news_state.get("is_running") or raw_news_proc is None:
            return {"status": "error", "message": "原始新闻采集未在运行"}
        proc = raw_news_proc
        raw_news_state["phase"] = "stopping"
        pid = int(getattr(proc, "pid", 0) or 0) or None
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            pass
        if proc.poll() is None:
            if pid:
                _kill_process_tree(pid)
            else:
                try:
                    proc.kill()
                except Exception:
                    pass
    finally:
        with raw_news_lock:
            raw_news_state["is_running"] = False
            raw_news_state["phase"] = "idle"
            raw_news_state["exit_code"] = proc.poll()
            raw_news_proc = None
            raw_news_state["pid"] = None
    return {"status": "success", "message": "已强制停止原始新闻采集（含子进程）"}

@app.get("/api/raw_news/status")
async def raw_news_status():
    global raw_news_proc
    with raw_news_lock:
        proc = raw_news_proc
        if raw_news_state.get("is_running") and proc is not None and proc.poll() is not None:
            raw_news_state["is_running"] = False
            raw_news_state["exit_code"] = proc.poll()
            raw_news_state["phase"] = "done" if raw_news_state["exit_code"] == 0 else "error"
            raw_news_state["pid"] = None
            raw_news_proc = None
        state = dict(raw_news_state)
        logs = list(raw_news_logs)
    return {"status": "success", "state": state, "logs": logs}

@app.get("/api/leads")
async def get_leads():
    """获取挖掘到的招商线索"""
    return {"status": "success", "data": crawler_engine.get_leads()}

@app.get("/api/export_leads")
async def export_leads(format: str = "xlsx"):
    rows = crawler_engine.get_leads() or []
    if not rows:
        rows = []
    df = pd.DataFrame(rows)
    columns_order = [
        "chain_name",
        "node_name",
        "chain_ids",
        "node_ids",
        "chain_node",
        "region_name",
        "clue_name",
        "investment_amount",
        "land_requirement",
        "investment_layout",
        "content",
        "company_name",
        "product_details",
        "company_intro",
        "company_customers",
        "company_revenue",
        "shareholder_background",
        "investment_plan_docs",
        "public_sentiment_link",
        "publish_date",
        "registration_place",
        "recommend_reason",
    ]
    for col in columns_order:
        if col not in df.columns:
            df[col] = ""
    df = df[columns_order]
    if "investment_plan_docs" in df.columns:
        df["investment_plan_docs"] = df["investment_plan_docs"].apply(
            lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else (str(v).strip() if v is not None else "[]")
        )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if str(format).lower() == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        data = buf.getvalue().encode("utf-8-sig")
        headers = {"Content-Disposition": f'attachment; filename="leads_{ts}.csv"'}
        return StreamingResponse(io.BytesIO(data), media_type="text/csv", headers=headers)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="招商线索", index=False)
    out.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="leads_{ts}.xlsx"'}
    return StreamingResponse(out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


def _run_uvicorn():
    import uvicorn

    port = int(os.getenv("INVESTMENT_LEAD_PORT", "8888"))
    host = os.getenv("INVESTMENT_LEAD_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    _run_uvicorn()
