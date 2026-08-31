import React from 'react'
import { motion } from 'framer-motion'
import { BellRing } from 'lucide-react'

const SEV_STYLE = {
  Critical: { dot: 'bg-red-500',    text: 'text-red-400',    bar: 'bg-red-500',    badge: 'bg-red-900/40 text-red-300 border-red-700/50' },
  High:     { dot: 'bg-orange-500', text: 'text-orange-400', bar: 'bg-orange-500', badge: 'bg-orange-900/30 text-orange-300 border-orange-700/40' },
  Medium:   { dot: 'bg-yellow-500', text: 'text-yellow-400', bar: 'bg-yellow-500', badge: 'bg-yellow-900/20 text-yellow-300 border-yellow-700/30' },
}

function SeverityRow({ label, count, color }) {
  const s     = SEV_STYLE[label] || SEV_STYLE.Medium
  const total = 100
  const pct   = Math.min((count / total) * 100, 100)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
          <span className="text-slate-300 text-sm">{label}</span>
        </div>
        <span className={`text-sm font-bold font-mono ${s.text}`}>{count}</span>
      </div>
      <div className="h-1 rounded-full bg-slate-800 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${s.bar}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          style={{ boxShadow: `0 0 6px ${s.dot === 'bg-red-500' ? '#ef4444' : s.dot === 'bg-orange-500' ? '#f97316' : '#eab308'}` }}
        />
      </div>
    </div>
  )
}

export default function AlertSummary({ summary = [] }) {
  const total = summary.reduce((acc, s) => acc + s.count, 0)

  return (
    <div
      className="rounded-xl border border-slate-800/80 h-full flex flex-col overflow-hidden"
      style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
    >
      <div className="px-5 py-4 border-b border-slate-800/60 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <BellRing className="w-4 h-4 text-rose-400" />
          <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Alert Summary</h3>
        </div>
        <span className="text-xs font-mono text-slate-500 bg-slate-800/60 px-2 py-0.5 rounded-full">{total} total</span>
      </div>

      <div className="flex-1 px-5 py-4 space-y-4">
        {summary.map((s) => (
          <SeverityRow key={s.label} {...s} />
        ))}
      </div>

      <div className="px-5 pb-4 text-xs text-slate-600 font-mono">Last 1h · auto-refreshing</div>
    </div>
  )
}
