import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, AlertCircle, Info, CheckCircle, X } from 'lucide-react'

const TYPE_CFG = {
  critical: {
    icon: AlertTriangle,
    bg:   'bg-gradient-to-r from-red-950 to-red-900',
    border: 'border-red-600/60',
    text: 'text-red-300',
    title: 'text-red-200',
    glow: '0 0 20px rgba(239,68,68,0.3)',
  },
  high: {
    icon: AlertCircle,
    bg:   'bg-gradient-to-r from-orange-950 to-orange-900',
    border: 'border-orange-600/50',
    text: 'text-orange-300',
    title: 'text-orange-200',
    glow: '0 0 16px rgba(249,115,22,0.25)',
  },
  medium: {
    icon: Info,
    bg:   'bg-gradient-to-r from-slate-900 to-slate-800',
    border: 'border-slate-600/50',
    text: 'text-slate-400',
    title: 'text-slate-200',
    glow: '0 0 10px rgba(100,116,139,0.15)',
  },
  success: {
    icon: CheckCircle,
    bg:   'bg-gradient-to-r from-emerald-950 to-emerald-900',
    border: 'border-emerald-600/50',
    text: 'text-emerald-300',
    title: 'text-emerald-200',
    glow: '0 0 16px rgba(34,197,94,0.2)',
  },
}

function Toast({ toast, onRemove }) {
  const cfg  = TYPE_CFG[toast.severity] || TYPE_CFG.medium
  const Icon = cfg.icon

  useEffect(() => {
    const t = setTimeout(() => onRemove(toast.id), toast.duration || 5000)
    return () => clearTimeout(t)
  }, [toast.id])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -60, scale: 0.96 }}
      animate={{ opacity: 1, x: 0,  scale: 1    }}
      exit={{    opacity: 0, x: -60, scale: 0.96, transition: { duration: 0.2 } }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl border ${cfg.bg} ${cfg.border} min-w-72 max-w-sm cursor-pointer`}
      style={{ boxShadow: cfg.glow }}
      onClick={() => onRemove(toast.id)}
    >
      <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${cfg.text}`} />
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-semibold ${cfg.title}`}>
          {typeof toast.title === 'object' ? JSON.stringify(toast.title) : toast.title}
        </div>
        {toast.message && (
          <div className={`text-xs mt-0.5 ${cfg.text} line-clamp-2`}>
            {typeof toast.message === 'object' ? JSON.stringify(toast.message) : toast.message}
          </div>
        )}
      </div>
      <X className={`w-3.5 h-3.5 shrink-0 ${cfg.text} opacity-60 hover:opacity-100 transition-opacity`} />
    </motion.div>
  )
}

export default function ToastContainer({ toasts, onRemove }) {
  return (
    <div className="fixed bottom-6 left-6 z-[100] flex flex-col gap-2 items-start pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((t) => (
          <Toast key={t.id} toast={t} onRemove={onRemove} />
        ))}
      </AnimatePresence>
    </div>
  )
}
