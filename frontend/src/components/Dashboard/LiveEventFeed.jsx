import React, { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, AlertCircle, Info, Zap } from 'lucide-react'

const SEV_MAP = {
  critical: {
    icon: AlertTriangle,
    color: 'text-red-400',
    dot: 'bg-red-500',
    border: 'border-l-red-500',
    bg: 'hover:bg-red-950/20',
    badge: 'bg-red-900/40 text-red-300 border-red-700/50',
  },
  high: {
    icon: AlertCircle,
    color: 'text-orange-400',
    dot: 'bg-orange-500',
    border: 'border-l-orange-500',
    bg: 'hover:bg-orange-950/15',
    badge: 'bg-orange-900/30 text-orange-300 border-orange-700/40',
  },
  medium: {
    icon: Info,
    color: 'text-yellow-400',
    dot: 'bg-yellow-500',
    border: 'border-l-yellow-500',
    bg: 'hover:bg-yellow-950/10',
    badge: 'bg-yellow-900/20 text-yellow-300 border-yellow-700/30',
  },
  low: {
    icon: Info,
    color: 'text-blue-400',
    dot: 'bg-blue-500',
    border: 'border-l-blue-500',
    bg: 'hover:bg-blue-950/10',
    badge: 'bg-blue-900/20 text-blue-300 border-blue-700/30',
  },
}

function EventRow({ evt }) {
  const cfg = SEV_MAP[evt.severity] || SEV_MAP.medium
  const Icon = cfg.icon

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -12, height: 0 }}
      animate={{ opacity: 1, x: 0, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
      className={`flex items-start gap-3 p-3 rounded-lg border-l-2 ${cfg.border} ${cfg.bg} transition-colors cursor-default`}
      style={{ background: 'rgba(15,23,42,0.6)' }}
    >
      <div className="mt-0.5 shrink-0">
        <Icon className={`w-4 h-4 ${cfg.color}`} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-0.5">
          <span className="text-slate-200 text-sm font-medium truncate">{evt.title}</span>
          <span className="text-slate-500 text-xs font-mono shrink-0">{evt.time}</span>
        </div>
        <div className="text-slate-400 text-xs truncate">{evt.source} — {evt.description}</div>
      </div>

      <span className={`shrink-0 text-[10px] font-bold tracking-widest px-1.5 py-0.5 rounded border ${cfg.badge} uppercase`}>
        {evt.severity}
      </span>
    </motion.div>
  )
}

export default function LiveEventFeed({ events = [], fullHeight = false }) {
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [events.length])

  return (
    <div
      className={`rounded-xl border border-slate-800/80 flex flex-col overflow-hidden ${fullHeight ? 'h-full' : 'h-[420px]'}`}
      style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
    >
      {/* header */}
      <div className="px-5 py-4 flex items-center justify-between border-b border-slate-800/60 shrink-0">
        <div className="flex items-center gap-2.5">
          <Zap className="w-4 h-4 text-blue-400" />
          <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Live Event Feed</h3>
          <span className="text-xs text-slate-500 font-mono bg-slate-800/60 px-2 py-0.5 rounded-full">
            {events.length} events
          </span>
        </div>

        <div className="flex items-center gap-2">
          <motion.span
            className="w-2 h-2 rounded-full bg-emerald-500"
            animate={{ opacity: [1, 0.3, 1], scale: [1, 0.8, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <span className="text-slate-500 text-xs">Streaming</span>
        </div>
      </div>

      {/* feed */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-2 scrollbar-thin scrollbar-thumb-slate-700/50">
        {events.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-600">
            <Zap className="w-8 h-8 opacity-30" />
            <p className="text-sm">Awaiting events…</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {events.map((e) => (
              <EventRow key={e.id} evt={e} />
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}
