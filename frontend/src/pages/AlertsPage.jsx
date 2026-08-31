import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BellRing, AlertTriangle, AlertCircle, Info, Filter, X } from 'lucide-react'

const SEV_ORDER = ['critical', 'high', 'medium', 'low']

const SEV_CFG = {
  critical: {
    icon: AlertTriangle,
    dot:  'bg-red-500',
    border: 'border-l-red-500',
    badge: 'bg-red-900/40 border-red-700/50 text-red-300',
    text:  'text-red-400',
    row:   'hover:bg-red-950/15',
  },
  high: {
    icon: AlertCircle,
    dot:  'bg-orange-500',
    border: 'border-l-orange-500',
    badge: 'bg-orange-900/30 border-orange-700/40 text-orange-300',
    text:  'text-orange-400',
    row:   'hover:bg-orange-950/10',
  },
  medium: {
    icon: Info,
    dot:  'bg-yellow-500',
    border: 'border-l-yellow-500',
    badge: 'bg-yellow-900/20 border-yellow-700/30 text-yellow-300',
    text:  'text-yellow-400',
    row:   'hover:bg-yellow-950/10',
  },
  low: {
    icon: Info,
    dot:  'bg-blue-500',
    border: 'border-l-blue-500',
    badge: 'bg-blue-900/20 border-blue-700/30 text-blue-300',
    text:  'text-blue-400',
    row:   'hover:bg-blue-950/10',
  },
}

function AlertCard({ alert }) {
  const cfg = SEV_CFG[alert.severity] || SEV_CFG.medium
  const Icon = cfg.icon

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex items-start gap-4 p-4 rounded-xl border border-slate-800/60 border-l-2 ${cfg.border} ${cfg.row} transition-colors cursor-default`}
      style={{ background: 'rgba(10,15,30,0.7)' }}
    >
      <div className="mt-0.5 shrink-0">
        <Icon className={`w-5 h-5 ${cfg.text}`} />
      </div>

      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-start justify-between gap-3">
          <span className="text-slate-200 font-semibold text-sm leading-snug">{alert.title}</span>
          <span className="text-slate-500 text-xs font-mono shrink-0 pt-0.5">{alert.time}</span>
        </div>
        <p className="text-slate-400 text-xs leading-relaxed">{alert.description}</p>
        <div className="flex items-center gap-2 pt-1">
          <span className="text-slate-600 text-xs font-mono">{alert.source}</span>
        </div>
      </div>

      <span className={`shrink-0 text-[10px] font-bold tracking-widest px-2 py-0.5 rounded border ${cfg.badge} uppercase self-start`}>
        {alert.severity}
      </span>
    </motion.div>
  )
}

const FILTERS = ['all', 'critical', 'high', 'medium', 'low']

export default function AlertsPage({ events = [] }) {
  const [filter, setFilter] = useState('all')

  // treat events as alerts — sort by severity
  const alerts = [...events].sort((a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity))
  const filtered = filter === 'all' ? alerts : alerts.filter(a => a.severity === filter)

  const counts = SEV_ORDER.reduce((acc, s) => {
    acc[s] = alerts.filter(a => a.severity === s).length
    return acc
  }, {})

  return (
    <div className="space-y-5">
      {/* page header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BellRing className="w-5 h-5 text-rose-400" />
            <h1 className="text-slate-100 font-bold text-xl">Alerts</h1>
          </div>
          <p className="text-slate-500 text-sm">Realtime security alert stream · {alerts.length} total</p>
        </div>

        {/* severity summary pills */}
        <div className="hidden sm:flex items-center gap-2">
          {SEV_ORDER.map(s => counts[s] > 0 && (
            <span key={s} className={`text-xs font-mono px-3 py-1.5 rounded-full border ${SEV_CFG[s].badge}`}>
              {counts[s]} {s}
            </span>
          ))}
        </div>
      </div>

      {/* filter bar */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        {FILTERS.map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`
              text-xs px-3 py-1.5 rounded-lg border font-mono transition-all capitalize
              ${filter === f
                ? 'bg-blue-600/30 border-blue-500/60 text-blue-300'
                : 'border-slate-700/40 text-slate-500 hover:text-slate-300 hover:border-slate-600/50'}
            `}
          >
            {f === 'all' ? `All (${alerts.length})` : `${f} (${counts[f] || 0})`}
          </button>
        ))}
      </div>

      {/* alert list */}
      <div
        className="rounded-xl border border-slate-800/80 overflow-hidden"
        style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
      >
        <div className="p-3 space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="py-16 text-center space-y-2 text-slate-600">
              <BellRing className="w-8 h-8 mx-auto opacity-30" />
              <p className="text-sm">No {filter === 'all' ? '' : filter} alerts</p>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {filtered.map(a => <AlertCard key={a.id} alert={a} />)}
            </AnimatePresence>
          )}
        </div>
      </div>
    </div>
  )
}
