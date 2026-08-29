import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import Avatar, { CHARACTERS } from './Avatar.jsx'

// Pre-generated scene key per stage (matches backend registry / pregen script).
const STAGE_SCENE = {
  'Case Intake': 'scene_case_intake',
  'Prosecution Opening': 'scene_prosecution_opening',
  'Defense Response': 'scene_defense_response',
  'Prosecution Evidence': 'scene_prosecution_evidence',
  'Witness Testimony': 'scene_witness_testimony',
  'Defense Evidence': 'scene_defense_evidence',
  'Prosecution Closing': 'scene_prosecution_closing',
  'Defense Closing': 'scene_defense_closing',
  'Law Retrieval (RAG)': 'scene_law_retrieval',
  Judgment: 'scene_judgment',
  Deliberation: 'scene_deliberation',
}

let manifestPromise = null
function getManifest() {
  if (!manifestPromise) {
    manifestPromise = api.imageManifest().then((r) => r.images || {}).catch(() => ({}))
  }
  return manifestPromise
}

/**
 * The large 2/3 scene panel. Shows the pre-generated scene image for the
 * current stage (loaded instantly from static cache), the active speaker,
 * a MiniMax-M3 narration caption, and reference cards.
 */
export default function SceneVisualizer({ snapshot, busy }) {
  const stage = snapshot?.stage_label || 'Case Intake'
  const speaker = snapshot?.current_node === 'judge' ? 'judge' : lastSpeaker(snapshot)
  const meta = CHARACTERS[speaker] || CHARACTERS.judge
  const [sceneSrc, setSceneSrc] = useState(null)
  const [narration, setNarration] = useState('')
  const [activeCard, setActiveCard] = useState(null)

  const sceneKey = STAGE_SCENE[stage] || 'scene_case_intake'

  // Load the pre-generated static scene image.
  useEffect(() => {
    let cancelled = false
    getManifest().then((urls) => {
      if (!cancelled) setSceneSrc(urls[sceneKey] || null)
    })
    return () => {
      cancelled = true
    }
  }, [sceneKey])

  // MiniMax-M3 narration for the current moment.
  useEffect(() => {
    if (!snapshot?.trial_id) return
    let cancelled = false
    api.trialScene(snapshot.trial_id).then((r) => {
      if (!cancelled) setNarration(r.caption)
    }).catch(() => {})
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot?.trial_id, snapshot?.current_node, snapshot?.transcript?.length])

  const cards = buildCards(snapshot)

  return (
    <div className="scene-panel">
      <div className="scene-stage">
        {sceneSrc ? (
          <img className="scene-img-big" src={sceneSrc} alt={stage} />
        ) : (
          <div className="scene-loading">🏛️ {stage}</div>
        )}

        <div className="scene-overlay">
          <Avatar role={speaker} size={88} />
          <div>
            <div className="scene-speaker">{meta.name}</div>
            <div className="scene-stage-label">{stage}</div>
            <div className="scene-talking">{busy ? '● speaking…' : ''}</div>
          </div>
        </div>

        {narration && <div className="scene-narration">🎙️ {narration}</div>}
      </div>

      <div className="scene-cards">
        {cards.map((c, i) => (
          <div key={i} className={`scene-card ${c.type}`} onClick={() => setActiveCard(activeCard === i ? null : i)}>
            <div className="scene-card-head">
              <span>{c.icon}</span> <b>{c.title}</b>
              <span className="scene-card-toggle">{activeCard === i ? '▲' : '▼'}</span>
            </div>
            {activeCard === i && <div className="scene-card-body">{c.body}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}

function lastSpeaker(snapshot) {
  const tr = snapshot?.transcript || []
  for (let i = tr.length - 1; i >= 0; i--) {
    if (['judge', 'prosecution', 'defense', 'witness', 'intake'].includes(tr[i].role)) return tr[i].role
  }
  return 'judge'
}

function buildCards(snapshot) {
  const cards = []
  const caseData = snapshot?.case
  const charges = caseData?.charges || []
  const evidence = caseData?.evidence || []
  const ctx = snapshot?.retrieved_context || []
  const checks = snapshot?.citation_checks || []

  if (charges.length) {
    cards.push({ icon: '⚖️', type: 'charges', title: 'Charges', body: charges.map((c) => `${c.description}${c.section ? ` (s.${c.section})` : ''}`).join('; ') })
  }
  if (evidence.length) {
    cards.push({ icon: '📦', type: 'evidence', title: 'Evidence', body: evidence.map((e) => `• ${e.description}${e.relevance ? ` — ${e.relevance}` : ''}`).join('\n') })
  }
  const statutes = ctx.filter((c) => c.source === 'statute' || c.source === 'constitution')
  if (statutes.length) {
    cards.push({ icon: '📕', type: 'law', title: 'Law / Books', body: statutes.map((s) => `• ${s.text.split('\n')[0]}`).join('\n') })
  }
  const precedents = ctx.filter((c) => c.source === 'precedent')
  if (precedents.length) {
    cards.push({ icon: '🗂️', type: 'cases', title: 'Similar Cases', body: precedents.map((s) => `• ${s.text.split('\n')[0]}`).join('\n') })
  }
  if (checks.length) {
    cards.push({ icon: '🔍', type: 'verify', title: 'Citation check', body: checks.map((c) => `${c.supported ? '✅' : '⚠️'} ${c.citation}`).join('\n') })
  }
  return cards
}