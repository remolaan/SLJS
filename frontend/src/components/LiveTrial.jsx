import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import Avatar, { CHARACTERS } from './Avatar.jsx'
import CourtroomStage from './CourtroomStage.jsx'

const CHAT_ROLES = ['judge', 'prosecution', 'defense', 'witness', 'intake']

export default function LiveTrial({ seeds, onJudgment }) {
  const [seedKey, setSeedKey] = useState(seeds[0].key)
  const [snap, setSnap] = useState(null)
  const [trialId, setTrialId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [autoplay, setAutoplay] = useState(false)
  const [interrupt, setInterrupt] = useState(false)
  const [askOpen, setAskOpen] = useState(false)
  const [questioner, setQuestioner] = useState('judge')
  const [addressee, setAddressee] = useState('witness')
  const [question, setQuestion] = useState('')
  const feedRef = useRef(null)
  const judgmentSentRef = useRef(false)

  const startCase = async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch(`/api/seed-case/${seedKey}`)
      if (!res.ok) throw new Error('seed not found')
      const caseInput = await res.json()
      const s = await api.startTrial(caseInput)
      setSnap(s); setTrialId(s.trial_id); setAutoplay(true)
      judgmentSentRef.current = false
    } catch (e) { setError(String(e.message || e)) }
    finally { setLoading(false) }
  }

  const doStep = async () => {
    if (!trialId || busy || interrupt) return
    setBusy(true)
    try {
      const s = await api.trialStep(trialId)
      setSnap(s)
      if (s.status === 'complete') {
        setAutoplay(false)
        if (s.judgment && !judgmentSentRef.current && onJudgment) {
          judgmentSentRef.current = true
          onJudgment(s.judgment, s.retrieved_context, s.citation_checks)
        }
      }
    } catch (e) { setError(String(e.message || e)) }
    finally { setBusy(false) }
  }

  const doAsk = async () => {
    if (!trialId || !question.trim()) return
    setBusy(true); setAskOpen(false)
    try {
      const s = await api.trialAsk(trialId, questioner, addressee, question.trim())
      setSnap(s)
    } catch (e) { setError(String(e.message || e)) }
    finally { setBusy(false); setQuestion('') }
  }

  useEffect(() => {
    if (!autoplay || !trialId || snap?.status === 'complete' || interrupt || busy) return
    const t = setTimeout(() => doStep(), 1600)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoplay, snap, trialId, interrupt, busy])

  const stop = () => { setAutoplay(false); setInterrupt(true) }
  const start = () => { setInterrupt(false); setAutoplay(true); if (snap?.status !== 'complete') doStep() }

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight
  }, [snap?.transcript?.length])

  const transcript = snap?.transcript || []

  return (
    <div className="court-app">
      {/* left: courtroom stage (big avatars positioned in the room) */}
      <div className="stage-col">
        {!snap ? (
          <div className="scene-empty">
            <button className="primary" onClick={startCase} disabled={loading}>
              {loading ? '…' : '⚖️ Open the Court'}
            </button>
          </div>
        ) : (
          <CourtroomStage snapshot={snap} onAsk={(a) => { setQuestioner(a[0]); setAddressee(a[1]); setAskOpen(true) }} />
        )}
      </div>

      {/* right: chat */}
      <div className="chat-col">
        <div className="chat-header">
          <div className="chat-title">
            <h2>{snap?.case?.title || 'Courtroom'}</h2>
            <span className={`pill ${snap?.status === 'complete' ? 'ok' : ''}`}>{snap?.status || 'idle'}</span>
            {snap?.stage_label && <span className="pill stage-pill">{snap.stage_label}</span>}
          </div>
          <div className="transport">
            <button title="Stop" className="t-btn stop" onClick={stop} disabled={!trialId}>⏹</button>
            <button title="Start / Continue" className="t-btn start" onClick={start} disabled={!trialId || snap?.status === 'complete' || busy}>▶</button>
            <button title="Pause" className="t-btn pause" onClick={() => setAutoplay(false)} disabled={!autoplay}>⏸</button>
          </div>
        </div>

        <div className="newcase">
          <select value={seedKey} onChange={(e) => setSeedKey(e.target.value)} disabled={loading}>
            {seeds.map((s) => <option key={s.key} value={s.key}>{s.title}</option>)}
          </select>
          <button className="primary" onClick={startCase} disabled={loading}>
            {loading ? '…' : 'New Trial'}
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="chat-feed" ref={feedRef}>
          {transcript.map((turn, i) => (
            <ChatBubble key={i} turn={turn} />
          ))}
          {busy && <div className="typing">… speaking</div>}
          {interrupt && <div className="paused-note">⏸ Trial paused</div>}
        </div>

        <div className="chat-input">
          <button className="ask-btn" onClick={() => setAskOpen((o) => !o)}>❓ Interrupt / Ask</button>
        </div>
        {askOpen && (
          <div className="ask-box">
            <div className="ask-row">
              <select value={questioner} onChange={(e) => setQuestioner(e.target.value)}>
                {CHAT_ROLES.map((r) => <option key={r} value={r}>{CHARACTERS[r].name}</option>)}
              </select>
              <span>asks</span>
              <select value={addressee} onChange={(e) => setAddressee(e.target.value)}>
                {CHAT_ROLES.map((r) => <option key={r} value={r}>{CHARACTERS[r].name}</option>)}
              </select>
            </div>
            <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder='e.g. "Where were you when it began?"' />
            <button onClick={doAsk} disabled={!question.trim()}>Send</button>
          </div>
        )}

        {snap?.status === 'complete' && snap?.judgment && (
          <button className="view-judgment" onClick={() => onJudgment && onJudgment(snap.judgment, snap.retrieved_context, snap.citation_checks)}>
            ⚖️ View the Judgment →
          </button>
        )}
      </div>
    </div>
  )
}

function ChatBubble({ turn }) {
  const meta = CHARACTERS[turn.role] || CHARACTERS.intake
  const isJudge = turn.role === 'judge'
  const isWitness = turn.role === 'witness'
  return (
    <div className={`chat-bubble ${turn.role}`}>
      <Avatar role={turn.role} size={38} />
      <div className="chat-bubble-main">
        <div className="chat-bubble-meta">
          <b style={{ color: meta.color }}>{turn.speaker || meta.name}</b>
          {turn.label && <span className="chat-label">{turn.label}</span>}
        </div>
        <div className={`chat-bubble-body ${isJudge ? 'judge' : ''} ${isWitness ? 'witness' : ''}`}>
          {turn.content}
        </div>
      </div>
    </div>
  )
}