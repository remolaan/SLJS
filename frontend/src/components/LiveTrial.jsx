import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import Avatar, { CHARACTERS } from './Avatar.jsx'
import SpotlightBar from './SpotlightBar.jsx'
import Courtroom3D from './Courtroom3D.jsx'

const CHAT_ROLES = ['judge', 'prosecution', 'defense', 'witness', 'intake']

// Persist the live trial so it survives tab switches and page reloads.
const STORE_KEY = 'ai_judge_trial_v1'
function loadSaved() {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    if (!raw) return null
    const obj = JSON.parse(raw)
    if (obj?.snap && obj?.trialId) return obj
  } catch { /* ignore */ }
  return null
}
function saveTrial(trialId, snap) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify({ trialId, snap })) } catch {}
}
function clearTrial() {
  try { localStorage.removeItem(STORE_KEY) } catch {}
}

export default function LiveTrial({ seeds, onJudgment }) {
  const saved = loadSaved()
  const [seedKey, setSeedKey] = useState(seeds[0].key)
  const [snap, setSnap] = useState(saved?.snap || null)
  const [trialId, setTrialId] = useState(saved?.trialId || null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [autoplay, setAutoplay] = useState(false)
  const [interrupt, setInterrupt] = useState(false)
  const [askOpen, setAskOpen] = useState(false)
  const [questioner, setQuestioner] = useState('judge')
  const [addressee, setAddressee] = useState('witness')
  const [question, setQuestion] = useState('')
  // Questions the person has sent, rendered as their own outgoing chat bubbles
  // so it feels like they're a participant inside the hearing, not a spectator.
  const [myQuestions, setMyQuestions] = useState({}) // keyed by transcript length at time of send
  const [muted, setMuted] = useState(false)
  const feedRef = useRef(null)
  const judgmentSentRef = useRef(false)
  const pausedRef = useRef(false)
  const autoplayRef = useRef(false)
  // keep autoplayRef in sync
  useEffect(() => { autoplayRef.current = autoplay }, [autoplay])

  // Text-to-speech: read each new transcript turn aloud (browser speechSynthesis).
  const spokeRef = useRef(0)
  useEffect(() => {
    if (muted || typeof window === 'undefined' || !('speechSynthesis' in window)) return
    const tr = snap?.transcript || []
    if (tr.length > spokeRef.current) {
      const turn = tr[tr.length - 1]
      spokeRef.current = tr.length
      // skip intake (long notes) unless it's short
      const text = String(turn.content || '')
      if (text && text.length < 1400) {
        try {
          window.speechSynthesis.cancel()
          const u = new SpeechSynthesisUtterance(text.replace(/\[/g, '').replace(/\]/g, ''))
          u.rate = 1.05
          u.pitch = 1
          window.speechSynthesis.speak(u)
        } catch { /* ignore */ }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snap?.transcript?.length, muted])

  // Persist snap + trialId whenever they change.
  useEffect(() => {
    if (snap && trialId) saveTrial(trialId, snap)
  }, [snap, trialId])

  const startCase = async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch(`/api/seed-case/${seedKey}`)
      if (!res.ok) throw new Error('seed not found')
      const caseInput = await res.json()
      const s = await api.startTrial(caseInput)
      setSnap(s); setTrialId(s.trial_id); setAutoplay(true)
      judgmentSentRef.current = false
      setMyQuestions({})
      clearTrial(); saveTrial(s.trial_id, s)
    } catch (e) { setError(String(e.message || e)) }
    finally { setLoading(false) }
  }

  const doStep = async () => {
    if (!trialId || busy || interrupt) return
    setBusy(true)
    pausedRef.current = false
    try {
      const s = await api.trialStep(trialId)
      // If the user paused while this step was in-flight, discard the result
      // so the chat visibly stops.
      if (pausedRef.current || !autoplayRef.current) return
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
    const askedText = question.trim()
    setBusy(true); setAskOpen(false)
    // Drop the person's own question into the feed immediately as an
    // outgoing (right-aligned) bubble, before the response even comes back.
    setMyQuestions((prev) => ({
      ...prev,
      [(snap?.transcript?.length || 0)]: { questioner, addressee, text: askedText },
    }))
    try {
      const s = await api.trialAsk(trialId, questioner, addressee, askedText)
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

  const stop = () => { pausedRef.current = true; setAutoplay(false); setInterrupt(true) }
  const start = () => { pausedRef.current = false; setInterrupt(false); setAutoplay(true); if (snap?.status !== 'complete') doStep() }
  const resetTrial = () => {
    clearTrial(); setSnap(null); setTrialId(null); setAutoplay(false); setInterrupt(false); setMyQuestions({})
  }

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight
  }, [snap?.transcript?.length, busy])

  const transcript = snap?.transcript || []

  return (
    <div className="court-app">
      {/* LEFT 1/3: interactive chat (you are a participant) */}
      <div className="chat-col court-chat">
      {/* Header: case + framing + case picker */}
      <div className="chat-header">
        <div className="chat-title">
          <h2>{snap?.case?.title || 'Choose a case to begin'}</h2>
          {snap && <span className="you-tag">You are the accused — awaiting judgment</span>}
        </div>
        <div className="chat-header-actions">
          <select className="case-pick" value={seedKey} onChange={(e) => setSeedKey(e.target.value)} disabled={loading}>
            {seeds.map((s) => <option key={s.key} value={s.key}>{s.title}</option>)}
          </select>
          <button className="mini-btn" onClick={startCase} disabled={loading}>{loading ? '…' : (snap ? 'New Trial' : '⚖️ Begin')}</button>
          {snap && <button className="mini-btn ghost" onClick={resetTrial}>Reset</button>}
          <button
            className={`mini-btn ${muted ? 'ghost' : ''}`}
            onClick={() => setMuted((m) => !m)}
            title={muted ? 'Unmute voice' : 'Mute voice'}
          >
            {muted ? '🔇' : '🔊'}
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {!snap ? (
        <div className="chat-empty">
          <div className="chat-empty-icon">⚖️</div>
          <p>Pick a case above and press <b>Begin</b>.</p>
          <p className="muted small">You'll sit in the hearing as it happens — prosecution, defense, witnesses, and finally the judge, all live in this chat.</p>
        </div>
      ) : (
        <>
          <SpotlightBar snapshot={snap} busy={busy} />

          <div className="chat-feed" ref={feedRef}>
            {transcript.map((turn, i) => (
              <React.Fragment key={i}>
                <ChatBubble turn={turn} />
                {myQuestions[i + 1] && <MyBubble q={myQuestions[i + 1]} />}
              </React.Fragment>
            ))}
            {busy && <TypingBubble role={snap?.current_node} />}
            {interrupt && <div className="paused-note">⏸ Hearing paused — press ▶ to continue</div>}
            {snap?.status === 'complete' && snap?.judgment && (
              <VerdictBubble judgment={snap.judgment} onView={() => onJudgment && onJudgment(snap.judgment, snap.retrieved_context, snap.citation_checks)} />
            )}
          </div>

          {/* Composer */}
          <div className="composer">
            <div className="transport">
              <button title="Pause" className="t-btn pause" onClick={() => { pausedRef.current = true; setAutoplay(false) }} disabled={!autoplay}>⏸ Pause</button>
              <button title="Continue" className="t-btn start" onClick={start} disabled={!trialId || snap?.status === 'complete' || busy}>▶ Continue</button>
              <button
                className="t-btn autoplay"
                onClick={() => (autoplay ? stop() : start())}
                disabled={!trialId || snap?.status === 'complete'}
              >
                {autoplay ? '⏹ Stop autoplay' : '⏵⏵ Autoplay'}
              </button>
            </div>
            <button className="ask-btn" onClick={() => setAskOpen((o) => !o)}>
              🙋 Speak up / Ask a question
            </button>
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
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && doAsk()}
                  placeholder='e.g. "Where were you when it began?"'
                  autoFocus
                />
                <button onClick={doAsk} disabled={!question.trim()}>Send</button>
              </div>
            )}
          </div>
        </>
      )}
      </div>{/* end chat-col */}

      {/* RIGHT 2/3: live courtroom scene image */}
      <div className="scene-col court-scene">
        {!snap ? (
          <div className="scene-empty">
            <button className="primary" onClick={startCase} disabled={loading}>
              {loading ? '…' : '⚖️ Open the Court'}
            </button>
          </div>
        ) : (
          <Courtroom3D snapshot={snap} />
        )}
      </div>
    </div>
  )
}

function ChatBubble({ turn }) {
  const meta = CHARACTERS[turn.role] || CHARACTERS.intake
  return (
    <div className={`chat-bubble ${turn.role}`}>
      <div className="chat-bubble-av">
        <Avatar role={turn.role} size={40} />
      </div>
      <div className="chat-bubble-main">
        <div className="chat-bubble-meta">
          <b style={{ color: meta.color }}>{turn.speaker || meta.name}</b>
          {turn.label && <span className="chat-label">{turn.label}</span>}
        </div>
        <div className="chat-bubble-body">
          <div className="chat-bubble-text">{renderText(turn.content)}</div>
        </div>
      </div>
    </div>
  )
}

// The person's own question, rendered right-aligned like an outgoing message
// in a normal group chat — this is what makes it feel like you're inside it.
function MyBubble({ q }) {
  return (
    <div className="chat-bubble me">
      <div className="chat-bubble-main">
        <div className="chat-bubble-meta me-meta">
          <span className="chat-label">{CHARACTERS[q.questioner]?.name || q.questioner} → {CHARACTERS[q.addressee]?.name || q.addressee}</span>
        </div>
        <div className="chat-bubble-body me-body">
          <div className="chat-bubble-text">{q.text}</div>
        </div>
      </div>
      <div className="chat-bubble-av">
        <div className="avatar avatar-fallback me-avatar">You</div>
      </div>
    </div>
  )
}

function TypingBubble({ role }) {
  const r = CHAT_ROLES.includes(role) ? role : 'judge'
  const meta = CHARACTERS[r]
  return (
    <div className={`chat-bubble ${r}`}>
      <div className="chat-bubble-av"><Avatar role={r} size={40} /></div>
      <div className="chat-bubble-main">
        <div className="chat-bubble-meta"><b style={{ color: meta.color }}>{meta.name}</b></div>
        <div className="chat-bubble-body">
          <span className="typing" />
        </div>
      </div>
    </div>
  )
}

// A dedicated, visually distinct message that lands right in the chat feed
// the moment the judge delivers a verdict — instead of only in a separate tab.
function VerdictBubble({ judgment, onView }) {
  const v = judgment.verdict
  const cls = v === 'guilty' || v === 'liable' ? 'guilty' : (v === 'not_guilty' || v === 'not_liable' ? 'notguilty' : 'insufficient')
  const label = cls === 'guilty' ? 'GUILTY' : cls === 'notguilty' ? 'NOT GUILTY' : 'INSUFFICIENT EVIDENCE'
  return (
    <div className="verdict-bubble-wrap">
      <div className={`verdict-bubble ${cls}`}>
        <div className="verdict-bubble-label">⚖️ The Court has reached a decision</div>
        <div className="verdict-bubble-word">{label}</div>
        <button className="verdict-bubble-btn" onClick={onView}>View full judgment →</button>
      </div>
    </div>
  )
}

// Render simple markdown as clean text: turn **bold**, # headings, --- rules
// into plain readable text (no literal symbols shown to the user).
function renderText(raw) {
  if (!raw) return ''
  return String(raw)
    .replace(/\*\*(.+?)\*\*/g, (_, s) => `[${s}]`)
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^-{3,}\s*$/gm, '')
    .replace(/\*\s/g, '• ')
    .replace(/^#{1,6}\s*/gm, '')
}
