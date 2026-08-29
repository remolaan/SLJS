import React, { useEffect, useState } from 'react'
import { api } from './api.js'
import LiveTrial from './components/LiveTrial.jsx'
import Judgment from './components/Judgment.jsx'
import Evaluation from './components/Evaluation.jsx'

const SEED_CASES = [
  {
    key: 'market_altercation',
    title: 'The Market Altercation',
    description: 'Grievous hurt in a sudden quarrel (Penal Code s.324)',
  },
  {
    key: 'shophouse_theft',
    title: 'The Shophouse Theft',
    description: 'Theft & house-trespass by night (s.367, s.431)',
  },
]

// LiveTrial exposes a callback to push the latest judgment up to App so the
// Judgment tab can render it once the trial completes.
export default function App() {
  const [tab, setTab] = useState('courtroom')
  const [health, setHealth] = useState(null)
  const [chunks, setChunks] = useState(null)
  const [judgment, setJudgment] = useState(null)
  const [sources, setSources] = useState([])
  const [checks, setChecks] = useState([])

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: 'down' }))
    api.vectorStats().then(setChunks).catch(() => {})
  }, [])

  const handleJudgment = (j, srcs, cks) => {
    setJudgment(j)
    setSources(srcs || [])
    setChecks(cks || [])
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="gavel">⚖️</span>
          <div>
            <h1>AI Judge</h1>
            <p>Courtroom Simulation for Sri Lanka — Research &amp; Education</p>
          </div>
        </div>
        <div className="topbar-right">
          <span className={`pill ${health?.status === 'ok' ? 'ok' : 'bad'}`}>
            API {health?.status}
          </span>
          <span className="pill">{chunks != null ? `${chunks.chunks} law chunks` : '…'}</span>
        </div>
      </header>

      <nav className="tabs">
        <button className={tab === 'courtroom' ? 'active' : ''} onClick={() => setTab('courtroom')}>
          🏛️ Courtroom
        </button>
        <button
          className={`judgment-tab ${tab === 'judgment' ? 'active' : ''}`}
          onClick={() => setTab('judgment')}
          disabled={!judgment}
        >
          ⚖️ Judgment {judgment && <span className="tab-dot">•</span>}
        </button>
        <button className={tab === 'eval' ? 'active' : ''} onClick={() => setTab('eval')}>
          📊 Evaluation
        </button>
      </nav>

      <main>
        {tab === 'courtroom' && (
          <LiveTrial seeds={SEED_CASES} onJudgment={handleJudgment} />
        )}
        {tab === 'judgment' && <Judgment judgment={judgment} sources={sources} checks={checks} />}
        {tab === 'eval' && <Evaluation />}
      </main>
    </div>
  )
}