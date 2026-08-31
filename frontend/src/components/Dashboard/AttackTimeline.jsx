import React from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, Eye, FileX, Lock, ShieldOff, Flame } from 'lucide-react'

const STAGES = [
  { id: 0, label: 'Healthy',              icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500', ring: 'ring-emerald-500/40' },
  { id: 1, label: 'Suspicious Process',   icon: Eye,         color: 'text-yellow-400',  bg: 'bg-yellow-500',  ring: 'ring-yellow-500/40'  },
  { id: 2, label: 'Rapid Modifications',  icon: FileX,       color: 'text-orange-400',  bg: 'bg-orange-500',  ring: 'ring-orange-500/40'  },
  { id: 3, label: 'Files Encrypted',      icon: Lock,        color: 'text-rose-400',    bg: 'bg-rose-500',    ring: 'ring-rose-500/40'    },
  { id: 4, label: 'Honeypot Triggered',   icon: Flame,       color: 'text-red-400',     bg: 'bg-red-600',     ring: 'ring-red-600/40'     },
  { id: 5, label: 'Quarantine Active',    icon: ShieldOff,   color: 'text-red-300',     bg: 'bg-red-700',     ring: 'ring-red-700/50'     },
]

export default function AttackTimeline({ activeStage = 0 }) {
  return (
    <div
      className="rounded-xl border border-slate-800/80 overflow-hidden"
      style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
    >
      <div className="px-5 py-4 border-b border-slate-800/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Flame className="w-4 h-4 text-orange-400" />
          <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Attack Progression</h3>
        </div>
        <span className="text-xs font-mono text-slate-500">
          Stage {activeStage + 1} / {STAGES.length}
        </span>
      </div>

      <div className="px-5 py-5">
        <div className="flex items-center gap-0">
          {STAGES.map((stage, i) => {
            const Icon = stage.icon
            const isActive  = i === activeStage
            const isPast    = i < activeStage
            const isFuture  = i > activeStage

            return (
              <React.Fragment key={stage.id}>
                {/* node */}
                <div className="flex flex-col items-center gap-2 shrink-0">
                  <motion.div
                    className={`
                      w-8 h-8 rounded-full flex items-center justify-center ring-2
                      ${isActive ? `${stage.bg} ${stage.ring} ring-offset-2 ring-offset-[#0a0f1e]` : ''}
                      ${isPast   ? 'bg-slate-700 ring-slate-600/30' : ''}
                      ${isFuture ? 'bg-slate-800/60 ring-slate-700/20' : ''}
                    `}
                    animate={isActive ? { scale: [1, 1.1, 1] } : { scale: 1 }}
                    transition={{ duration: 1.5, repeat: isActive ? Infinity : 0, ease: 'easeInOut' }}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-white' : isPast ? 'text-slate-400' : 'text-slate-600'}`} />
                  </motion.div>

                  <span className={`text-[10px] font-mono text-center leading-tight w-14
                    ${isActive ? stage.color : isPast ? 'text-slate-400' : 'text-slate-700'}
                  `}>
                    {stage.label}
                  </span>
                </div>

                {/* connector line */}
                {i < STAGES.length - 1 && (
                  <div className="flex-1 h-px mx-1 relative overflow-hidden" style={{ marginBottom: '20px' }}>
                    <div className="absolute inset-0 bg-slate-800" />
                    {isPast && (
                      <motion.div
                        className="absolute inset-0 bg-gradient-to-r from-slate-500 to-slate-400"
                        initial={{ scaleX: 0, originX: 0 }}
                        animate={{ scaleX: 1 }}
                        transition={{ duration: 0.4, delay: i * 0.1 }}
                      />
                    )}
                    {isActive && (
                      <motion.div
                        className={`absolute inset-0 ${stage.bg}`}
                        animate={{ opacity: [0.3, 0.8, 0.3] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      />
                    )}
                  </div>
                )}
              </React.Fragment>
            )
          })}
        </div>
      </div>
    </div>
  )
}
