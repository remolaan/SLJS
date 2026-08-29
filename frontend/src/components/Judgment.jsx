import React from 'react'

function verdictStyle(v) {
  if (v === 'guilty' || v === 'liable') return { cls: 'guilty', label: 'GUILTY / LIABLE' }
  return { cls: 'notguilty', label: 'NOT GUILTY' }
}

export default function Judgment({ judgment, sources = [], checks = [] }) {
  if (!judgment) {
    return (
      <div className="empty panel">
        <h2>No judgment yet.</h2>
        <p>Run a trial in the Courtroom tab; once the judge delivers a verdict it will appear here.</p>
      </div>
    )
  }

  const vs = verdictStyle(judgment.verdict)
  const statutes = sources.filter((s) => s.source === 'statute' || s.source === 'constitution')
  const precedents = sources.filter((s) => s.source === 'precedent')
  const supported = checks.filter((c) => c.supported)
  const unsupported = checks.filter((c) => !c.supported)

  return (
    <div className="judgment-page">
      <div className="verdict-hero">
        <div>
          <h1>Judgment of the Court</h1>
        </div>
        <div className={`verdict-banner ${vs.cls}`}>
          <div className="verdict-word">{vs.label}</div>
          <div className="verdict-confidence">
            Confidence: {Math.round(judgment.verdict_confidence * 100)}%
            {judgment.evidentiary_directive === 'produce_more' && (
              <span className="ie-note"> — record insufficient; court directs further evidence be produced</span>
            )}
            {judgment.evidentiary_directive === 'acquit' && (
              <span className="ie-note"> — record insufficient; accused acquitted</span>
            )}
          </div>
        </div>
      </div>

      {judgment.bench_verdict && (
        <div className="bench-box">
          <h3>⚖️ Bench deliberation ({Object.keys(judgment.bench_verdict.per_judge || {}).length}-judge bench)</h3>
          <div className="bench-judges">
            {Object.entries(judgment.bench_verdict.per_judge || {}).map(([id, v]) => (
              <span key={id} className={`bench-judge-chip ${(judgment.bench_verdict.dissents || []).includes(id) ? 'dissent' : ''}`}>
                {id}: <b>{v}</b>
                {(judgment.bench_verdict.dissents || []).includes(id) ? ' (dissent)' : ''}
              </span>
            ))}
          </div>
          <div className="bench-majority">
            Majority: <b>{judgment.bench_verdict.majority_verdict}</b>
          </div>
          {judgment.bench_verdict.dissent_summary && (
            <div className="bench-dissent">Dissent: {judgment.bench_verdict.dissent_summary}</div>
          )}
        </div>
      )}

      <div className="judgment-grid">
        {/* Left: the written judgment — ALL sections shown expanded */}
        <div className="j-col">
          <h3>Facts Found</h3>
          <p>{judgment.facts_found || '(none recorded)'}</p>

          <h3>Legal Reasoning</h3>
          <p>{judgment.legal_reasoning}</p>

          <h3>Sentence</h3>
          <p>{sentenceText(judgment.sentence) || 'None'}</p>

          {judgment.release && <div className="release-note">Accused ordered released.</div>}

          <h3>Citations ({judgment.citations?.length || 0})</h3>
          {judgment.citations?.length ? (
            <ul className="cites">
              {judgment.citations.map((c, i) => {
                const chk = checks.find((x) => x.citation === c)
                return (
                  <li key={i}>
                    <span className={`cite-badge ${chk ? (chk.supported ? 'sup' : 'unsup') : 'unk'}`}>
                      {chk ? (chk.supported ? '✓ verified' : '⚠ unverified') : '·'}
                    </span>
                    {c}
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="muted">No citations.</p>
          )}
        </div>

        {/* Right: supporting sources to convince — ALL shown expanded */}
        <div className="j-col sources">
          <h3>📚 Why this decision</h3>
          <p className="muted small">Retrieved (RAG) law and precedent that grounded the reasoning.</p>

          {statutes.length > 0 && (
            <>
              <h4>Statute / Constitution</h4>
              {statutes.map((s, i) => (
                <div key={i} className="source-open">
                  <div className="source-open-title">{s.text.split('\n')[0]}</div>
                  <pre>{s.text}</pre>
                </div>
              ))}
            </>
          )}

          {precedents.length > 0 && (
            <>
              <h4>Similar Cases</h4>
              {precedents.map((s, i) => (
                <div key={i} className="source-open precedent">
                  <div className="source-open-title">{s.text.split('\n')[0]}</div>
                  <pre>{s.text}</pre>
                </div>
              ))}
            </>
          )}

          {checks.length > 0 && (
            <div className="hallucination">
              <h4>🔍 Citation verification</h4>
              <p className="small">
                {supported.length}/{checks.length} verified against retrieved law.
                {unsupported.length > 0 && (
                  <span className="warn"> {unsupported.length} unverified — possible hallucination.</span>
                )}
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="disclaimer">
        ⚠️ {judgment.methodology_warning} Not legal advice; do not rely on for real decisions.
      </div>
    </div>
  )
}

function sentenceText(sentence) {
  if (!sentence) return ''
  const parts = []
  if (sentence.custodial) {
    parts.push(`Custodial: ${sentence.term_years ?? 0}y ${sentence.term_months ?? 0}m`)
  } else {
    parts.push('Non-custodial')
  }
  if (sentence.fine_lkr != null) parts.push(`Fine: LKR ${sentence.fine_lkr.toLocaleString()}`)
  if (sentence.conditions?.length) parts.push(`Conditions: ${sentence.conditions.join(', ')}`)
  if (sentence.note) parts.push(sentence.note)
  return parts.join('\n')
}