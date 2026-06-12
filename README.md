# Robot Control System with MuJoCo Simulation

A web-based robot control system with MuJoCo physics simulation, real-time GPU rendering, and interactive joint control.

## Architecture

```
┌─────────────┐     WebSocket/HTTP     ┌──────────────┐
│   Vue/Vite   │ ◄────────────────────► │   FastAPI    │
│  (Frontend)  │                        │   (Backend)   │
└─────────────┘                        └──────┬───────┘
                                              │
                                       ┌──────▼───────┐
                                       │   MuJoCo     │
                                       │ (Simulation)  │
                                       └──────────────┘
```

## Features

- 🤖 **MuJoCo Physics Simulation** - Realistic robot dynamics with GPU offscreen rendering
- 🐕 **Unitree Go2** - 12-DOF quadruped with PD torque control
- 🎮 **8 Gait Patterns** - Stand, Sit, Trot, Pace, Bound, Crawl, Jump, Dance
- 🎚️ **Joint Sliders** - Real-time individual joint control
- 📷 **Camera Control** - Rotate, zoom, reset view
- ⚡ **60fps Rendering** - GPU-accelerated offscreen rendering streamed via WebSocket

## v1.2 Changes

- Switched from Unitree Go1 to **Unitree Go2** model
- Tuned joint parameters to match Go2 official keyframe (hip=0, thigh=0.9, calf=-1.8)
- Implemented **PD torque control** for Go2 motors (kp=100, kd=2)
- Models moved to `/home/cxhlab/lqj_code/data/` for lightweight code backups

## Quick Start

### Backend (GPU required)

```bash
fuser -k 8009/tcp 2>/dev/null
cd /home/cxhlab/lqj_code/robotics/robot-control-system/backend
MUJOCO_GL=egl PYOPENGL_PLATFORM=egl EGL_DEVICE_ID=0 python3 main.py
```

### Frontend

```bash
cd /home/cxhlab/lqj_code/robotics/robot-control-system/frontend
npm run dev -- --host 0.0.0.0 --port 5174
```

Open browser to **http://localhost:5174**

## Project Structure

```
robot-control-system/
├── backend/
│   ├── main.py              # FastAPI + WebSocket server
│   ├── simulation.py        # MuJoCo Go2 simulation with PD control
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   └── App.vue          # Vue SPA with control panel
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/robot/info` | Robot model info |
| GET | `/api/robot/state` | Current simulation state |
| POST | `/api/robot/reset` | Reset to initial pose |
| POST | `/api/robot/control` | Send joint positions/controls |
| POST | `/api/robot/gait/{type}` | Start gait (stand/sit/trot/pace/bound/crawl/jump/dance) |
| POST | `/api/robot/gait/stop` | Stop gait |
| WS | `/ws/robot/state` | Real-time state stream |
| WS | `/ws/robot/render` | Real-time GPU render stream |
| WS | `/ws/robot/control` | Real-time joint control |
