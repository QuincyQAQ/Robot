# Robot Control System with MuJoCo Simulation

A complete web-based robot control system with MuJoCo physics simulation, real-time visualization, and interactive control.

## Architecture

```
┌─────────────┐     WebSocket/HTTP     ┌──────────────┐
│   Vue/React │ ◄────────────────────► │   FastAPI    │
│  (Frontend) │                        │   (Backend)   │
└─────────────┘                        └──────┬───────┘
                                              │
                                       ┌──────▼───────┐
                                       │   MuJoCo     │
                                       │ (Simulation)  │
                                       └──────────────┘
```

## Features

- 🤖 **MuJoCo Physics Simulation** - Realistic robot dynamics
- 🎮 **Web-based Control** - Interactive UI for robot control
- 📊 **Real-time Visualization** - 3D visualization in browser
- 🔌 **WebSocket Communication** - Low-latency real-time data
- 🐕 **Quadruped Support** - Unitree Go1 model
- 🦾 **Robot Arm Support** - UR5e model

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open browser to `http://localhost:5173`

## Project Structure

```
robot-control-system/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── simulation.py        # MuJoCo simulation engine
│   ├── models/              # Robot models (XML)
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.vue          # Main application
│   │   ├── components/      # Vue components
│   │   └── api/             # API clients
│   ├── package.json
│   └── vite.config.js
└── README.md
```


fuser -k 8007/tcp 2>/dev/null; cd /home/cxhlab/lqj_code/robotics/robot-control-system/backend && MUJOCO_GL=egl PYOPENGL_PLATFORM=egl EGL_DEVICE_ID=0 python3 main.py
cd /home/cxhlab/lqj_code/robotics/robot-control-system/frontend && npm run dev -- --host 0.0.0.0 --port 5174


fuser -k 8009/tcp 2>/dev/null; cd /home/cxhlab/lqj_code/robotics/robot-control-system/backend && MUJOCO_GL=egl PYOPENGL_PLATFORM=egl EGL_DEVICE_ID=0 python3 main.py