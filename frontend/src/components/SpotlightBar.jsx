import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import Avatar, { CHARACTERS } from './Avatar.jsx'

const SPEAKER_ROLES = ['judge', 'prosecution', 'defense', 'witness', 'intake']

function lastSpeaker(snapshot) {
  const tr = snapshot?.transcript || []
  for (let i = tr.length - 1; i >= 0; i--) {
    if (SPEAKER_ROLES.includes(tr[i].role)) return tr[i].role
  }
  return 'intake'
}

/**
 * A single sticky strip at the top of the chat feed: a big pulsing avatar of
 * whoever is currently speaking (or about to), plus a short narration caption.
 * This replaces the old absolutely-positioned "room with seats" — it never
 * clips, never overlaps, and scales to any screen size because it's just a
 * flex row, not pixel-tuned percentage coordinates.
 */
export default function SpotlightBar({ snapshot, busy }) {
  const currentRole = snapshot?.current_node === 'judge' ? 'judge' : lastSpeaker(snapshot)
  const meta = CHARACTERS[currentRole] || CHARACTERS.intake
  const [narration, setNarration] = useState('')

  useEffect(() => {
    if (!snapshot?.trial_id) return
    let cancelled = false
    api.trialScene(snapshot.trial_id).then((r) => {
      if (!cancelled) setNarration(r.caption)
    }).catch(() => {})
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot?.trial_id, snapshot?.current_node, snapshot?.transcript?.length])

  if (!snapshot) return null

  return (
    <div className="spotlight">
      <div className={`spotlight-avatar ${busy ? 'pulsing' : ''}`}>
        <Avatar role={currentRole} size={56} />
      </div>
      <div className="spotlight-info">
        <div className="spotlight-name" style={{ color: meta.color }}>
          {meta.name}
          {busy && <span className="spotlight-typing"> is speaking…</span>}
        </div>
        {narration && <div className="spotlight-caption">{narration}</div>}
      </div>
      {snapshot.stage_label && <span className="pill stage-pill spotlight-stage">{snapshot.stage_label}</span>}
    </div>
  )
}
