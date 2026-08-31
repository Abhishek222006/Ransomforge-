const BASE = 'http://127.0.0.1:8000'

async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`)
  return res.json()
}

export const api = {
  health:          ()       => apiFetch('/health'),
  recentEvents:    (limit = 25) => apiFetch(`/events/recent?limit=${limit}`),
  recentProcesses: ()       => apiFetch('/processes/recent'),
  quarantineStatus:()       => apiFetch('/quarantine/status'),
  honeypotAssets:  ()       => apiFetch('/assets/honeypots'),
  startFullScan:   ()       => apiFetch('/operations/full-scan',      { method: 'POST' }),
  isolateNetwork:  ()       => apiFetch('/operations/isolate-network', { method: 'POST' }),
  containHost:     (host)   => apiFetch(`/operations/contain-host?host=${encodeURIComponent(host)}`, { method: 'POST' }),
  demoEvent:       ()       => apiFetch('/demo/event',                { method: 'POST' }),
  listBackups:     ()       => apiFetch('/api/recovery/backups'),
  getRecoveryStats:()       => apiFetch('/api/recovery/stats'),
  getRecoveryLogs: ()       => apiFetch('/api/recovery/logs'),
  createBackup:    ()       => apiFetch('/api/recovery/backup/create', { method: 'POST' }),
  restoreBackup:   (id)     => apiFetch(`/api/recovery/restore/${id}`, { method: 'POST' }),
  restoreLatest:   ()       => apiFetch('/api/recovery/restore/latest', { method: 'POST' }),
  emergencyBoot:   ()       => apiFetch('/api/recovery/emergency-boot', { method: 'POST' }),
  generateReport:  async () => {
    const res = await fetch(`${BASE}/api/recovery/report/generate?download=true`, { method: 'POST' })
    if (!res.ok) throw new Error(`Report generation failed: ${res.status}`)
    return res.blob()
  },
  assistantChat:   (payload) => apiFetch('/assistant/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
}
