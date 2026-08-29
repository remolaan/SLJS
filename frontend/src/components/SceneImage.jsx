import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

const cache = new Map()

/**
 * Fetches (and caches by prompt) a generated scene image from the backend,
 * or shows a loading / fallback state. The backend returns an inline SVG data
 * URL when no OpenRouter key is configured, so it always renders something.
 */
export default function SceneImage({ prompt, label, className = '', height = 'auto' }) {
  const [src, setSrc] = useState(cache.get(prompt) || null)
  const [status, setStatus] = useState(cache.has(prompt) ? 'ready' : 'loading')

  useEffect(() => {
    if (cache.has(prompt)) {
      setSrc(cache.get(prompt))
      setStatus('ready')
      return
    }
    let cancelled = false
    setStatus('loading')
    api
      .generateImage(prompt)
      .then((r) => {
        if (cancelled) return
        cache.set(prompt, r.image)
        setSrc(r.image)
        setStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [prompt])

  if (status === 'loading') {
    return <div className={`scene-img scene-placeholder ${className}`} style={{ height }}>🎨 Generating scene…</div>
  }
  if (status === 'error') {
    return <div className={`scene-img scene-error ${className}`} style={{ height }}>⚠️ Could not generate image</div>
  }

  return (
    <figure className={`scene-figure ${className}`}>
      <img className="scene-img" src={src} alt={label || 'scene'} />
      {label && <figcaption>{label}</figcaption>}
    </figure>
  )
}
