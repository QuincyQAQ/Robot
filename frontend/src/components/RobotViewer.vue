<template>
  <div ref="container" class="robot-viewer"></div>
</template>

<script>
import * as THREE from 'three'
import { markRaw } from 'vue'

export default {
  name: 'RobotViewer',
  props: {
    robotState: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      _three: null,
      animationId: null,
    }
  },
  mounted() {
    this._three = markRaw({
      scene: null,
      camera: null,
      renderer: null,
      robotParts: {},
    })
    this.initThreeJS()
    this.createRobot()
    this.animate()
  },
  beforeUnmount() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
    }
    if (this._three?.renderer) {
      this._three.renderer.dispose()
    }
  },
  watch: {
    robotState: {
      handler(newState) {
        if (newState && newState.qpos) {
          this.updateRobotPose(newState.qpos)
        }
      },
      deep: true,
    },
  },
  methods: {
    initThreeJS() {
      const container = this.$refs.container
      const width = container.clientWidth
      const height = container.clientHeight
      const t = this._three

      // Scene
      t.scene = new THREE.Scene()
      t.scene.background = new THREE.Color(0x0f3460)

      // Camera
      t.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100)
      t.camera.position.set(1, 1, 1.5)
      t.camera.lookAt(0, 0, 0.2)

      // Renderer
      t.renderer = new THREE.WebGLRenderer({ antialias: true })
      t.renderer.setSize(width, height)
      t.renderer.shadowMap.enabled = true
      container.appendChild(t.renderer.domElement)

      // Lights
      const ambientLight = new THREE.AmbientLight(0x404040, 0.5)
      t.scene.add(ambientLight)

      const directionalLight = new THREE.DirectionalLight(0xffffff, 1)
      directionalLight.position.set(1, 2, 1)
      directionalLight.castShadow = true
      t.scene.add(directionalLight)

      // Grid
      const gridHelper = new THREE.GridHelper(2, 20, 0x1a5276, 0x0a2a4a)
      t.scene.add(gridHelper)

      // Orbit controls
      this.setupOrbitControls()
    },

    setupOrbitControls() {
      const t = this._three
      let isDragging = false
      let previousMousePosition = { x: 0, y: 0 }

      t.renderer.domElement.addEventListener('mousedown', (e) => {
        isDragging = true
        previousMousePosition = { x: e.clientX, y: e.clientY }
      })

      t.renderer.domElement.addEventListener('mousemove', (e) => {
        if (!isDragging) return

        const deltaMove = {
          x: e.clientX - previousMousePosition.x,
          y: e.clientY - previousMousePosition.y,
        }

        const spherical = new THREE.Spherical()
        const offset = new THREE.Vector3()
        offset.copy(t.camera.position).sub(new THREE.Vector3(0, 0, 0))
        spherical.setFromVector3(offset)

        spherical.theta -= deltaMove.x * 0.01
        spherical.phi -= deltaMove.y * 0.01
        spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi))

        offset.setFromSpherical(spherical)
        t.camera.position.copy(offset)
        t.camera.lookAt(0, 0, 0.2)

        previousMousePosition = { x: e.clientX, y: e.clientY }
      })

      t.renderer.domElement.addEventListener('mouseup', () => {
        isDragging = false
      })

      t.renderer.domElement.addEventListener('wheel', (e) => {
        const scale = e.deltaY > 0 ? 1.1 : 0.9
        t.camera.position.multiplyScalar(scale)
      })
    },

    createRobot() {
      const t = this._three

      const bodyMaterial = new THREE.MeshStandardMaterial({
        color: 0x2ecc71,
        metalness: 0.3,
        roughness: 0.7,
      })

      const jointMaterial = new THREE.MeshStandardMaterial({
        color: 0x3498db,
        metalness: 0.5,
        roughness: 0.5,
      })

      // Base body
      const baseGeom = new THREE.BoxGeometry(0.3, 0.1, 0.16)
      const base = new THREE.Mesh(baseGeom, bodyMaterial)
      base.position.y = 0.35
      base.castShadow = true
      t.scene.add(base)
      t.robotParts.base = base

      // Create legs
      const legConfigs = [
        { name: 'FL', x: 0.15, y: 0.08, z: 0 },
        { name: 'FR', x: 0.15, y: -0.08, z: 0 },
        { name: 'RL', x: -0.15, y: 0.08, z: 0 },
        { name: 'RR', x: -0.15, y: -0.08, z: 0 },
      ]

      legConfigs.forEach((config) => {
        const legGroup = new THREE.Group()
        legGroup.position.set(config.x, 0.35, config.z)

        // Hip joint
        const hipGeom = new THREE.CylinderGeometry(0.03, 0.03, 0.08, 16)
        const hip = new THREE.Mesh(hipGeom, jointMaterial)
        hip.rotation.x = Math.PI / 2
        legGroup.add(hip)

        // Thigh
        const thighGroup = new THREE.Group()
        thighGroup.position.y = config.name.includes('L') ? 0.06 : -0.06

        const thighGeom = new THREE.BoxGeometry(0.04, 0.2, 0.04)
        const thigh = new THREE.Mesh(thighGeom, jointMaterial)
        thigh.position.y = -0.1
        thighGroup.add(thigh)

        // Calf
        const calfGroup = new THREE.Group()
        calfGroup.position.y = -0.2

        const calfGeom = new THREE.BoxGeometry(0.03, 0.16, 0.03)
        const calf = new THREE.Mesh(calfGeom, jointMaterial)
        calf.position.y = -0.08
        calfGroup.add(calf)

        thighGroup.add(calfGroup)
        legGroup.add(thighGroup)

        t.scene.add(legGroup)
        t.robotParts[config.name] = {
          hip: legGroup,
          thigh: thighGroup,
          calf: calfGroup,
        }
      })
    },

    updateRobotPose(qpos) {
      const t = this._three
      if (!qpos || qpos.length < 12) return

      const jointMap = ['FL', 'FR', 'RL', 'RR']
      
      jointMap.forEach((leg, i) => {
        const part = t.robotParts[leg]
        if (!part) return

        const thighIdx = i * 3 + 1
        const calfIdx = i * 3 + 2

        part.thigh.rotation.x = qpos[thighIdx] || 0
        part.calf.rotation.x = qpos[calfIdx] || 0
      })

      if (t.robotParts.base && qpos.length >= 3) {
        t.robotParts.base.position.set(
          qpos[0] || 0,
          (qpos[1] || 0) + 0.35,
          qpos[2] || 0
        )
      }
    },

    animate() {
      this.animationId = requestAnimationFrame(() => this.animate())
      this._three.renderer.render(this._three.scene, this._three.camera)
    },
  },
}
</script>

<style scoped>
.robot-viewer {
  width: 100%;
  height: 100%;
}
</style>
