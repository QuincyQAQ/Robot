"""
MuJoCo Simulation Engine
Handles robot physics simulation and state management.
"""

import mujoco
import numpy as np
from typing import Dict, List


class MujocoSimulator:
    def __init__(self, xml_path: str = "/home/cxhlab/lqj_code/data/mujoco_menagerie/unitree_go1/scene.xml"):
        self.model = mujoco.MjModel.from_xml_path(xml_path)
        self.data = mujoco.MjData(self.model)
        
        # Reset to home keyframe
        if self.model.nkey > 0:
            mujoco.mj_resetDataKeyframe(self.model, self.data, 0)
            mujoco.mj_forward(self.model, self.data)
        
        self.initial_qpos = self.data.qpos.copy()
        self.initial_qvel = self.data.qvel.copy()
        self.initial_ctrl = self.data.ctrl.copy()
        
        # Renderer (lazy init)
        self._renderer = None
        
        # Gait controller
        self._gait_type = None
        self._gait_start_time = 0
        self._use_gait = False
            
    def step(self):
        """Single physics step. Call from asyncio loop."""
        if self._use_gait:
            self._apply_gait()
        # 8 substeps for realtime at ~60fps with timestep=0.002
        mujoco.mj_step(self.model, self.data, 8)
    
    def _apply_gait(self):
        t = self.data.time - self._gait_start_time
        phi = t * 2 * np.pi
        base = np.array([0, 0.9, -1.8] * 4)
        offsets = np.zeros(12)
        
        if self._gait_type == "stand":
            self.data.ctrl[:] = base
            
        elif self._gait_type == "sit":
            self.data.ctrl[:] = np.array([0, 1.5, -2.5] * 4)
            
        elif self._gait_type == "trot":
            freq, ts, cs = 2.0, 0.3, 0.4
            p = t * freq * 2 * np.pi
            offsets[1] = ts * np.sin(p);      offsets[2] = cs * np.sin(p)
            offsets[4] = ts * np.sin(p + np.pi); offsets[5] = cs * np.sin(p + np.pi)
            offsets[7] = ts * np.sin(p + np.pi); offsets[8] = cs * np.sin(p + np.pi)
            offsets[10] = ts * np.sin(p);       offsets[11] = cs * np.sin(p)
            self.data.ctrl[:] = base + offsets
            
        elif self._gait_type == "pace":
            freq, ts, cs = 1.5, 0.25, 0.35
            p = t * freq * 2 * np.pi
            # Left pair (FL + RL) phase 0, Right pair (FR + RR) phase pi
            offsets[1] = ts * np.sin(p);       offsets[2] = cs * np.sin(p)
            offsets[4] = ts * np.sin(p + np.pi); offsets[5] = cs * np.sin(p + np.pi)
            offsets[7] = ts * np.sin(p);        offsets[8] = cs * np.sin(p)
            offsets[10] = ts * np.sin(p + np.pi); offsets[11] = cs * np.sin(p + np.pi)
            self.data.ctrl[:] = base + offsets
            
        elif self._gait_type == "bound":
            freq, ts, cs = 2.5, 0.35, 0.5
            p = t * freq * 2 * np.pi
            # Front pair (FL + FR) phase 0, Hind pair (RL + RR) phase pi
            offsets[1] = ts * np.sin(p);       offsets[2] = cs * np.sin(p)
            offsets[4] = ts * np.sin(p);        offsets[5] = cs * np.sin(p)
            offsets[7] = ts * np.sin(p + np.pi); offsets[8] = cs * np.sin(p + np.pi)
            offsets[10] = ts * np.sin(p + np.pi); offsets[11] = cs * np.sin(p + np.pi)
            self.data.ctrl[:] = base + offsets
            
        elif self._gait_type == "crawl":
            freq, ts, cs = 1.0, 0.2, 0.3
            p = t * freq * 2 * np.pi
            # 4-phase gait: FL→FR→RL→RR, each pi/2 apart
            offsets[1] = ts * np.sin(p);              offsets[2] = cs * np.sin(p)
            offsets[4] = ts * np.sin(p + np.pi/2);     offsets[5] = cs * np.sin(p + np.pi/2)
            offsets[7] = ts * np.sin(p + np.pi);       offsets[8] = cs * np.sin(p + np.pi)
            offsets[10] = ts * np.sin(p + 1.5*np.pi);  offsets[11] = cs * np.sin(p + 1.5*np.pi)
            self.data.ctrl[:] = base + offsets
            
        elif self._gait_type == "jump":
            # Crouch → spring → land
            cycle = 1.5  # second cycle
            phase = (t % cycle) / cycle  # 0→1
            if phase < 0.3:
                s = phase / 0.3
                self.data.ctrl[:] = base + (s * np.array([0, 0.6, -0.8] * 4))
            elif phase < 0.5:
                s = (phase - 0.3) / 0.2
                self.data.ctrl[:] = np.array([0, 0.6, -0.8] * 4) * s + base
            elif phase < 0.7:
                s = (phase - 0.5) / 0.2
                self.data.ctrl[:] = base * (1 - s)
            else:
                self.data.ctrl[:] = base
                
        elif self._gait_type == "dance":
            freq = 1.0
            p = t * freq * 2 * np.pi
            # Gentle body sway + alternating front leg taps
            sway = 0.08 * np.sin(p)
            offsets[0] = sway   # FR hip sway
            offsets[3] = -sway  # FL hip sway
            offsets[6] = sway   # RR hip sway
            offsets[9] = -sway  # RL hip sway
            
            # Alternating front leg knee lifts
            tap = 0.3 * max(0, np.sin(p))
            offsets[2] = -tap       # FR calf lifts
            offsets[5] = -tap * max(0, np.sin(p + np.pi))  # FL calf alternate
            
            self.data.ctrl[:] = base + offsets
            
    def get_state(self) -> Dict:
        return {
            "qpos": self.data.qpos.tolist(),
            "qvel": self.data.qvel.tolist(),
            "xpos": self.data.xpos.tolist(),
            "xmat": self.data.xmat.tolist(),
            "time": self.data.time,
        }
            
    def set_joint_positions(self, positions: List[float]):
        self._use_gait = False
        for i in range(min(len(positions), len(self.data.ctrl))):
            self.data.ctrl[i] = positions[i]
                    
    def set_controls(self, controls: List[float]):
        self._use_gait = False
        for i, ctrl in enumerate(controls):
            if i < len(self.data.ctrl):
                self.data.ctrl[i] = np.clip(ctrl, -1.0, 1.0)
    
    def start_gait(self, gait_type: str):
        self._gait_type = gait_type
        self._gait_start_time = self.data.time
        self._use_gait = True
    
    def stop_gait(self):
        self._use_gait = False
                    
    def reset(self):
        self._use_gait = False
        self.data.qpos[:] = self.initial_qpos.copy()
        self.data.qvel[:] = self.initial_qvel.copy()
        self.data.ctrl[:] = self.initial_ctrl.copy()
        mujoco.mj_forward(self.model, self.data)
            
    def render_jpeg(self, height: int = 480, width: int = 640, quality: int = 50) -> str:
        """Render + encode JPEG in one call (thread-safe for run_in_executor)."""
        import io, base64
        from PIL import Image
        img = self.render(height, width)
        buf = io.BytesIO()
        Image.fromarray(img).save(buf, format='JPEG', quality=quality)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"
        
    def render(self, height: int = 480, width: int = 640) -> np.ndarray:
        if self._renderer is None:
            import os
            print(f"[Render] {width}x{height}, GPU: {os.environ.get('MUJOCO_GL', '?')}")
            self.model.vis.global_.offwidth = width
            self.model.vis.global_.offheight = height
            self.model.vis.quality.offsamples = 2
            self._renderer = mujoco.Renderer(self.model, height, width)
        
        self._renderer.update_scene(self.data)
        return self._renderer.render()
            
    def get_robot_info(self) -> Dict:
        return {
            "nq": self.model.nq,
            "nv": self.model.nv,
            "nu": self.model.nu,
            "nbody": self.model.nbody,
            "names": [mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, i) 
                     for i in range(self.model.nbody)],
        }
