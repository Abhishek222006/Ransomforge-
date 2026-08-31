import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Shield, FileSearch, AlertTriangle, CheckCircle, Loader } from 'lucide-react'

function ProgressBar({ pct, threats }) {
  const color = threats > 3 ? 'bg-rose-500' : threats > 0 ? 'bg-orange-500' : 'bg-blue-500'
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs font-mono text-slate-400">
        <span>{pct.toFixed(1)}%</span>
        <span className={threats > 0 ? 'text-rose-400' : 'text-slate-500'}>
          {threats} threat{threats !== 1 ? 's' : ''} found
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
          transition={{ duration: 0.2 }}
        />
      </div>
    </div>
  )
}

export default function ScanModal({ scan, onClose }) {
  if (!scan) return null

  const isDone = scan.phase === 'completed'
  const isRunning = scan.phase === 'running'

  return (
    <AnimatePresence>
      {scan && (
        <motion.div
          className="fixed inset-0 z-[200] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={isDone ? onClose : undefined}
          />

          <motion.div
            className="relative w-full max-w-lg rounded-2xl border border-slate-700/60 overflow-hidden z-10"
            style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0d1428 100%)' }}
            initial={{ scale: 0.95, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 20 }}
            transition={{ duration: 0.25 }}
          >
            {/* header */}
            <div className="px-6 py-5 border-b border-slate-800/60 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {isRunning ? (
                  <Loader className="w-5 h-5 text-blue-400 animate-spin" />
                ) : isDone ? (
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                ) : (
                  <FileSearch className="w-5 h-5 text-blue-400" />
                )}
                <div>
                  <div className="text-slate-200 font-semibold text-sm">
                    {isRunning ? 'Scanning System…' : isDone ? 'Scan Complete' : 'Initialising Scan'}
                  </div>
                  <div className="text-slate-500 text-xs font-mono">
                    {isRunning
                      ? `${scan.scanned?.toLocaleString()} / ${scan.total?.toLocaleString()} files`
                      : isDone
                      ? `${scan.scanned?.toLocaleString()} files scanned`
                      : 'Preparing…'}
                  </div>
                </div>
              </div>
              {isDone && (
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* body */}
            <div className="px-6 py-5 space-y-5">
              {(isRunning || isDone) && (
                <ProgressBar pct={scan.percent || 0} threats={scan.threats_found || 0} />
              )}

              {isDone && (
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Files Scanned', value: scan.scanned?.toLocaleString(), icon: FileSearch, color: 'text-blue-400' },
                    { label: 'Threats Found', value: scan.threats_found,             icon: AlertTriangle, color: scan.threats_found > 0 ? 'text-rose-400' : 'text-emerald-400' },
                    { label: 'Threat Score',  value: scan.threat_score,              icon: Shield,        color: scan.threat_score > 70 ? 'text-rose-400' : 'text-amber-400' },
                  ].map(({ label, value, icon: Icon, color }) => (
                    <div key={label} className="p-3 rounded-lg border border-slate-800/60 bg-slate-900/40 text-center space-y-1">
                      <Icon className={`w-4 h-4 mx-auto ${color}`} />
                      <div className={`text-xl font-bold font-mono ${color}`}>{value}</div>
                      <div className="text-slate-500 text-xs">{label}</div>
                    </div>
                  ))}
                </div>
              )}

              {isDone && (
                <div
                  className={`flex items-center gap-2 px-4 py-3 rounded-lg border text-sm
                    ${scan.threats_found > 0
                      ? 'border-rose-700/40 bg-rose-950/30 text-rose-300'
                      : 'border-emerald-700/40 bg-emerald-950/30 text-emerald-300'
                    }`}
                >
                  {scan.threats_found > 0
                    ? <AlertTriangle className="w-4 h-4 shrink-0" />
                    : <CheckCircle className="w-4 h-4 shrink-0" />
                  }
                  {scan.threats_found > 0
                    ? `${scan.threats_found} threat(s) detected. Quarantine recommended.`
                    : 'No threats detected. System appears clean.'}
                </div>
              )}
            </div>

            {isDone && (
              <div className="px-6 pb-5">
                <button
                  onClick={onClose}
                  className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition-colors"
                >
                  Close Report
                </button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
