import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import Avatar, { CHARACTERS } from './Avatar.jsx'

// Positions of each participant in the courtroom (in % of stage).
const POSITIONS = {
  judge: { left: '50%', top: '8%', transform: 'translateX(-50%)' },
  witness: { left: '50%', top: '55%', transform: 'translateX(-50%)' },
  prosecution: { left: '22%', top: '52%', transform: 'translateX(-50%)' },
  defense: { left: '78%', top: '52%', transform: 'translateX(-50%)' },
  intake: { left: '10%', top: '12%', transform: 'translateX(-50%)' },
}

const SPEAKER_ROLES = ['judge', 'prosecution', 'defense', 'witness', 'intake']

/**
 * Courtroom stage: big avatars positioned like a real court. The active
 * speaker is highlighted and "speaks". A narration bar shows the current
 * moment, and clicking a seated person lets the judge question them.
 */
export default function CourtroomStage({ snapshot, onAsk }) {
  const stage = snapshot?.stage_label || 'Case Intake'
  const currentRole = snapshot?.current_node === 'judge' ? 'judge' : lastSpeaker(snapshot)
  const [narration, setNarration] = useState('')
  const [currentText, setCurrentText] = useState('')

  // Current speaker's latest message.
  useEffect(() => {
    const tr = snapshot?.transcript || []
    if (!tr.length) return
    setCurrentText(tr[tr.length - 1].content)
  }, [snapshot?.transcript?.length])

  // MiniMax-M3 narration.
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
      <div className="stage-head">
        <h2>{snapshot?.case?.title || 'Courtroom'}</h2>
        <span className="pill stage-pill">{stage}</span>
        <span className={`pill ${snapshot?.status === 'complete' ? 'ok' : ''}`}>{snapshot?.status || 'idle'}</span>
      </div>

      <div className="courtroom-stage">
        {/* bench / floor */}
        <div className="bench" />
        <div className="floor" />

        {/* judge bench (big avatar) */}
        <div className={`seat judge ${currentRole === 'judge' ? 'active' : ''}`} style={POSITIONS.judge}>
          <Avatar role="judge" size={150} />
          <div className="seat-label">THE JUDGE</div>
        </div>

        {/* witness stand */}
        <div className={`seat witness ${currentRole === 'witness' ? 'active' : ''}`} style={POSITIONS.witness}>
          <Avatar role="witness" size={110} />
          <div className="seat-label">WITNESS STAND</div>
        </div>

        {/* prosecution table */}
        <div className={`seat prosecution ${currentRole === 'prosecution' ? 'active' : ''}`} style={POSITIONS.prosecution}>
          <Avatar role="prosecution" size={110} />
          <div className="seat-label">PROSECUTION</div>
        </div>

        {/* defense table */}
        <div className={`seat defense ${currentRole === 'defense' ? 'active' : ''}`} style={POSITIONS.defense}>
          <Avatar role="defense" size={110} />
          <div className="seat-label">DEFENSE</div>
        </div>

        {/* clerk */}
        <div className={`seat intake ${currentRole === 'intake' ? 'active' : ''}`} style={POSITIONS.intake}>
          <Avatar role="intake" size={90} />
          <div className="seat-label">CLERK</div>
        </div>

        {/* who is speaking */}
        {currentText && (
          <div className="speaking-bubble">
            <div className="speaking-who">
              <b style={{ color: (CHARACTERS[currentRole] || {}).color }}>
                {(CHARACTERS[currentRole] || {}).name}
              </b>
            </div>
            <div className="speaking-text">{currentText.slice(0, 200)}</div>
          </div>
        )}

        {narration && <div className="narration-bar">🎙️ {narration}</div>}
      </div>

      {/* quick ask controls on the stage */}
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