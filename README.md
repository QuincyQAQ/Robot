# Robot Control System (Flask + UniApp)

Web-based robot control system with MuJoCo physics simulation, real-time GPU rendering, and interactive joint control.
Migrated from FastAPI + Vue/Vite to **Flask + UniApp** for cross-platform support (H5, iOS, Android, mini-programs).

## Architecture

```
┌──────────────────┐     WebSocket/HTTP     ┌──────────────┐
│   UniApp (H5)    │ ◄────────────────────► │    Flask     │
│   (Frontend)     │                        │   (Backend)   │
└──────────────────┘                        └──────┬───────┘
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
- 📱 **Cross-Platform** - UniApp supports H5, iOS, Android, and mini-programs

## v1.3 Changes

- Migrated from FastAPI + Vue/Vite → **Flask + UniApp**
- Frontend built as static H5 files, served directly by Flask (single port 8009)
- Replaced asyncio physics loop with `threading.Thread` + `threading.Lock`
- WebSocket: `flask-sock` (raw WebSocket) compatible with UniApp `uni.connectSocket()`
- No more separate frontend dev server needed for deployment

### Quick Start (v1.3 — single port)

```bash
# 后端（自带前端页面 + API + WebSocket）
cd /home/cxhlab/lqj_code/robotics/robot-control-system-flask/backend
fuser -k 8009/tcp 2>/dev/null
MUJOCO_GL=egl PYOPENGL_PLATFORM=egl EGL_DEVICE_ID=0 python3 app.py &

# 前端（仅开发时构建，不需要常驻运行）
cd /home/cxhlab/lqj_code/robotics/robot-control-system-flask/frontend
npm run build:h5
```

Open browser to **http://localhost:8009** — everything on one port.

## Tech Stack Change

| Layer | Old | New |
|-------|-----|-----|
| Backend | FastAPI + asyncio | Flask + flask-sock + threading |
| Frontend | Vue 3 + Vite | UniApp (Vue 3) |
| WebSocket | Raw asyncio WebSocket | flask-sock (raw WebSocket) |
| HTTP Client | fetch() | uni.request() |
| CSS Units | px, rem | px + rpx + responsive |

## Quick Start

### Backend (GPU required)

```bash
cd backend
pip install -r requirements.txt
MUJOCO_GL=egl PYOPENGL_PLATFORM=egl EGL_DEVICE_ID=0 python3 app.py
```

Server starts on **http://localhost:8009**

### Frontend

```bash
cd frontend
npm install
npm run dev:h5
```

Open browser to the URL shown in terminal (default: **http://localhost:5174**)

### Production

```bash
# Backend with gunicorn
cd backend
gunicorn -k gevent -w 1 --bind 0.0.0.0:8009 app:app

# Frontend H5 build
cd frontend
npm run build:h5
# Serve dist/build/h5/ with nginx or similar
```

## Project Structure

```
robot-control-system-flask/
├── backend/
│   ├── app.py              # Flask server (REST + WebSocket)
│   ├── simulation.py       # MuJoCo Go2 simulation with PD control
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── manifest.json       # UniApp app config
│   ├── pages.json          # Page routing
│   ├── App.vue             # Root component
│   ├── main.js             # Entry point
│   ├── uni.scss            # SCSS variables
│   ├── package.json        # Node dependencies
│   └── pages/
│       └── index/
│           └── index.vue   # Main control page
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

## Key Differences from FastAPI Version

### Backend
- **Thread safety**: `threading.Lock` serializes all MuJoCo data access across Flask request threads and the physics thread
- **Physics loop**: Thread-based (`threading.Thread`) instead of asyncio
- **Route ordering**: `/api/robot/gait/stop` must be defined before `/api/robot/gait/<gait_type>` in Flask
- **Lifecycle**: Lazy-start in `before_request` + `atexit`/signal cleanup instead of `on_event`

### Frontend
- **WebSocket API**: `uni.connectSocket()` with `SocketTask` instead of raw `new WebSocket()`
- **HTTP API**: `uni.request()` with Promise wrapper instead of `fetch()`
- **DOM elements**: `<view>`, `<image>`, `<text>` UniApp components
- **Lifecycle**: `onLoad()` / `onUnload()` instead of `mounted()` / `beforeUnmount()`
- **Responsive**: Media query breakpoint at 768px for mobile layout
