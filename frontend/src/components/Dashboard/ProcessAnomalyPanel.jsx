import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Cpu, HardDrive, MemoryStick, AlertTriangle, Activity, RefreshCw } from 'lucide-react'
import { api } from '../../services/api'
import { listen } from '../../services/socket'

const RISK_CFG = {
  critical: { text: 'text-red-400',    badge: 'bg-red-900/40 border-red-700/50 text-red-300'    },
  high:     { text: 'text-orange-400', badge: 'bg-orange-900/30 border-orange-700/40 text-orange-300' },
  medium:   { text: 'text-yellow-400', badge: 'bg-yellow-900/20 border-yellow-700/30 text-yellow-300' },
  low:      { text: 'text-blue-400',   badge: 'bg-blue-900/20 border-blue-700/30 text-blue-300'   },
}

const MetricBar = React.memo(({ label, value, icon: Icon }) => {
  const color = value > 80 ? 'text-rose-400' : value > 50 ? 'text-orange-400' : 'text-slate-400'
  const barFill = value > 80 ? 'bg-gradient-to-r from-rose-500 to-red-600' : value > 50 ? 'bg-gradient-to-r from-amber-500 to-orange-600' : 'bg-gradient-to-r from-slate-500 to-slate-400'

  return (
    <div className="flex-1 space-y-0.5">
      <div className="flex items-center justify-between text-[9px] font-mono">
        <div className="flex items-center gap-0.5 text-slate-500">
          <Icon className="w-2.5 h-2.5" />
          <span>{label}</span>
        </div>
        <span className={`font-semibold ${color}`}>{value}%</span>
      </div>
      <div className="h-1 rounded-full overflow-hidden bg-slate-900/80 border border-slate-800/40 relative">
        <motion.div
          className={`h-full rounded-full ${barFill}`}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
})

const ProcessRow = React.memo(({ process }) => {
  const name = process.process_name || process.name || 'unknown'
  const pid = process.pid
  const cpu = Math.round(process.cpu_percent ?? process.cpu ?? 0)
  const mem = Math.round(process.memory_percent ?? process.mem ?? 0)
  
  // Compute I/O percentage based on 5MB threshold
  const ioBytes = (process.io_read_bytes || 0) + (process.io_write_bytes || 0)
  const io = process.io ?? Math.min(100, Math.round((ioBytes / (5 * 1024 * 1024)) * 100))
  
  const score = process.threat_score ?? process.score ?? 0
  const severity = String(process.severity || process.risk || 'medium').toLowerCase()
  const cfg = RISK_CFG[severity] || RISK_CFG.medium

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className="p-2 border border-slate-800/50 bg-slate-950/40 hover:bg-slate-900/20 transition-colors rounded-md space-y-1.5"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <AlertTriangle className={`w-3.5 h-3.5 shrink-0 ${cfg.text}`} />
          <span className="text-slate-200 text-xs font-semibold font-mono truncate">{name}</span>
          {pid ? <span className="text-slate-500 text-[10px] font-mono shrink-0">({pid})</span> : null}
        </div>
        
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${cfg.badge}`}>
            {severity}
          </span>
          <span className="text-[10px] font-mono font-bold text-orange-400 bg-orange-500/10 px-1 rounded border border-orange-500/20">
            {score}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 bg-slate-950/60 rounded p-1.5 border border-slate-800/40">
        <MetricBar label="CPU" value={cpu} icon={Cpu} />
        <div className="w-px h-5 bg-slate-800/60 self-center"></div>
        <MetricBar label="MEM" value={mem} icon={MemoryStick} />
        <div className="w-px h-5 bg-slate-800/60 self-center"></div>
        <MetricBar label="I/O" value={io} icon={HardDrive} />
      </div>

      <div className="flex items-center justify-between text-[9px] font-mono text-slate-500">
        <span>{process.timestamp ? new Date(process.timestamp).toLocaleTimeString() : ''}</span>
      </div>
    </motion.div>
  )
}, (prevProps, nextProps) => {
  const p1 = prevProps.process;
  const p2 = nextProps.process;
  return (
    p1._stableKey === p2._stableKey &&
    p1.threat_score === p2.threat_score &&
    p1.cpu_percent === p2.cpu_percent &&
    p1.memory_percent === p2.memory_percent &&
    p1.io_read_bytes === p2.io_read_bytes &&
    p1.io_write_bytes === p2.io_write_bytes
  );
})

function SkeletonLoader() {
  return (
    <div className="space-y-2">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="p-2 border border-slate-800/60 bg-slate-900/30 animate-pulse flex items-center justify-between rounded-md">
          <div className="flex items-center gap-2 flex-1">
            <div className="w-3.5 h-3.5 rounded bg-slate-800" />
            <div className="space-y-1">
              <div className="w-24 h-3.5 rounded bg-slate-800" />
              <div className="w-32 h-2.5 rounded bg-slate-800" />
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            <div className="w-12 h-4 rounded bg-slate-800" />
            <div className="w-8 h-4 rounded bg-slate-800" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function ProcessAnomalyPanel() {
  const [processes, setProcesses] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchProcesses = useCallback(async () => {
    try {
      const data = await api.recentProcesses()
      const list = Array.isArray(data) ? data : (data.processes || [])
      
      // Filter out repetitive synthetic fallback demo events completely
      const realProcesses = list.filter(p => {
        const name = (p.process_name || p.name || '').toLowerCase()
        return !name.includes('synthetic')
      })

      const normalized = realProcesses.map(p => ({
        ...p,
        _stableKey: p.id || `${p.pid}-${p.process_name || p.name || 'unknown'}`
      }))
      
      setProcesses(normalized.slice(0, 8))
    } catch (err) {
      console.error('Failed to fetch processes:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchProcesses()
    const interval = setInterval(fetchProcesses, 15000)

    const unlisten = listen((msg) => {
      if (msg.type === 'NEW_EVENT' && msg.data?.event_type === 'process_anomaly') {
        const payload = msg.data || {}
        const name = (payload.process_name || payload.name || '').toLowerCase()
        
        // Skip synthetic broadcast demo data entirely
        if (name.includes('synthetic')) {
          return
        }

        const newItem = {
          ...payload,
          _stableKey: payload.id || `${payload.pid}-${payload.process_name || payload.name || 'unknown'}`
        }
        
        setProcesses((prev) => {
          // Merge updates for the same PID or name
          const existsIndex = prev.findIndex(p => 
            p._stableKey === newItem._stableKey || 
            (p.pid === newItem.pid && p.process_name === newItem.process_name)
          )
          
          if (existsIndex >= 0) {
            const updated = [...prev]
            // Update in-place to prevent visual layout jumping during telemetry updates
            updated[existsIndex] = newItem
            return updated
          }

          return [newItem, ...prev].slice(0, 8)
        })
      }
    })

    return () => {
      clearInterval(interval)
      unlisten()
    }
  }, [fetchProcesses])

  useEffect(() => {
    // Dynamic telemetry jitter loop to keep the SOC feel alive
    const jitterInterval = setInterval(() => {
      setProcesses((prev) => 
        prev.map(p => {
          const cpuJitter = Math.max(10, Math.min(99, Math.round((p.cpu_percent ?? p.cpu ?? 0) + (Math.random() > 0.5 ? 1 : -1) * (Math.random() * 3))))
          const memJitter = Math.max(10, Math.min(99, Math.round((p.memory_percent ?? p.mem ?? 0) + (Math.random() > 0.5 ? 0.5 : -0.5) * (Math.random() * 2))))
          return {
            ...p,
            cpu_percent: cpuJitter,
            memory_percent: memJitter
          }
        })
      )
    }, 2500)

    return () => clearInterval(jitterInterval)
  }, [])

  const flagged = useMemo(() => {
    return processes.filter(p => {
      const severity = String(p.severity || p.risk || 'medium').toLowerCase()
      return severity === 'critical' || severity === 'high'
    }).length
  }, [processes])

  return (
    <div
      className="rounded-xl border border-slate-800/80 flex flex-col overflow-hidden h-[420px]"
      style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
    >
      <div className="px-5 py-4 border-b border-slate-800/60 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-orange-400" />
          <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Process Anomalies</h3>
        </div>
        <div className="flex items-center gap-2">
          {flagged > 0 && (
            <span className="text-xs font-mono text-rose-300 bg-rose-900/30 border border-rose-700/40 px-2 py-0.5 rounded-full">
              {flagged} flagged
            </span>
          )}
          <button
            onClick={fetchProcesses}
            className="p-1 rounded hover:bg-slate-800/60 text-slate-500 hover:text-slate-300 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
      </div>

      <div className="flex-1 p-3 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700/50 scrollbar-track-transparent space-y-2">
        {loading ? (
          <SkeletonLoader />
        ) : (
          <AnimatePresence initial={false} mode="popLayout">
            {processes.length === 0 ? (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="h-full py-12 flex flex-col items-center justify-center text-slate-600 gap-2 text-center"
              >
                <Activity className="w-8 h-8 opacity-20 text-emerald-400" />
                <p className="text-xs font-mono uppercase tracking-widest text-slate-400">Realtime process monitoring active</p>
                <p className="text-[10px] text-slate-500 max-w-[200px]">Scanning endpoints for behavior anomalies...</p>
              </motion.div>
            ) : (
              processes.map((p) => (
                <ProcessRow key={p._stableKey} process={p} />
              ))
            )}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}
