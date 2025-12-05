import sys
import os
import threading
import shutil
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from main import run_task
from log_manager import LogManager

app = FastAPI()

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

class TaskRequest(BaseModel):
    task: str

runs = {}

def execute_task(run_id: str, task: str, log_manager: LogManager):
    try:
        runs[run_id]["status"] = "running"
        success = run_task(task, str(log_manager.code_dir), log_manager)
        if success:
            runs[run_id]["status"] = "completed"
        else:
            runs[run_id]["status"] = "failed"
    except Exception as e:
        log_manager.exception(f"Exception in task execution: {e}")
        runs[run_id]["status"] = "failed"

@app.post("/api/start")
async def start_task(request: TaskRequest, background_tasks: BackgroundTasks):
    runs_dir = project_root / "runs"
    lm = LogManager(base_dir=str(runs_dir), retention_days=7)
    run_id = lm.run_dir.name
    
    runs[run_id] = {
        "status": "pending",
        "log_manager": lm
    }
    
    background_tasks.add_task(execute_task, run_id, request.task, lm)
    
    return {"run_id": run_id}

@app.get("/api/status/{run_id}")
async def get_status(run_id: str):
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_info = runs[run_id]
    lm = run_info["log_manager"]
    
    logs = ""
    if lm.program_log_path.exists():
        with open(lm.program_log_path, "r", encoding="utf-8") as f:
            logs = f.read()
            
    return {
        "run_id": run_id,
        "status": run_info["status"],
        "logs": logs
    }

@app.get("/api/download_app/{run_id}")
async def download_app(run_id: str):
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
        
    run_info = runs[run_id]
    lm = run_info["log_manager"]
    
    app_path = lm.code_dir / "dist" / "app"
    
    if not app_path.exists():
        dist_dir = lm.code_dir / "dist"
        if dist_dir.exists():
            exes = [f for f in dist_dir.iterdir() if f.is_file() and os.access(f, os.X_OK)]
            if exes:
                app_path = exes[0]
            else:
                 raise HTTPException(status_code=404, detail="Executable not found in dist")
        else:
             raise HTTPException(status_code=404, detail="Dist directory not found")

    return FileResponse(str(app_path), media_type='application/octet-stream', filename="application")

@app.get("/api/download_code/{run_id}")
async def download_code(run_id: str):
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
        
    run_info = runs[run_id]
    lm = run_info["log_manager"]
    
    zip_path = lm.run_dir / "project_code"
    shutil.make_archive(str(zip_path), 'zip', lm.code_dir)
    
    return FileResponse(f"{zip_path}.zip", media_type='application/zip', filename=f"{run_id}_code.zip")

@app.get("/")
async def read_index():
    return FileResponse(Path(__file__).parent / 'static/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
