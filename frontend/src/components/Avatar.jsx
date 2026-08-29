import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

export const CHARACTERS = {
  judge: { name: 'Judge', color: '#7a2e1d', img: 'avatar_judge' },
  prosecution: { name: 'Prosecution', color: '#b23b1e', img: 'avatar_prosecution' },
  defense: { name: 'Defense', color: '#2f6db2', img: 'avatar_defense' },
  witness: { name: 'Witness', color: '#8a7a3f', img: 'avatar_witness' },
  intake: { name: 'Clerk', color: '#5a5a5a', img: 'avatar_intake' },
}

const fallbackRole = (role) =>
  CHARACTERS[role] || { name: role, color: '#555', img: 'avatar_intake' }

// Module-level manifest cache (fetched once).
let manifestPromise = null
function getManifest() {
  if (!manifestPromise) {
    manifestPromise = api.imageManifest().then((r) => r.images || {}).catch(() => ({}))
  }
  return manifestPromise
}

/**
 * Shows a pre-generated static avatar (from the backend's static cache).
 * Loads instantly, no per-load generation.
 */
export default function Avatar({ role, size = 40 }) {
  const meta = fallbackRole(role)
  const [src, setSrc] = useState(null)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false
    getManifest().then((urls) => {
      if (cancelled) return
      const url = urls[meta.img]
      if (url) {
        setSrc(url)
        setStatus('ready')
      } else {
        setStatus('fallback')
      }
    })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta.img])

  const style = { width: size, height: size, fontSize: size * 0.45, background: meta.color }

  if (status === 'ready' && src) {
    return <img className="avatar" src={src} alt={meta.name} style={style} />
  }
  if (status === 'fallback') {
    return <div className="avatar avatar-fallback" style={style}>{meta.name[0]}</div>
  }
  return <div className="avatar avatar-loading" style={style}>•</div>
}