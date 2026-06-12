"""
FastAPI Backend for Robot Control System
Provides REST API and WebSocket for real-time robot control.
"""

import os
os.environ["MUJOCO_GL"] = "egl"
os.environ["PYOPENGL_PLATFORM"] = "egl"

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import base64
import io

from simulation import MujocoSimulator

app = FastAPI(title="Robot Control System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sim = MujocoSimulator()

# Background physics task
_physics_task = None


async def _physics_loop():
    """Run physics with PD control. 4 steps per 8ms = 1x realtime."""
    while True:
        for _ in range(4):
            sim.step()
        await asyncio.sleep(0.008)


@app.on_event("startup")
async def startup_event():
    global _physics_task
    _physics_task = asyncio.create_task(_physics_loop())
    print("🚀 Simulation started")


@app.on_event("shutdown")
async def shutdown_event():
    global _physics_task
    if _physics_task:
        _physics_task.cancel()
    print("🛑 Simulation stopped")


class JointControl(BaseModel):
    positions: Optional[List[float]] = None
    controls: Optional[List[float]] = None


class RobotInfo(BaseModel):
    nq: int
    nv: int
    nu: int
    nbody: int
    names: List[str]


@app.get("/api/robot/info", response_model=RobotInfo)
async def get_robot_info():
    return sim.get_robot_info()


@app.get("/api/robot/state")
async def get_robot_state():
    return sim.get_state()


@app.post("/api/robot/control")
async def control_robot(control: JointControl):
    if control.positions is not None:
        sim.set_joint_positions(control.positions)
    if control.controls is not None:
        sim.set_controls(control.controls)
    return {"status": "ok"}


@app.post("/api/robot/reset")
async def reset_robot():
    sim.reset()
    return {"status": "ok"}


@app.post("/api/robot/gait/{gait_type}")
async def start_gait(gait_type: str):
    if gait_type not in ("stand", "sit", "trot", "pace", "bound", "jump", "crawl", "dance"):
        return {"status": "error", "message": f"Unknown gait: {gait_type}"}
    sim.start_gait(gait_type)
    return {"status": "ok", "gait": gait_type}


@app.post("/api/robot/gait/stop")
async def stop_gait():
    sim.stop_gait()
    return {"status": "ok"}


@app.websocket("/ws/robot/state")
async def websocket_robot_state(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            state = sim.get_state()
            await websocket.send_json(state)
            await asyncio.sleep(0.016)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/robot/render")
async def websocket_robot_render(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            jpeg_data = sim.render_jpeg(320, 480, 30)
            try:
                await websocket.send_json({"image": jpeg_data})
                await asyncio.sleep(0)  # yield to other tasks
            except Exception:
                break
            await asyncio.sleep(0.016)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.websocket("/ws/robot/control")
async def websocket_robot_control(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if "positions" in data:
                sim.set_joint_positions(data["positions"])
            if "controls" in data:
                sim.set_controls(data["controls"])
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
