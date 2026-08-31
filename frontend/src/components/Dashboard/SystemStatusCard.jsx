import React from 'react'
import { motion } from 'framer-motion'

function Stat({ label, value, delta, color = 'text-slate-200' }) {
  return (
    <div
      className="p-4 rounded-lg border border-slate-800/60 flex flex-col gap-1"
      style={{ background: 'rgba(15,23,42,0.7)' }}
    >
      <div className="text-slate-500 text-xs font-mono uppercase tracking-wider">{label}</div>
      <motion.div
        key={value}
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className={`text-2xl font-bold font-mono ${color}`}
      >
        {typeof value === 'number' ? value.toLocaleString() : value}
      </motion.div>
      {delta !== undefined && (
        <div className="text-xs text-slate-500 font-mono">{delta}</div>
      )}
    </div>
  )
}

export default function SystemStatusCard({ stats = [] }) {
  return (
    <div
      className="rounded-xl border border-slate-800/80 h-full flex flex-col overflow-hidden"
      style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
    >
      <div className="px-5 py-4 border-b border-slate-800/60 shrink-0">
        <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">System Status</h3>
      </div>
      <div className="flex-1 p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
        {stats.map((s) => (
          <Stat key={s.label} {...s} />
        ))}
      </div>
    </div>
  )
}
