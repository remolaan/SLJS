import React, { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Html, Image } from '@react-three/drei'
import * as THREE from 'three'
import { api } from '../api.js'

const SPEAKER_ROLES = ['judge', 'prosecution', 'defense', 'witness', 'intake']

// 3D positions of each participant in the courtroom.
const POS = {
  judge: [0, 1.7, -4],
  witness: [1.6, 1.4, 0.5],
  prosecution: [-2.4, 1.4, 0.8],
  defense: [2.4, 1.4, 0.8],
  intake: [4.2, 1.5, -3.5],
}

// Camera target when each speaker is active (pans toward them).
const CAM = {
  judge: { pos: [0, 2.6, 4.5], look: [0, 1.6, -4] },
  witness: { pos: [1.6, 2.2, 5.0], look: [1.6, 1.4, 0.5] },
  prosecution: { pos: [-2.4, 2.2, 5.2], look: [-2.4, 1.4, 0.8] },
  defense: { pos: [2.4, 2.2, 5.2], look: [2.4, 1.4, 0.8] },
  intake: { pos: [4.2, 2.2, 4.5], look: [4.2, 1.5, -3.5] },
}

const COLORS = {
  judge: '#7a2e1d',
  prosecution: '#b23b1e',
  defense: '#2f6db2',
  witness: '#8a7a3f',
  intake: '#5a5a5a',
}

// Load the static image URLs once (shared manifest cache).
let manifestPromise = null
function getManifest() {
  if (!manifestPromise) {
    manifestPromise = api.imageManifest().then((r) => r.images || {}).catch(() => ({}))
  }
  return manifestPromise
}

// Camera rig: smoothly pans toward the active speaker.
function CameraRig({ active }) {
  const { camera } = useThree()
  const target = CAM[active] || CAM.judge
  const goal = useMemo(() => new THREE.Vector3(...target.pos), [active])
  const look = useMemo(() => new THREE.Vector3(...target.look), [active])

  useFrame(() => {
    camera.position.x += (goal.x - camera.position.x) * 0.06
    camera.position.y += (goal.y - camera.position.y) * 0.06
    camera.position.z += (goal.z - camera.position.z) * 0.06
    camera.lookAt(look)
  })
  return null
}

// A character avatar as a textured image billboard in the courtroom.
function Character({ role, active, url }) {
  const color = COLORS[role]
  const isActive = active === role
  const [hover, setHover] = useState(false)

  return (
    <group position={POS[role]}>
      {/* nameplate */}
      <Html position={[0, 1.7, 0]} center distanceFactor={10} className="charname-wrap">
        <div className={`charname ${isActive ? 'active' : ''}`} style={{ borderColor: color }}>
          {role.toUpperCase()}
        </div>
      </Html>
      {/* avatar sprite */}
      <Image
        url={url}
        position={[0, 0.55, 0]}
        scale={[1.3, 1.6, 1]}
        transparent
        onPointerOver={() => setHover(true)}
        onPointerOut={() => setHover(false)}
      />
      {/* highlight ring / glow when speaking */}
      <mesh position={[0, -0.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.85, 1.0, 32]} />
        <meshBasicMaterial color={isActive ? '#ffd98a' : '#444'} transparent opacity={isActive ? 0.9 : 0.3} />
      </mesh>
    </group>
  )
}

// Floor + walls + bench + tables (simple low-poly courtroom).
function Courtroom() {
  return (
    <group>
      {/* floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
        <planeGeometry args={[14, 12]} />
        <meshStandardMaterial color="#8a6a45" roughness={0.9} />
      </mesh>
      {/* back wall */}
      <mesh position={[0, 3, -6]}>
        <boxGeometry args={[14, 6, 0.3]} />
        <meshStandardMaterial color="#6b4a2f" />
      </mesh>
      {/* judge bench (raised) */}
      <group position={[0, 0, -4.4]}>
        <mesh position={[0, 0.6, 0]}>
          <boxGeometry args={[3, 1.2, 1.2]} />
          <meshStandardMaterial color="#5c2e0c" />
        </mesh>
        <mesh position={[0, 1.5, 0]}>
          <boxGeometry args={[2.4, 0.8, 0.6]} />
          <meshStandardMaterial color="#7a4a1f" />
        </mesh>
      </group>
      {/* prosecution table (left) */}
      <mesh position={[-2.4, 0.45, 1.2]} rotation={[0, 0, 0]}>
        <boxGeometry args={[1.8, 0.9, 0.9]} />
        <meshStandardMaterial color="#6b4a2f" />
      </mesh>
      {/* defense table (right) */}
      <mesh position={[2.4, 0.45, 1.2]}>
        <boxGeometry args={[1.8, 0.9, 0.9]} />
        <meshStandardMaterial color="#6b4a2f" />
      </mesh>
      {/* witness stand */}
      <mesh position={[1.6, 0.5, 0.8]}>
        <boxGeometry args={[0.8, 1.0, 0.8]} />
        <meshStandardMaterial color="#8a6a45" />
      </mesh>
      {/* clerk desk */}
      <mesh position={[4.2, 0.45, -3.6]}>
        <boxGeometry args={[1.2, 0.9, 0.9]} />
        <meshStandardMaterial color="#5a432e" />
      </mesh>
      {/* lighting */}
      <ambientLight intensity={0.6} />
      <directionalLight position={[3, 6, 3]} intensity={0.9} />
    </group>
  )
}

export default function Courtroom3D({ snapshot }) {
  const [urls, setUrls] = useState({})
  const active = snapshot?.current_node === 'judge' ? 'judge' : lastSpeaker(snapshot)

  useEffect(() => {
    getManifest().then(setUrls)
  }, [])

  const hasImage = urls.avatar_judge

  return (
    <div className="court3d">
      <Canvas camera={{ position: [0, 3, 6], fov: 55 }}>
        <Suspense fallback={null}>
          <Courtroom />
          {hasImage && (
            <>
              <Character role="judge" active={active} url={urls.avatar_judge} />
              <Character role="prosecution" active={active} url={urls.avatar_prosecution} />
              <Character role="defense" active={active} url={urls.avatar_defense} />
              <Character role="witness" active={active} url={urls.avatar_witness} />
              <Character role="intake" active={active} url={urls.avatar_intake} />
            </>
          )}
          <CameraRig active={active} />
        </Suspense>
      </Canvas>
      {!hasImage && <div className="court3d-loading">🏛️ Loading courtroom…</div>}
    </div>
  )
}

function lastSpeaker(snapshot) {
  const tr = snapshot?.transcript || []
  for (let i = tr.length - 1; i >= 0; i--) {
    if (SPEAKER_ROLES.includes(tr[i].role)) return tr[i].role
  }
  return 'judge'
}