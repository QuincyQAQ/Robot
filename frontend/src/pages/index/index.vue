<template>
  <view class="app">
    <view class="header">
      <text class="title">🤖 Robot Control System</text>
      <view class="status">
        <view :class="['indicator', connected ? 'connected' : 'disconnected']"></view>
        <text>{{ connected ? 'Connected' : 'Disconnected' }}</text>
      </view>
    </view>

    <view class="main">
      <!-- MuJoCo Render View -->
      <view class="visualization">
        <image
          v-if="renderImage"
          :src="renderImage"
          mode="aspectFit"
          class="render-frame"
        />
        <view v-else class="render-placeholder">
          <text>Waiting for MuJoCo render...</text>
        </view>
      </view>

      <!-- Control Panel -->
      <view class="controls">
        <view class="panel">
          <text class="panel-title">🎮 Joint Control</text>
          <view class="joint-sliders">
            <view v-for="(joint, index) in joints" :key="index" class="joint-row">
              <text class="joint-label">{{ joint.name }}</text>
              <input
                type="range"
                :min="joint.min"
                :max="joint.max"
                step="0.01"
                :value="jointValues[index]"
                @input="onSliderInput(index, $event)"
                class="joint-slider"
              />
              <text class="joint-value">{{ jointValues[index].toFixed(2) }}</text>
            </view>
          </view>
          <view class="btn reset" @click="resetRobot">
            <text>🔄 Reset</text>
          </view>
        </view>

        <view class="panel">
          <text class="panel-title">📊 Robot State</text>
          <view class="state-info">
            <text class="state-line">Time: {{ robotState?.time?.toFixed(2) || 0 }}s</text>
            <text class="state-line">Base Position: {{ getBasePosition() }}</text>
          </view>
        </view>

        <view class="panel">
          <text class="panel-title">🎯 Preset Poses</text>
          <view class="presets">
            <view class="btn" @click="applyPreset('stand')"><text>Stand</text></view>
            <view class="btn" @click="applyPreset('sit')"><text>Sit</text></view>
            <view class="btn" @click="applyPreset('trot')"><text>Trot</text></view>
            <view class="btn" @click="applyPreset('pace')"><text>Pace</text></view>
            <view class="btn" @click="applyPreset('bound')"><text>Bound</text></view>
            <view class="btn" @click="applyPreset('crawl')"><text>Crawl</text></view>
            <view class="btn" @click="applyPreset('jump')"><text>Jump</text></view>
            <view class="btn" @click="applyPreset('dance')"><text>Dance</text></view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
// Backend server address — change for production
const API_BASE = 'http://localhost:8009'
const WS_BASE = 'ws://localhost:8009'

export default {
  name: 'RobotControl',
  data() {
    return {
      connected: false,
      robotState: null,
      renderImage: null,
      stateSocketTask: null,
      renderSocketTask: null,
      controlSocketTask: null,
      // Unitree Go2 joint ordering: FL_abd,FL_thigh,FL_calf, FR_abd,FR_thigh,FR_calf,
      //                           RL_abd,RL_thigh,RL_calf, RR_abd,RR_thigh,RR_calf
      joints: [
        { name: 'FL Hip Abd', min: -0.863, max: 0.863 },
        { name: 'FL Thigh',   min: -0.686, max: 4.501 },
        { name: 'FL Calf',    min: -2.818, max: -0.888 },
        { name: 'FR Hip Abd', min: -0.863, max: 0.863 },
        { name: 'FR Thigh',   min: -0.686, max: 4.501 },
        { name: 'FR Calf',    min: -2.818, max: -0.888 },
        { name: 'RL Hip Abd', min: -0.863, max: 0.863 },
        { name: 'RL Thigh',   min: -0.686, max: 4.501 },
        { name: 'RL Calf',    min: -2.818, max: -0.888 },
        { name: 'RR Hip Abd', min: -0.863, max: 0.863 },
        { name: 'RR Thigh',   min: -0.686, max: 4.501 },
        { name: 'RR Calf',    min: -2.818, max: -0.888 },
      ],
      // Go2 official keyframe: hip=0, thigh=0.9, calf=-1.8
      jointValues: [0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8],
    }
  },
  onLoad() {
    this.connectStateSocket()
    this.connectRenderSocket()
    this.connectControlSocket()
  },
  onUnload() {
    if (this.stateSocketTask) this.stateSocketTask.close()
    if (this.renderSocketTask) this.renderSocketTask.close()
    if (this.controlSocketTask) this.controlSocketTask.close()
  },
  methods: {
    // --- WebSocket connections using uni.connectSocket ---

    connectStateSocket() {
      this.stateSocketTask = uni.connectSocket({
        url: WS_BASE + '/ws/robot/state',
        complete: () => {}
      })

      this.stateSocketTask.onOpen(() => {
        this.connected = true
        console.log('State WebSocket connected')
      })

      this.stateSocketTask.onMessage((res) => {
        this.robotState = JSON.parse(res.data)
      })

      this.stateSocketTask.onClose(() => {
        this.connected = false
        console.log('State WebSocket closed, reconnecting...')
        setTimeout(() => this.connectStateSocket(), 3000)
      })

      this.stateSocketTask.onError((err) => {
        console.error('State WebSocket error:', err)
      })
    },

    connectRenderSocket() {
      this.renderSocketTask = uni.connectSocket({
        url: WS_BASE + '/ws/robot/render',
        complete: () => {}
      })

      this.renderSocketTask.onMessage((res) => {
        const data = JSON.parse(res.data)
        if (data.image) {
          this.renderImage = data.image
        }
      })

      this.renderSocketTask.onClose(() => {
        console.log('Render WebSocket closed, reconnecting...')
        setTimeout(() => this.connectRenderSocket(), 3000)
      })

      this.renderSocketTask.onError((err) => {
        console.error('Render WebSocket error:', err)
      })
    },

    connectControlSocket() {
      this.controlSocketTask = uni.connectSocket({
        url: WS_BASE + '/ws/robot/control',
        complete: () => {}
      })

      this.controlSocketTask.onOpen(() => {
        console.log('Control WebSocket connected')
      })

      this.controlSocketTask.onClose(() => {
        console.log('Control WebSocket closed, reconnecting...')
        setTimeout(() => this.connectControlSocket(), 3000)
      })

      this.controlSocketTask.onError((err) => {
        console.error('Control WebSocket error:', err)
      })
    },

    // --- Joint slider control ---

    onSliderInput(index, event) {
      // UniApp: @input on range slider gives event.detail.value
      const value = parseFloat(event.detail.value)
      this.jointValues[index] = value
      this.sendControl()
    },

    sendControl() {
      if (this.controlSocketTask) {
        this.controlSocketTask.send({
          data: JSON.stringify({
            controls: [...this.jointValues]
          })
        })
      }
    },

    // --- REST API using uni.request wrapped in Promise ---

    async resetRobot() {
      try {
        const res = await this._request('POST', '/api/robot/reset')
        if (res.statusCode === 200) {
          this.jointValues = [0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8]
        }
      } catch (err) {
        console.error('Reset failed:', err)
      }
    },

    async applyPreset(preset) {
      try {
        if (preset === 'stand') {
          await this._request('POST', '/api/robot/gait/stand')
          this.jointValues = [0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8, 0, 0.9, -1.8]
        } else if (preset === 'sit') {
          await this._request('POST', '/api/robot/gait/sit')
          this.jointValues = [0, 1.5, -2.5, 0, 1.5, -2.5, 0, 1.5, -2.5, 0, 1.5, -2.5]
        } else {
          await this._request('POST', '/api/robot/gait/' + preset)
        }
      } catch (err) {
        console.error('Preset failed:', err)
      }
    },

    // Promise wrapper around uni.request
    _request(method, path, body) {
      return new Promise((resolve, reject) => {
        uni.request({
          url: API_BASE + path,
          method: method,
          data: body,
          header: { 'Content-Type': 'application/json' },
          success: resolve,
          fail: reject
        })
      })
    },

    // --- Helpers ---

    getBasePosition() {
      if (!this.robotState?.qpos) return 'N/A'
      const pos = this.robotState.qpos.slice(0, 3)
      return '(' + pos.map(v => v.toFixed(2)).join(', ') + ')'
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

.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
  flex-shrink: 0;
}

.title {
  font-size: 24px;
  font-weight: 600;
  color: #eee;
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #aaa;
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
  gap: 16px;
  padding: 16px;
  flex: 1;
  min-height: 0;
}

.visualization {
  background: #0f3460;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.render-frame {
  width: 100%;
  height: 100%;
}

.render-placeholder {
  color: #666;
  text-align: center;
  font-size: 16px;
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.panel {
  background: #16213e;
  border-radius: 8px;
  padding: 16px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  display: block;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #0f3460;
  color: #eee;
}

.joint-sliders {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.joint-row {
  display: grid;
  grid-template-columns: 80px 1fr 60px;
  align-items: center;
  gap: 8px;
}

.joint-label {
  font-size: 13px;
  color: #aaa;
}

.joint-slider {
  width: 100%;
  accent-color: #4caf50;
}

.joint-value {
  font-size: 13px;
  font-family: monospace;
  text-align: right;
  color: #eee;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  background: #0f3460;
  color: #eee;
  cursor: pointer;
  text-align: center;
  font-size: 14px;
  transition: background 0.2s;
}

.btn:hover {
  background: #1a5276;
}

.btn:active {
  background: #0f3460;
}

.btn.reset {
  width: 100%;
  margin-top: 16px;
  background: #e74c3c;
}

.btn.reset:hover {
  background: #c0392b;
}

.presets {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.presets .btn {
  flex: 1;
  min-width: 70px;
}

.state-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.state-line {
  font-family: monospace;
  font-size: 14px;
  color: #ccc;
}

/* --- Mobile responsive --- */
@media screen and (max-width: 768px) {
  .header {
    padding: 12px 16px;
  }

  .title {
    font-size: 18px;
  }

  .main {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 12px;
    height: auto;
  }

  .visualization {
    min-height: 280px;
    max-height: 50vh;
  }

  .controls {
    gap: 12px;
  }

  .joint-row {
    grid-template-columns: 70px 1fr 55px;
    gap: 6px;
  }

  .joint-label {
    font-size: 12px;
  }

  .joint-value {
    font-size: 12px;
  }

  .presets .btn {
    min-width: 60px;
    font-size: 13px;
    padding: 6px 10px;
  }
}
</style>
