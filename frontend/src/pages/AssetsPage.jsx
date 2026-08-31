import React from 'react'
import { Database, ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react'
import AssetsPanel from '../components/Dashboard/AssetsPanel'

export default function AssetsPage({ assets = [] }) {
  const triggered = assets.filter(a => a.status === 'triggered').length
  const modified  = assets.filter(a => a.status === 'modified').length
  const clean     = assets.filter(a => a.status === 'clean').length

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Database className="w-5 h-5 text-blue-400" />
            <h1 className="text-slate-100 font-bold text-xl">Monitored Assets & Honeypots</h1>
          </div>
          <p className="text-slate-500 text-sm">Realtime status of critical files and decoy assets</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="p-4 rounded-xl border border-slate-800/60 bg-slate-900/40 space-y-1">
          <div className="flex items-center gap-2 text-slate-400 text-sm">
            <ShieldCheck className="w-4 h-4 text-emerald-400" /> Clean
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">{clean}</div>
        </div>
        <div className="p-4 rounded-xl border border-slate-800/60 bg-slate-900/40 space-y-1">
          <div className="flex items-center gap-2 text-slate-400 text-sm">
            <AlertTriangle className="w-4 h-4 text-orange-400" /> Modified
          </div>
          <div className="text-2xl font-bold font-mono text-orange-400">{modified}</div>
        </div>
        <div className="p-4 rounded-xl border border-slate-800/60 bg-slate-900/40 space-y-1">
          <div className="flex items-center gap-2 text-slate-400 text-sm">
            <ShieldAlert className="w-4 h-4 text-red-400" /> Triggered
          </div>
          <div className="text-2xl font-bold font-mono text-red-400">{triggered}</div>
        </div>
      </div>

      <AssetsPanel assets={assets} />
    </div>
  )
}
