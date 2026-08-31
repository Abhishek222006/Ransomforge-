import React from 'react'
import { motion } from 'framer-motion'
import { HardDrive, Database, ShieldAlert, ShieldCheck, AlertTriangle } from 'lucide-react'

const STATUS_CFG = {
  triggered: { text: 'text-red-400',    badge: 'bg-red-900/40 border-red-700/50 text-red-300',    icon: ShieldAlert  },
  modified:  { text: 'text-orange-400', badge: 'bg-orange-900/30 border-orange-700/40 text-orange-300', icon: AlertTriangle },
  clean:     { text: 'text-emerald-400',badge: 'bg-emerald-900/20 border-emerald-700/30 text-emerald-300', icon: ShieldCheck },
}

const TYPE_ICON = {
  honeypot:  HardDrive,
  protected: Database,
}

function AssetRow({ asset }) {
  const s    = STATUS_CFG[asset.status] || STATUS_CFG.clean
  const Icon = TYPE_ICON[asset.type] || Database
  const StatusIcon = s.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 px-4 py-3 rounded-lg border border-slate-800/50 hover:bg-slate-800/20 transition-colors"
      style={{ background: 'rgba(10,15,30,0.5)' }}
    >
      <Icon className={`w-4 h-4 shrink-0 ${s.text}`} />

      <div className="flex-1 min-w-0">
        <div className="text-slate-200 text-sm font-mono truncate">{asset.name}</div>
        <div className="text-slate-500 text-xs truncate">{asset.path}</div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-slate-500 capitalize hidden sm:inline">{asset.type}</span>
        <span className={`flex items-center gap-1 text-[10px] font-bold tracking-widest px-2 py-0.5 rounded border ${s.badge} uppercase`}>
          <StatusIcon className="w-3 h-3" />
          {asset.status}
        </span>
      </div>
    </motion.div>
  )
}

export default function AssetsPanel({ assets = [] }) {
  const triggered = assets.filter(a => a.status === 'triggered').length
  const modified  = assets.filter(a => a.status === 'modified').length

  return (
    <div
      className="rounded-xl border border-slate-800/80 overflow-hidden"
      style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
    >
      <div className="px-5 py-4 border-b border-slate-800/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-400" />
          <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Monitored Assets</h3>
        </div>
        <div className="flex items-center gap-2">
          {triggered > 0 && (
            <span className="text-xs bg-red-900/40 border border-red-700/50 text-red-300 px-2 py-0.5 rounded-full font-mono">
              {triggered} triggered
            </span>
          )}
          {modified > 0 && (
            <span className="text-xs bg-orange-900/30 border border-orange-700/40 text-orange-300 px-2 py-0.5 rounded-full font-mono">
              {modified} modified
            </span>
          )}
        </div>
      </div>

      <div className="p-3 space-y-2">
        {assets.length === 0 ? (
          <div className="py-8 text-center text-slate-600 text-sm">Loading assets…</div>
        ) : (
          assets.map((a) => <AssetRow key={a.id} asset={a} />)
        )}
      </div>
    </div>
  )
}
