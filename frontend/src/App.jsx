import React, { useState, useEffect, useCallback } from 'react'
import { Routes, Route } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { connect, disconnect, listen } from './services/socket'
import { api } from './services/api'

import Sidebar from './components/Layout/Sidebar'
import Navbar from './components/Layout/Navbar'
import ThreatScoreCard from './components/Dashboard/ThreatScoreCard'
import SystemStatusCard from './components/Dashboard/SystemStatusCard'
import LiveEventFeed from './components/Dashboard/LiveEventFeed'
import AlertSummary from './components/Dashboard/AlertSummary'
import ProcessAnomalyPanel from './components/Dashboard/ProcessAnomalyPanel'
import AttackTimeline from './components/Dashboard/AttackTimeline'
import ToastContainer from './components/Dashboard/ToastContainer'
import ScanModal from './components/Dashboard/ScanModal'
import AssetsPanel from './components/Dashboard/AssetsPanel'
import { ShieldOff, X, Loader, WifiOff } from 'lucide-react'
import Recovery from "./pages/Recovery";
import RecoveryAssistant from './components/Chatbot/RecoveryAssistant';

// Pages
import AlertsPage from './pages/AlertsPage'
import LiveFeedPage from './pages/LiveFeedPage'
import AssetsPage from './pages/AssetsPage'

// ── helpers ───────────────────────────────────────────────────────────────────
function severityToStage(severity) {
  if (severity === 'critical') return 4
  if (severity === 'high')     return 3
  if (severity === 'medium')   return 2
  return 1
}

// ── Quarantine banner ─────────────────────────────────────────────────────────
function QuarantineBanner({ onDismiss }) {
  return (
    <motion.div
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0,   opacity: 1 }}
      exit={{    y: -80, opacity: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="fixed top-14 left-0 right-0 z-50 flex items-center gap-4 px-6 py-3 border-b"
      style={{
        background:  'linear-gradient(90deg, #180000 0%, #2d0000 50%, #180000 100%)',
        borderColor: '#ef4444',
        boxShadow:   '0 0 40px rgba(239,68,68,0.45)',
      }}
    >
      <motion.div
        animate={{ opacity: [1, 0.45, 1] }}
        transition={{ duration: 0.75, repeat: Infinity }}
        className="flex items-center gap-2 text-red-400 shrink-0"
      >
        <ShieldOff className="w-5 h-5" />
        <span className="font-bold text-sm tracking-widest uppercase">System Quarantined</span>
      </motion.div>
      <span className="text-red-300/80 text-sm hidden sm:block">
        Ransomware activity detected · Isolation mode activated · All outbound traffic blocked
      </span>
      <button
        onClick={onDismiss}
        className="ml-auto p-1.5 rounded hover:bg-red-900/40 text-red-400 hover:text-red-200 transition-colors shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  )
}

// ── Operation button ──────────────────────────────────────────────────────────
function OpButton({ label, onClick, loading, disabled, danger }) {
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className={`
        flex items-center justify-center gap-2 px-4 py-3 rounded-lg border text-sm font-mono transition-all
        ${danger
          ? 'border-red-700/50 text-red-400 hover:bg-red-900/30 hover:border-red-600/60 hover:text-red-300'
          : 'border-slate-700/40 text-slate-400 hover:bg-slate-800/40 hover:border-slate-600/60 hover:text-slate-200'}
        disabled:opacity-40 disabled:cursor-not-allowed
      `}
    >
      {loading && <Loader className="w-3.5 h-3.5 animate-spin shrink-0" />}
      {!loading && <span>›</span>}
      {label}
    </button>
  )
}

// ── Dashboard Overview Component ──────────────────────────────────────────────────
function DashboardOverview({ 
  attackStage, threatScore, stats, summary, events, assets, scan, opLoading,
  handleStartScan, handleIsolateNetwork, handleContainHost, handleDemoAttack, networkIsolated
}) {
  return (
    <div className="space-y-5">
      {/* Attack Timeline */}
      <AttackTimeline activeStage={attackStage} />

      {/* Row 1: Threat Score + System Status + Alert Summary */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 items-stretch">
        <div className="sm:col-span-2 lg:col-span-2">
          <ThreatScoreCard score={threatScore} />
        </div>
        <div><SystemStatusCard stats={stats} /></div>
        <div><AlertSummary summary={summary} /></div>
      </section>

      {/* Row 2: Live Feed + Process Panel */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <LiveEventFeed events={events} />
        </div>
        <div>
          <ProcessAnomalyPanel />
        </div>
      </section>

      {/* Row 3: Assets + Operations */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <AssetsPanel assets={assets} />

        {/* Operations panel */}
        <div
          className="rounded-xl border border-slate-800/80 overflow-hidden flex flex-col"
          style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
        >
          <div className="px-5 py-4 border-b border-slate-800/60 flex items-center justify-between shrink-0">
            <div>
              <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Rapid Response</h3>
              <p className="text-slate-500 text-xs mt-0.5">Actions logged to audit trail</p>
            </div>
          </div>

          <div className="flex-1 p-4 grid grid-cols-2 gap-3">
            <OpButton
              label="Start Full Scan"
              loading={opLoading.scan}
              disabled={scan?.phase === 'running'}
              onClick={handleStartScan}
            />
            <OpButton
              label="Isolate Network"
              loading={opLoading.isolate}
              disabled={networkIsolated}
              onClick={handleIsolateNetwork}
              danger
            />
            <OpButton
              label="Contain Host"
              loading={opLoading.contain}
              onClick={handleContainHost}
            />
            <OpButton
              label="Simulate Attack"
              loading={opLoading.demo}
              onClick={handleDemoAttack}
              danger
            />
          </div>

          {/* Scan status mini indicator */}
          {scan?.phase === 'running' && (
            <div className="px-4 pb-4">
              <div className="flex items-center justify-between text-xs font-mono text-slate-500 mb-1">
                <span>Scanning… {scan.scanned?.toLocaleString()} / {scan.total?.toLocaleString()} files</span>
                <span className={scan.threats_found > 0 ? 'text-rose-400' : 'text-slate-500'}>
                  {scan.threats_found} threats
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-blue-500"
                  style={{ width: `${scan.percent || 0}%` }}
                  transition={{ duration: 0.2 }}
                />
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [collapsed,    setCollapsed]    = useState(false)
  const [threatScore,  setThreatScore]  = useState(68)
  const [socketStatus, setSocketStatus] = useState('connecting')
  const [quarantined,  setQuarantined]  = useState(false)
  const [networkIsolated, setNetworkIsolated] = useState(false)
  const [attackStage,  setAttackStage]  = useState(0)
  const [toasts,       setToasts]       = useState([])
  const [toastQueue,   setToastQueue]   = useState([])
  const [scan,         setScan]         = useState(null)   // null | { phase, ... }

  const [opLoading,    setOpLoading]    = useState({})
  const [assets,       setAssets]       = useState([])

  const [events, setEvents] = useState([
    { id: 1, title: 'Ransomware family behavior flagged',  time: '2m ago',  source: 'Sensor-12',  severity: 'critical', description: 'Suspicious encryption activity'      },
    { id: 2, title: 'Malicious domain blocked',           time: '5m ago',  source: 'DNS',        severity: 'high',     description: 'Known C2 domain contacted'           },
    { id: 3, title: 'New process launched as admin',      time: '12m ago', source: 'Endpoint-3', severity: 'medium',   description: 'Unusual parent-child process tree'   },
    { id: 4, title: 'Multiple failed logins',             time: '18m ago', source: 'Auth',       severity: 'medium',   description: 'Brute force signature matched'       },
  ])

  const stats = [
    { label: 'Hosts Online',        value: 1248, delta: '+2.3%',       color: 'text-emerald-400' },
    { label: 'Infected Hosts',      value: 12,   delta: '-1 this hour', color: 'text-rose-400'   },
    { label: 'Blocked Connections', value: 4823, delta: '+8%',          color: 'text-amber-300'  },
  ]

  const summary = [
    { label: 'Critical', count: 7,  color: 'bg-rose-500'  },
    { label: 'High',     count: 21, color: 'bg-amber-500' },
    { label: 'Medium',   count: 64, color: 'bg-sky-400'   },
  ]

  // ── toast helper ────────────────────────────────────────────────────────────
  const pushToast = useCallback((title, message, severity = 'medium', duration = 5000) => {
    setToastQueue(prev => {
      // Deduplicate: check if identical toast is already in queue
      const isDuplicate = prev.some(t => t.title === title && t.message === message)
      if (isDuplicate) return prev

      // Limit queue size to avoid backlog spam
      if (prev.length >= 5) return prev

      const id = Date.now() + Math.random()
      return [...prev, { id, title, message, severity, duration }]
    })
  }, [])

  // Process toast queue
  useEffect(() => {
    if (toastQueue.length > 0 && toasts.length < 2) {
      const timer = setTimeout(() => {
        const nextToast = toastQueue[0]
        
        // Final check before showing: ensure not already visible
        setToasts(prev => {
          const isVisible = prev.some(t => t.title === nextToast.title && t.message === nextToast.message)
          if (isVisible) return prev
          return [...prev, nextToast]
        })
        
        setToastQueue(prev => prev.slice(1))
      }, 600) // Stagger delay for premium feel

      return () => clearTimeout(timer)
    }
  }, [toastQueue, toasts])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  // ── initial data load ────────────────────────────────────────────────────────
  useEffect(() => {
    // restore recent events from REST
    api.recentEvents(25).then(data => {
      if (!data.events?.length) return
      const restored = data.events.map(e => ({
        id:          e.id,
        title:       e.event_type?.replace(/_/g, ' ') || 'Event',
        time:        e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : '—',
        source:      e.file_path || e.process_name || 'System',
        severity:    e.threat_score >= 85 ? 'critical' : e.threat_score >= 65 ? 'high' : e.threat_score >= 35 ? 'medium' : 'low',
        description: `Threat score: ${e.threat_score}`,
      }))
      setEvents(prev => [...restored, ...prev].slice(0, 50))
    }).catch(() => {})

    // load assets
    api.honeypotAssets().then(data => {
      setAssets(data.assets || [])
    }).catch(() => {})

    // restore quarantine state
    api.quarantineStatus().then(data => {
      if (data.isolated) setNetworkIsolated(true)
    }).catch(() => {})
  }, [])

  // ── websocket ────────────────────────────────────────────────────────────────
  useEffect(() => {
    connect()
    const stop = listen((data) => {
      switch (data.type) {

        case 'STATUS_UPDATE':
          setSocketStatus(data.value)
          break

        case 'THREAT_UPDATE': {
          const score = Number(
            data.score
            || data.payload?.threat_score
            || data.payload?.score
          ) || 0
          setThreatScore(score)
          if      (score >= 90) setAttackStage(s => Math.max(s, 4))
          else if (score >= 75) setAttackStage(s => Math.max(s, 3))
          else if (score >= 50) setAttackStage(s => Math.max(s, 2))
          else if (score >= 25) setAttackStage(s => Math.max(s, 1))
          break
        }

        case 'NEW_EVENT':
        case 'ALERT': {
          const payload = data.payload || data.data || data.event
          if (!payload) break
          const newEvent = {
            id:          payload.id || Date.now() + Math.random(),
            title:       payload.title || payload.event_type || 'Alert',
            time:        payload.timestamp ? new Date(payload.timestamp).toLocaleTimeString() : 'Just now',
            source:      payload.file_path || payload.source || 'System',
            severity:    payload.severity || 'medium',
            description: payload.description || 'System event',
          }
          setEvents(prev => [newEvent, ...prev].slice(0, 50))
          setAttackStage(s => Math.max(s, severityToStage(newEvent.severity)))
          if (newEvent.severity === 'critical') pushToast(newEvent.title, newEvent.description, 'critical', 7000)
          else if (newEvent.severity === 'high') pushToast(newEvent.title, newEvent.description, 'high', 5000)
          break
        }

        case 'ISOLATION_TRIGGERED':
          setQuarantined(true)
          setAttackStage(5)
          pushToast('SYSTEM QUARANTINED', 'Isolation mode activated. All outbound traffic blocked.', 'critical', 10000)
          break

        case 'NETWORK_ISOLATED':
          setNetworkIsolated(true)
          setAttackStage(s => Math.max(s, 5))
          pushToast('Network Isolated', 'All network traffic has been blocked.', 'critical', 8000)
          break

        case 'SCAN_STARTED':
          setScan({ phase: 'running', scanned: 0, total: data.payload?.total_files, percent: 0, threats_found: 0 })
          break

        case 'SCAN_PROGRESS':
          setScan(prev => prev ? {
            ...prev,
            phase:         'running',
            scanned:       data.payload?.scanned       ?? prev.scanned,
            total:         data.payload?.total         ?? prev.total,
            percent:       data.payload?.percent       ?? prev.percent,
            threats_found: data.payload?.threats_found ?? prev.threats_found,
          } : prev)
          break

        case 'SCAN_COMPLETED':
          setScan({
            phase:         'completed',
            scanned:       data.payload?.scanned,
            total:         data.payload?.scanned,
            percent:       100,
            threats_found: data.payload?.threats_found,
            threat_score:  data.payload?.threat_score,
          })
          if (data.payload?.threats_found > 0) {
            pushToast(
              `Scan Complete: ${data.payload.threats_found} threats found`,
              `Threat score updated to ${data.payload.threat_score}`,
              'high', 8000
            )
          } else {
            pushToast('Scan Complete', 'No threats detected. System appears clean.', 'success', 5000)
          }
          break

        case 'RECOVERY_CREATED':
          pushToast('Snapshot Created', data.payload?.message || 'New system snapshot stored successfully.', 'success', 5000)
          break

        case 'RECOVERY_RESTORED':
          pushToast('System Restored', data.payload?.message || 'Backup restoration completed successfully.', 'success', 7000)
          break

        case 'RECOVERY_FAILED':
          pushToast('Recovery Action Failed', data.payload?.message || 'Operation could not be completed.', 'critical', 8000)
          break

        default:
          break
      }
    })

    return () => { stop(); disconnect() }
  }, [pushToast])

  // ── operations ────────────────────────────────────────────────────────────────
  const runOp = useCallback(async (key, apiFn, onSuccess) => {
    setOpLoading(prev => ({ ...prev, [key]: true }))
    try {
      const result = await apiFn()
      onSuccess?.(result)
    } catch (e) {
      pushToast(`Operation Failed`, e.message || 'Request failed', 'medium', 4000)
    } finally {
      setOpLoading(prev => ({ ...prev, [key]: false }))
    }
  }, [pushToast])

  const handleStartScan = () => runOp('scan', api.startFullScan, (res) => {
    if (res.status === 'already_running') {
      pushToast('Scan Already Running', 'A scan is already in progress.', 'medium')
      setScan(prev => prev || { phase: 'running', percent: 0, threats_found: 0 })
    }
  })

  const handleIsolateNetwork = () => runOp('isolate', api.isolateNetwork, () => {
    setNetworkIsolated(true)
    pushToast('Network Isolation Requested', 'Isolation command sent to backend.', 'high')
  })

  const handleContainHost = () => runOp('contain', () => api.containHost('Endpoint-1'), () => {
    pushToast('Host Containment Requested', 'Endpoint-1 containment command sent.', 'high')
  })

  const handleDemoAttack = () => runOp('demo', api.demoEvent, () => {
    pushToast('Attack Simulation Started', 'Demo ransomware event triggered on backend.', 'critical', 5000)
    setAttackStage(s => Math.max(s, 3))
  })

  // ── layout offsets ────────────────────────────────────────────────────────────
  const bannerOffset = quarantined ? 'mt-28' : 'mt-14'

  return (
    <div
      className="min-h-screen text-slate-200 relative"
      style={{ background: 'linear-gradient(160deg, #050a14 0%, #070c18 60%, #050a14 100%)' }}
    >
      {/* quarantine danger tint */}
      <AnimatePresence>
        {(quarantined || networkIsolated) && (
          <motion.div
            key="danger-env"
            className="fixed inset-0 pointer-events-none z-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ background: 'radial-gradient(ellipse at top, rgba(239,68,68,0.07) 0%, transparent 60%)' }}
          />
        )}
      </AnimatePresence>

      <Sidebar collapsed={collapsed} />
      <Navbar onToggleSidebar={() => setCollapsed(s => !s)} status={socketStatus} />

      <AnimatePresence>
        {quarantined && <QuarantineBanner onDismiss={() => setQuarantined(false)} />}
      </AnimatePresence>

      {/* Network isolation sub-banner */}
      <AnimatePresence>
        {networkIsolated && !quarantined && (
          <motion.div
            initial={{ y: -60, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -60, opacity: 0 }}
            className="fixed top-14 left-0 right-0 z-50 flex items-center gap-3 px-6 py-2 border-b border-orange-800/60"
            style={{ background: 'linear-gradient(90deg, #1a0800 0%, #2a1000 50%, #1a0800 100%)' }}
          >
            <WifiOff className="w-4 h-4 text-orange-400 shrink-0" />
            <span className="text-orange-300 text-sm font-semibold">Network Isolated</span>
            <span className="text-orange-400/70 text-xs hidden sm:block">All outbound connections blocked</span>
            <button
              onClick={() => setNetworkIsolated(false)}
              className="ml-auto p-1 rounded hover:bg-orange-900/40 text-orange-400 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className={`md:ml-64 transition-all duration-200 ${bannerOffset} relative z-10`}>
        <main className="p-6 max-w-[1440px] mx-auto">
          <Routes>
            <Route path="/" element={
              <DashboardOverview 
                attackStage={attackStage} threatScore={threatScore} stats={stats} summary={summary}
                events={events} assets={assets} scan={scan} opLoading={opLoading}
                handleStartScan={handleStartScan} handleIsolateNetwork={handleIsolateNetwork}
                handleContainHost={handleContainHost} handleDemoAttack={handleDemoAttack}
                networkIsolated={networkIsolated}
              />
            } />
            <Route path="/alerts" element={<AlertsPage events={events} />} />
            <Route path="/live" element={<LiveFeedPage events={events} />} />
            <Route path="/assets" element={<AssetsPage assets={assets} />} />
            <Route path="/settings" element={<div className="p-10 text-slate-500">Settings panel configuration...</div>} />
            <Route path="/recovery" element={<Recovery />} />
          </Routes>
        </main>
      </div>

      {/* Scan modal */}
      <ScanModal scan={scan} onClose={() => setScan(null)} />

      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />

      {/* Floating Chatbot Assistant */}
      <RecoveryAssistant 
        threatScore={threatScore} 
        quarantined={quarantined} 
        networkIsolated={networkIsolated} 
        events={events} 
      />
    </div>
  )
}
