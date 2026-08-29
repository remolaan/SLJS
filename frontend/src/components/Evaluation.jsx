import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Evaluation() {
  const [dataset, setDataset] = useState(null)
  const [report, setReport] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getDataset().then(setDataset).catch(() => {})
  }, [])

  const runAll = async () => {
    setRunning(true); setError('')
    try {
      const r = await api.runDatasetEval()
      setReport(r)
    } catch (e) { setError(String(e.message || e)) }
    finally { setRunning(false) }
  }

  const runOne = async (hc) => {
    setRunning(true); setError('')
    try {
      const r = await api.runSingleEval(hc)
      // merge into a lightweight report view
      setReport({
        n_cases: 1, correct: r.correct ? 1 : 0,
        accuracy: r.correct ? 1 : 0,
        mean_confidence: r.verdict_confidence,
        mean_citation_accuracy: r.citation_accuracy,
        hallucination_rate: r.total_citations ? r.hallucinated_citations.length / r.total_citations : 0,
        results: [r], confusion: {},
        _single: true,
      })
    } catch (e) { setError(String(e.message || e)) }
    finally { setRunning(false) }
  }

  const confMatrix = report?.confusion || {}

  return (
    <div className="eval">
      <div className="panel">
        <div className="eval-header">
          <div>
            <h2>Judge Accuracy Evaluation</h2>
            <p className="muted">
              Feed historical (anonymized) case data — the system returns a verdict
              grounded in law — and compare it against the real outcome for an accuracy score.
            </p>
          </div>
          <button className="primary" onClick={runAll} disabled={running}>
            {running ? '⏳ Evaluating…' : '📊 Run full dataset'}
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        {dataset && (
          <table className="cases">
            <thead>
              <tr><th>Case</th><th>Ground-truth verdict</th><th>Notes</th><th></th></tr>
            </thead>
            <tbody>
              {dataset.cases.map((c, i) => (
                <tr key={i}>
                  <td>{c.case.title}</td>
                  <td><span className={`verdict-chip ${c.ground_truth_verdict}`}>{c.ground_truth_verdict}</span></td>
                  <td className="muted small">{c.notes}</td>
                  <td>
                    <button className="small-btn" disabled={running} onClick={() => runOne(c)}>
                      Run
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {report && (
        <div className="panel report">
          <h2>Results</h2>
          <div className="metric-grid">
            <Metric label="Accuracy" value={`${(report.accuracy * 100).toFixed(1)}%`} sub={`${report.correct}/${report.n_cases} correct`} />
            <Metric label="Mean confidence" value={(report.mean_confidence * 100).toFixed(0) + '%'} />
            <Metric label="Citation accuracy" value={(report.mean_citation_accuracy * 100).toFixed(1) + '%'} />
            <Metric label="Hallucination rate" value={(report.hallucination_rate * 100).toFixed(1) + '%'} sub="unverified citations" />
          </div>

          {Object.keys(confMatrix).length > 0 && (
            <div className="confusion">
              <h3>Confusion matrix (ground truth → predicted)</h3>
              <table>
                <thead>
                  <tr>
                    <th>Truth ↓ / Pred →</th>
                    {Object.keys(confMatrix).map((pred) => <th key={pred}>{pred}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(confMatrix).map(([truth, row]) => (
                    <tr key={truth}>
                      <td>{truth}</td>
                      {Object.keys(confMatrix).map((pred) => (
                        <td key={pred}>{row[pred] || 0}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3>Per-case breakdown</h3>
          <table className="cases">
            <thead>
              <tr><th>Case</th><th>Predicted</th><th>Ground truth</th><th>Match</th><th>Conf.</th><th>Hallucinated cites</th></tr>
            </thead>
            <tbody>
              {report.results?.map((r, i) => (
                <tr key={i}>
                  <td>{r.case_title}</td>
                  <td><span className={`verdict-chip ${r.predicted_verdict}`}>{r.predicted_verdict}</span></td>
                  <td><span className={`verdict-chip ${r.ground_truth_verdict}`}>{r.ground_truth_verdict}</span></td>
                  <td>{r.correct ? '✅' : '❌'}</td>
                  <td>{(r.verdict_confidence * 100).toFixed(0)}%</td>
                  <td>{r.hallucinated_citations?.length || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, sub }) {
  return (
    <div className="metric">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  )
}
