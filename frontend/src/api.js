const BASE = '/api'

async function j(res) {
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`Request failed ${res.status}: ${body}`)
  }
  return res.json()
}

export const api = {
  health: () => fetch(`${BASE}/health`).then(j),

  // one-shot trial
  runCase: (caseInput, includeWitness = true) =>
    fetch(`${BASE}/cases/run?include_witness=${includeWitness}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(caseInput),
    }).then(j),

  // stepped demo trial
  startTrial: (caseInput, includeWitness = true) =>
    fetch(`${BASE}/trials?include_witness=${includeWitness}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(caseInput),
    }).then(j),

  trialState: (id) => fetch(`${BASE}/trials/${id}`).then(j),
  trialStep: (id) => fetch(`${BASE}/trials/${id}/step`, { method: 'POST' }).then(j),
  trialScene: (id) => fetch(`${BASE}/trials/${id}/scene`).then(j),

  trialAsk: (id, questioner, addressee, question) =>
    fetch(`${BASE}/trials/${id}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ questioner, addressee, question }),
    }).then(j),

  // evaluation
  getDataset: () => fetch(`${BASE}/evaluation/dataset`).then(j),
  runSingleEval: (historical, includeWitness = true) =>
    fetch(`${BASE}/evaluation/run-single?include_witness=${includeWitness}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(historical),
    }).then(j),
  runDatasetEval: (includeWitness = true) =>
    fetch(`${BASE}/evaluation/run-dataset?include_witness=${includeWitness}`, {
      method: 'POST',
    }).then(j),

  citationCheck: () => fetch(`${BASE}/citation-check`).then(j),
  vectorStats: () => fetch(`${BASE}/vectorstore/stats`).then(j),
  runs: (kind) => fetch(`${BASE}/runs${kind ? `?kind=${kind}` : ''}`).then(j),

  // image generation
  generateImage: (prompt) =>
    fetch(`${BASE}/images/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    }).then(j),

  // pre-generated static images (no API call, always loads)
  imageManifest: () => fetch(`${BASE}/images/manifest`).then(j),
}
