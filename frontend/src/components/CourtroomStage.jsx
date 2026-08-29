import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import Avatar, { CHARACTERS } from './Avatar.jsx'

const POSITIONS = {
  judge: { left: '50%', top: '10%', transform: 'translateX(-50%)' },
  witness: { left: '50%', top: '56%', transform: 'translateX(-50%)' },
  prosecution: { left: '20%', top: '56%', transform: 'translateX(-50%)' },
  defense: { left: '80%', top: '56%', transform: 'translateX(-50%)' },
  intake: { left: '8%', top: '12%', transform: 'translateX(-50%)' },
}

const SPEAKER_ROLES = ['judge', 'prosecution', 'defense', 'witness', 'intake']

export default function CourtroomStage({ snapshot, onAsk }) {
  const stage = snapshot?.stage_label || 'Case Intake'
  const currentRole = snapshot?.current_node === 'judge' ? 'judge' : lastSpeaker(snapshot)
  const [narration, setNarration] = useState('')
  const [currentText, setCurrentText] = useState('')

  useEffect(() => {
    const tr = snapshot?.transcript || []
    if (!tr.length) return
    setCurrentText(tr[tr.length - 1].content)
  }, [snapshot?.transcript?.length])

  useEffect(() => {
    if (!snapshot?.trial_id) return
    let cancelled = false
    api.trialScene(snapshot.trial_id).then((r) => {
      if (!cancelled) setNarration(r.caption)
    }).catch(() => {})
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot?.trial_id, snapshot?.current_node, snapshot?.transcript?.length])

  return (
    <div className="stage-wrap">
      {/* Top bar */}
      <div className="stage-head">
        <h2>{snapshot?.case?.title || 'Courtroom'}</h2>
        <span className="pill stage-pill">{stage}</span>
        <span className={`pill ${snapshot?.status === 'complete' ? 'ok' : ''}`}>{snapshot?.status || 'idle'}</span>
      </div>

      {/* The courtroom room */}
      <div className="courtroom-stage">
        <div className="bench" />
        <div className="floor" />

        <div className={`seat judge ${currentRole === 'judge' ? 'active' : ''}`} style={POSITIONS.judge}>
          <Avatar role="judge" size={170} />
          <div className="seat-label">THE JUDGE</div>
        </div>
        <div className={`seat witness ${currentRole === 'witness' ? 'active' : ''}`} style={POSITIONS.witness}>
          <Avatar role="witness" size={120} />
          <div className="seat-label">WITNESS</div>
        </div>
        <div className={`seat prosecution ${currentRole === 'prosecution' ? 'active' : ''}`} style={POSITIONS.prosecution}>
          <Avatar role="prosecution" size={120} />
          <div className="seat-label">PROSECUTION</div>
        </div>
        <div className={`seat defense ${currentRole === 'defense' ? 'active' : ''}`} style={POSITIONS.defense}>
          <Avatar role="defense" size={120} />
          <div className="seat-label">DEFENSE</div>
        </div>
        <div className={`seat intake ${currentRole === 'intake' ? 'active' : ''}`} style={POSITIONS.intake}>
          <Avatar role="intake" size={90} />
          <div className="seat-label">CLERK</div>
        </div>

        {/* narration bar at the very top of the room, no overlap */}
        {narration && <div className="narration-bar">🎙️ {narration}</div>}
      </div>

      {/* Current speaker's message — BELOW the room, clean panel, never overlaps */}
      {currentText && (
        <div className="current-panel">
          <div className="current-who">
            <Avatar role={currentRole} size={26} />
            <b style={{ color: (CHARACTERS[currentRole] || {}).color }}>
              {(CHARACTERS[currentRole] || {}).name}
            </b>
          </div>
          <div className="current-text">{currentText}</div>
        </div>
      )}

      {/* Ask controls */}
      <div className="stage-ask">
        <button onClick={() => onAsk && onAsk(['judge', currentRole === 'judge' ? 'witness' : currentRole])}>
          ❓ Judge questions {currentRole === 'judge' ? 'the witness' : (CHARACTERS[currentRole] || {}).name}
        </button>
      </div>
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