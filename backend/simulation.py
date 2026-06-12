"""
MuJoCo Simulation Engine for Unitree Go2
Go2 motors are pure torque. We use explicit PD control to track joint positions.
"""

import mujoco
import numpy as np
from typing import Dict, List


class MujocoSimulator:
    def __init__(self, xml_path: str = "/home/cxhlab/lqj_code/data/mujoco_menagerie/unitree_go2/scene.xml"):
        self.model = mujoco.MjModel.from_xml_path(xml_path)
        self.data = mujoco.MjData(self.model)
        
        # Load official keyframe
        if self.model.nkey > 0:
            mujoco.mj_resetDataKeyframe(self.model, self.data, 0)
            mujoco.mj_forward(self.model, self.data)
        
        self.initial_qpos = self.data.qpos.copy()
        self.initial_qvel = self.data.qvel.copy()
        
        # PD gains for Go2 torque motors (kp=100, kd=2)
        self.kp = 100.0
        self.kd = 2.0
        
        # Target joint positions (set by gait or manual control)
        self._target = self.initial_qpos[7:].copy()
        
        self._renderer = None

        # Dual camera presets (azimuth/elevation in radians, distance in meters)
        # 视角一: custom view (closer side angle)
        # 视角二: MuJoCo default (classic isometric-like view)
        self._camera_presets = {
            1: {"azimuth": 0.0,   "elevation": -0.35,  "distance": 3.0},   # 视角一 (my defaults)
            2: {"azimuth": 90.0,  "elevation": -45.0,  "distance": 2.0},   # 视角二 (MuJoCo original)
        }
        self._active_preset = 1   # currently active camera preset

        self._gait_type = None
        self._gait_start_time = 0
        self._use_gait = False
            
    def step(self):
        """Physics step with PD torque control."""
        if self._use_gait:
            self._compute_gait_targets()
        
        # PD control: torque = kp*(target - actual) - kd*velocity
        for i in range(12):
            torque = self.kp * (self._target[i] - self.data.qpos[7+i]) - self.kd * self.data.qvel[6+i]
            self.data.ctrl[i] = torque
        
        mujoco.mj_step(self.model, self.data)
    
    def _compute_gait_targets(self):
        """Update target joint positions for current gait."""
        t = self.data.time - self._gait_start_time
        # Go2 official keyframe: hip=0, thigh=0.9, calf=-1.8
        base = np.array([0.0, 0.9, -1.8] * 4)
        offsets = np.zeros(12)
        
        if self._gait_type == "stand":
            self._target[:] = base
            
        elif self._gait_type == "sit":
            self._target[:] = np.array([0.0, 1.5, -2.5] * 4)
            
        elif self._gait_type == "trot":
            f, a = 2.0, 0.3
            p = t * f * 2 * np.pi
            offsets[1] = a*np.sin(p);          offsets[2] = a*0.5*np.sin(p)
            offsets[4] = a*np.sin(p+np.pi);    offsets[5] = a*0.5*np.sin(p+np.pi)
            offsets[7] = a*np.sin(p+np.pi);    offsets[8] = a*0.5*np.sin(p+np.pi)
            offsets[10]= a*np.sin(p);          offsets[11]= a*0.5*np.sin(p)
            self._target[:] = base + offsets
            
        elif self._gait_type == "pace":
            f, a = 1.5, 0.2
            p = t * f * 2 * np.pi
            offsets[1] = a*np.sin(p);          offsets[2] = a*0.5*np.sin(p)
            offsets[4] = a*np.sin(p+np.pi);    offsets[5] = a*0.5*np.sin(p+np.pi)
            offsets[7] = a*np.sin(p);          offsets[8] = a*0.5*np.sin(p)
            offsets[10]= a*np.sin(p+np.pi);    offsets[11]= a*0.5*np.sin(p+np.pi)
            self._target[:] = base + offsets
            
        elif self._gait_type == "bound":
            f, a = 2.5, 0.3
            p = t * f * 2 * np.pi
            offsets[1] = a*np.sin(p);          offsets[2] = a*0.5*np.sin(p)
            offsets[4] = a*np.sin(p);          offsets[5] = a*0.5*np.sin(p)
            offsets[7] = a*np.sin(p+np.pi);    offsets[8] = a*0.5*np.sin(p+np.pi)
            offsets[10]= a*np.sin(p+np.pi);    offsets[11]= a*0.5*np.sin(p+np.pi)
            self._target[:] = base + offsets
            
        elif self._gait_type == "crawl":
            f, a = 1.0, 0.15
            p = t * f * 2 * np.pi
            offsets[1] = a*np.sin(p);              offsets[2] = a*0.5*np.sin(p)
            offsets[4] = a*np.sin(p+np.pi/2);       offsets[5] = a*0.5*np.sin(p+np.pi/2)
            offsets[7] = a*np.sin(p+np.pi);         offsets[8] = a*0.5*np.sin(p+np.pi)
            offsets[10]= a*np.sin(p+1.5*np.pi);     offsets[11]= a*0.5*np.sin(p+1.5*np.pi)
            self._target[:] = base + offsets
            
        elif self._gait_type == "jump":
            cycle = 1.5
            ph = (t % cycle) / cycle
            if ph < 0.3:
                self._target[:] = base + (ph/0.3)*np.array([0, 0.5, -0.6]*4)
            elif ph < 0.5:
                s = (ph-0.3)/0.2
                self._target[:] = np.array([0, 0.5, -0.6]*4)*s + base
            elif ph < 0.7:
                s = (ph-0.5)/0.2
                self._target[:] = base*(1-s)
            else:
                self._target[:] = base
                
        elif self._gait_type == "dance":
            p = t * 1.0 * 2 * np.pi
            s = 0.05*np.sin(p)
            offsets[0]=s; offsets[3]=-s; offsets[6]=s; offsets[9]=-s
            tap = 0.2*max(0, np.sin(p))
            offsets[2] = -tap
            offsets[5] = -tap*max(0, np.sin(p+np.pi))
            self._target[:] = base + offsets
            
    def get_state(self) -> Dict:
        return {
            "qpos": self.data.qpos.tolist(), "qvel": self.data.qvel.tolist(),
            "xpos": self.data.xpos.tolist(), "xmat": self.data.xmat.tolist(),
            "time": self.data.time,
        }
            
    def set_joint_positions(self, positions: List[float]):
        self._use_gait = False
        for i in range(min(len(positions), 12)):
            self._target[i] = positions[i]
                    
    def set_controls(self, controls: List[float]):
        self._use_gait = False
        for i in range(min(len(controls), 12)):
            self._target[i] = controls[i]
    
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
        self._target[:] = self.initial_qpos[7:].copy()
        mujoco.mj_forward(self.model, self.data)
            
    def render_jpeg(self, height=480, width=640, quality=50) -> str:
        import io, base64
        from PIL import Image
        img = self.render(height, width)
        buf = io.BytesIO()
        Image.fromarray(img).save(buf, format='JPEG', quality=quality)
        return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
        
    def render(self, height=480, width=640) -> np.ndarray:
        if self._renderer is None:
            import os
            print(f"[Render] {width}x{height}, GPU: {os.environ.get('MUJOCO_GL','?')}")
            self.model.vis.global_.offwidth = width
            self.model.vis.global_.offheight = height
            self.model.vis.quality.offsamples = 2
            self._renderer = mujoco.Renderer(self.model, height, width)

        # Create MjvCamera using the active preset
        p = self._camera_presets[self._active_preset]
        cam = mujoco.MjvCamera()
        cam.azimuth = p["azimuth"]
        cam.elevation = p["elevation"]
        cam.distance = p["distance"]
        cam.lookat = self.data.body('base').xpos.copy() if self.model.nbody > 1 else [0, 0, 0.25]
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE

        self._renderer.update_scene(self.data, camera=cam)
        return self._renderer.render()

    def move_camera(self, action: str, step: float = 0.15):
        """Move camera: left, right, up, down, zoom_in, zoom_out (affects active preset)"""
        p = self._camera_presets[self._active_preset]
        if action == "left":
            p["azimuth"] -= step
        elif action == "right":
            p["azimuth"] += step
        elif action == "up":
            p["elevation"] += step * 0.5
        elif action == "down":
            p["elevation"] -= step * 0.5
        elif action == "zoom_in":
            p["distance"] = max(0.3, p["distance"] - step)
        elif action == "zoom_out":
            p["distance"] = min(20.0, p["distance"] + step)

    def switch_camera_preset(self, preset: int):
        """Switch to preset 1 or 2"""
        if preset in (1, 2):
            self._active_preset = preset

    def get_camera_info(self) -> Dict:
        p = self._camera_presets[self._active_preset]
        return {
            "active_preset": self._active_preset,
            "presets": self._camera_presets,
            "azimuth": p["azimuth"],
            "elevation": p["elevation"],
            "distance": p["distance"],
        }
            
    def get_robot_info(self) -> Dict:
        return {
            "nq": self.model.nq, "nv": self.model.nv, "nu": self.model.nu,
            "nbody": self.model.nbody,
            "names": [mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, i) 
                     for i in range(self.model.nbody)],
        }
