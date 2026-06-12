<template>
  <div class="app">
    <header class="header">
      <h1>🤖 Robot Control System</h1>
      <div class="status">
        <span :class="['indicator', connected ? 'connected' : 'disconnected']"></span>
        {{ connected ? 'Connected' : 'Disconnected' }}
      </div>
    </header>

    <main class="main">
      <!-- MuJoCo Render View -->
      <div class="visualization">
        <img v-if="renderImage" :src="renderImage" alt="MuJoCo Render" class="render-frame" />
        <div v-else class="render-placeholder">
          <p>Waiting for MuJoCo render...</p>
        </div>
      </div>

      <!-- Control Panel -->
      <div class="controls">
        <div class="panel">
          <h2>🎮 Joint Control</h2>
          <div class="joint-sliders">
            <div v-for="(joint, index) in joints" :key="index" class="joint-row">
              <label>{{ joint.name }}</label>
              <input
                type="range"
                :min="joint.min"
                :max="joint.max"
                step="0.01"
                v-model.number="jointValues[index]"
                @input="sendControl"
              />
              <span class="value">{{ jointValues[index].toFixed(2) }}</span>
            </div>
          </div>
          <button class="btn reset" @click="resetRobot">🔄 Reset</button>
        </div>

        <div class="panel">
          <h2>📊 Robot State</h2>
          <div class="state-info">
            <p>Time: {{ robotState?.time?.toFixed(2) || 0 }}s</p>
            <p>Base Position: {{ getBasePosition() }}</p>
          </div>
        </div>

        <div class="panel">
          <h2>🎯 Preset Poses</h2>
          <div class="presets">
            <button class="btn" @click="applyPreset('stand')">Stand</button>
            <button class="btn" @click="applyPreset('sit')">Sit</button>
            <button class="btn" @click="applyPreset('trot')">Trot</button>
            <button class="btn" @click="applyPreset('pace')">Pace</button>
            <button class="btn" @click="applyPreset('bound')">Bound</button>
            <button class="btn" @click="applyPreset('crawl')">Crawl</button>
            <button class="btn" @click="applyPreset('jump')">Jump</button>
            <button class="btn" @click="applyPreset('dance')">Dance</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      connected: false,
      robotState: null,
      renderImage: null,
      stateWs: null,
      renderWs: null,
      controlWs: null,
      // Official Unitree Go1 joint configuration: 12 position-controlled motors
      // Order: FR_abd,FR_thigh,FR_calf, FL_abd,FL_thigh,FL_calf, RR_abd,RR_thigh,RR_calf, RL_abd,RL_thigh,RL_calf
      joints: [
        { name: 'FR Hip Abd', min: -0.863, max: 0.863 },
        { name: 'FR Thigh', min: -0.686, max: 4.501 },
        { name: 'FR Calf', min: -2.818, max: -0.888 },
        { name: 'FL Hip Abd', min: -0.863, max: 0.863 },
        { name: 'FL Thigh', min: -0.686, max: 4.501 },
        { name: 'FL Calf', min: -2.818, max: -0.888 },
        { name: 'RR Hip Abd', min: -0.863, max: 0.863 },
        { name: 'RR Thigh', min: -0.686, max: 4.501 },
        { name: 'RR Calf', min: -2.818, max: -0.888 },
        { name: 'RL Hip Abd', min: -0.863, max: 0.863 },
        { name: 'RL Thigh', min: -0.686, max: 4.501 },
        { name: 'RL Calf', min: -2.818, max: -0.888 },
      ],
      // Home pose (standing): all abductions=0, thighs=0.9, calves=-1.8
      jointValues: [0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8],
    }
  },
  mounted() {
    this.connectStateWebSocket()
    this.connectRenderWebSocket()
    this.connectControlWebSocket()
  },
  beforeUnmount() {
    if (this.stateWs) this.stateWs.close()
    if (this.renderWs) this.renderWs.close()
    if (this.controlWs) this.controlWs.close()
  },
  methods: {
    connectStateWebSocket() {
      this.stateWs = new WebSocket('ws://localhost:8009/ws/robot/state')
      
      this.stateWs.onopen = () => {
        this.connected = true
        console.log('Connected to state WebSocket')
      }
      
      this.stateWs.onmessage = (event) => {
        this.robotState = JSON.parse(event.data)
      }
      
      this.stateWs.onclose = () => {
        this.connected = false
        setTimeout(() => this.connectStateWebSocket(), 3000)
      }
    },
    
    connectRenderWebSocket() {
      this.renderWs = new WebSocket('ws://localhost:8009/ws/robot/render')
      
      this.renderWs.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.image) {
          this.renderImage = data.image
        }
      }
      
      this.renderWs.onclose = () => {
        setTimeout(() => this.connectRenderWebSocket(), 3000)
      }
    },
    
    connectControlWebSocket() {
      this.controlWs = new WebSocket('ws://localhost:8009/ws/robot/control')
      
      this.controlWs.onopen = () => {
        console.log('Control WebSocket connected')
      }
      
      this.controlWs.onclose = () => {
        console.log('Control WebSocket disconnected, reconnecting...')
        setTimeout(() => this.connectControlWebSocket(), 3000)
      }
    },
    
    sendControl() {
      if (this.controlWs && this.controlWs.readyState === WebSocket.OPEN) {
        this.controlWs.send(JSON.stringify({
          controls: [...this.jointValues]
        }))
      } else {
        console.warn('Control WebSocket not ready, state:', this.controlWs?.readyState)
      }
    },
    
    async resetRobot() {
      await fetch('http://localhost:8009/api/robot/reset', { method: 'POST' })
      this.jointValues = [0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8]
    },
    
    async applyPreset(preset) {
      if (preset === 'stand') {
        await fetch('http://localhost:8009/api/robot/gait/stand', { method: 'POST' })
        this.jointValues = [0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8]
      } else if (preset === 'sit') {
        await fetch('http://localhost:8009/api/robot/gait/sit', { method: 'POST' })
        this.jointValues = [0, 1.5, -2.5, 0, 1.5, -2.5, 0, 1.5, -2.5, 0, 1.5, -2.5]
      } else {
        await fetch('http://localhost:8009/api/robot/gait/' + preset, { method: 'POST' })
      }
    },
    
    getBasePosition() {
      if (!this.robotState?.qpos) return 'N/A'
      const pos = this.robotState.qpos.slice(0, 3)
      return `(${pos.map(v => v.toFixed(2)).join(', ')})`
    },
  },
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #1a1a2e;
  color: #eee;
}

.app {
  min-height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.header h1 {
  font-size: 1.5rem;
}

.status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.indicator.connected {
  background: #4caf50;
  box-shadow: 0 0 10px #4caf50;
}

.indicator.disconnected {
  background: #f44336;
}

.main {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 1rem;
  padding: 1rem;
  height: calc(100vh - 60px);
}

.visualization {
  background: #0f3460;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.render-frame {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.render-placeholder {
  color: #666;
  text-align: center;
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
}

.panel h2 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #0f3460;
}

.joint-sliders {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.joint-row {
  display: grid;
  grid-template-columns: 80px 1fr 60px;
  align-items: center;
  gap: 0.5rem;
}

.joint-row label {
  font-size: 0.85rem;
  color: #aaa;
}

.joint-row input[type="range"] {
  width: 100%;
  accent-color: #4caf50;
}

.joint-row .value {
  font-size: 0.85rem;
  font-family: monospace;
  text-align: right;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background: #0f3460;
  color: #eee;
  cursor: pointer;
  transition: background 0.2s;
}

.btn:hover {
  background: #1a5276;
}

.btn.reset {
  width: 100%;
  margin-top: 1rem;
  background: #e74c3c;
}

.btn.reset:hover {
  background: #c0392b;
}

.presets {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.presets .btn {
  flex: 1;
  min-width: 80px;
}

.state-info p {
  margin: 0.5rem 0;
  font-family: monospace;
  font-size: 0.9rem;
}
</style>
