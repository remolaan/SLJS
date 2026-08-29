import React from 'react'

function verdictStyle(v) {
  if (v === 'guilty' || v === 'liable') return { cls: 'guilty', label: 'GUILTY / LIABLE' }
  return { cls: 'notguilty', label: 'NOT GUILTY' }
}

export default function JudgmentCard({ judgment, sources = [], checks = [] }) {
  if (!judgment) return null
  const vs = verdictStyle(judgment.verdict)
  const statutes = sources.filter((s) => s.source === 'statute' || s.source === 'constitution')
  const precedents = sources.filter((s) => s.source === 'precedent')
  const checked = checks.length > 0
  const supported = checks.filter((c) => c.supported)
  const unsupported = checks.filter((c) => !c.supported)

  return (
    <div className="judgment">
      <h2>📜 Judgment of the Court</h2>

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

      <div className="judgment-grid">
        <div className="j-col">
          <h3>Facts Found</h3>
          <p>{judgment.facts_found || '(none recorded)'}</p>

          <h3>Legal Reasoning</h3>
          <p>{judgment.legal_reasoning}</p>

          <h3>Citations</h3>
          {judgment.citations?.length ? (
            <ul className="cites">
              {judgment.citations.map((c, i) => {
                const check = checks.find((ch) => ch.citation === c)
                return (
                  <li key={i}>
                    <span className={`cite-badge ${check ? (check.supported ? 'sup' : 'unsup') : 'unk'}`}>
                      {check ? (check.supported ? '✓ supported' : '⚠ unverified') : '·'}
                    </span>
                    {c}
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="muted">No citations.</p>
          )}

          {judgment.sentence && (
            <>
              <h3>Sentence</h3>
              <div className="sentence">
                {judgment.sentence.custodial
                  ? `Custodial: ${judgment.sentence.term_years ?? 0}y ${judgment.sentence.term_months ?? 0}m`
                  : 'Non-custodial'}
                {judgment.sentence.fine_lkr != null && ` · Fine: LKR ${judgment.sentence.fine_lkr.toLocaleString()}`}
                {judgment.sentence.conditions?.length > 0 && ` · Conditions: ${judgment.sentence.conditions.join(', ')}`}
                {judgment.sentence.note && <div className="muted">{judgment.sentence.note}</div>}
              </div>
            </>
          )}
          {judgment.release && <div className="release-note">Accused ordered released.</div>}
        </div>

        <div className="j-col sources">
          <h3>📚 Why this decision — supporting sources</h3>
          <p className="muted small">
            The law below was retrieved (RAG) from the corpus and used to ground the reasoning.
          </p>

          {statutes.length > 0 && (
            <>
              <h4>Statute / Constitution</h4>
              {statutes.map((s, i) => (
                <details key={i} className="source">
                  <summary>{s.text.split('\n')[0] || 'Statute'}</summary>
                  <pre>{s.text}</pre>
                </details>
              ))}
            </>
          )}

          {precedents.length > 0 && (
            <>
              <h4>Similar Cases (precedent)</h4>
              {precedents.map((s, i) => (
                <details key={i} className="source precedent">
                  <summary>{s.text.split('\n')[0] || 'Precedent'}</summary>
                  <pre>{s.text}</pre>
                </details>
              ))}
            </>
          )}

          {checked && (
            <div className="hallucination">
              <h4>🔍 Citation verification (hallucination check)</h4>
              <p className="small">
                {supported.length}/{checks.length} citations verified against retrieved law.
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
