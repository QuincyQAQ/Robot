"""
Flask Backend for Robot Control System
Provides REST API and WebSocket for real-time robot control.
Migrated from FastAPI to Flask + flask-sock.
"""

import os
os.environ["MUJOCO_GL"] = "egl"
os.environ["PYOPENGL_PLATFORM"] = "egl"

import atexit
import json
import signal
import threading
import time

from flask import Flask, request, jsonify, send_from_directory
from flask_sock import Sock
from flask_cors import CORS

from simulation import MujocoSimulator

app = Flask(__name__)
sock = Sock(app)
CORS(app)

sim = MujocoSimulator()

# --- Thread-safe physics loop ---
_physics_thread = None
_physics_lock = threading.Lock()
_physics_running = False


def _physics_loop():
    """Run physics with PD control. 4 steps per 8ms = 1x realtime."""
    global _physics_running
    while _physics_running:
        with _physics_lock:
            for _ in range(4):
                sim.step()
        time.sleep(0.008)


def _ensure_physics_started():
    """Lazy-start the physics thread on first request."""
    global _physics_thread, _physics_running
    if _physics_thread is None:
        _physics_running = True
        _physics_thread = threading.Thread(target=_physics_loop, daemon=True)
        _physics_thread.start()
        print("🚀 Simulation started")


def _shutdown_physics():
    global _physics_running, _physics_thread
    if _physics_running:
        _physics_running = False
        if _physics_thread:
            _physics_thread.join(timeout=2)
        print("🛑 Simulation stopped")


atexit.register(_shutdown_physics)
signal.signal(signal.SIGTERM, lambda s, f: _shutdown_physics())
signal.signal(signal.SIGINT, lambda s, f: _shutdown_physics())

# Use before_request to lazy-start physics on first incoming request
@app.before_request
def _startup():
    _ensure_physics_started()


# --- REST API Endpoints ---

VALID_GAITS = ("stand", "sit", "trot", "pace", "bound", "jump", "crawl", "dance")


@app.route("/api/robot/info")
def get_robot_info():
    with _physics_lock:
        info = sim.get_robot_info()
    return jsonify(info)


@app.route("/api/robot/state")
def get_robot_state():
    with _physics_lock:
        state = sim.get_state()
    return jsonify(state)


@app.route("/api/robot/control", methods=["POST"])
def control_robot():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    positions = data.get("positions")
    controls = data.get("controls")

    if positions is not None:
        if not isinstance(positions, list) or not all(isinstance(v, (int, float)) for v in positions):
            return jsonify({"status": "error", "message": "positions must be list[float]"}), 400
        sim.set_joint_positions(positions)
    if controls is not None:
        if not isinstance(controls, list) or not all(isinstance(v, (int, float)) for v in controls):
            return jsonify({"status": "error", "message": "controls must be list[float]"}), 400
        sim.set_controls(controls)

    return jsonify({"status": "ok"})


@app.route("/api/robot/reset", methods=["POST"])
def reset_robot():
    with _physics_lock:
        sim.reset()
    return jsonify({"status": "ok"})


# IMPORTANT: static route MUST come before parameterized route
# to prevent "stop" being captured as <gait_type>
@app.route("/api/robot/gait/stop", methods=["POST"])
def stop_gait():
    sim.stop_gait()
    return jsonify({"status": "ok"})


@app.route("/api/robot/gait/<gait_type>", methods=["POST"])
def start_gait(gait_type):
    if gait_type not in VALID_GAITS:
        return jsonify({"status": "error", "message": f"Unknown gait: {gait_type}"}), 400
    sim.start_gait(gait_type)
    return jsonify({"status": "ok", "gait": gait_type})


# --- WebSocket Endpoints ---

@sock.route("/ws/robot/state")
def ws_robot_state(ws):
    while True:
        try:
            with _physics_lock:
                state = sim.get_state()
            ws.send(json.dumps(state))
            time.sleep(0.016)
        except Exception:
            break


@sock.route("/ws/robot/render")
def ws_robot_render(ws):
    while True:
        try:
            with _physics_lock:
                jpeg_data = sim.render_jpeg(320, 480, 30)
            ws.send(json.dumps({"image": jpeg_data}))
            time.sleep(0.016)
        except Exception:
            break


@sock.route("/ws/robot/control")
def ws_robot_control(ws):
    while True:
        try:
            data = ws.receive()
            if data is None:
                break
            msg = json.loads(data)
            if "positions" in msg:
                sim.set_joint_positions(msg["positions"])
            if "controls" in msg:
                sim.set_controls(msg["controls"])
        except Exception:
            break


# --- Serve Frontend Static Files ---
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIST, "index.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(os.path.join(FRONTEND_DIST, "assets"), filename)


if __name__ == "__main__":
    # threaded=True is essential for WebSocket support in development
    app.run(host="0.0.0.0", port=8009, debug=False, threaded=True)
