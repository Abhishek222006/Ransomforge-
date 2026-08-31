import React from 'react'
import { Menu, Search, Bell, User, Wifi, WifiOff, Loader } from 'lucide-react'
import { motion } from 'framer-motion'

function StatusPill({ status }) {
  if (status === 'connected')
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/60 border border-emerald-800/40">
        <Wifi className="w-3 h-3 text-emerald-400" />
        <span className="text-emerald-400 text-xs font-mono">LIVE</span>
      </div>
    )
  if (status === 'reconnecting')
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-yellow-950/60 border border-yellow-800/40">
        <Loader className="w-3 h-3 text-yellow-400 animate-spin" />
        <span className="text-yellow-400 text-xs font-mono">RECONNECTING</span>
      </div>
    )
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-950/60 border border-rose-800/40">
      <WifiOff className="w-3 h-3 text-rose-400" />
      <span className="text-rose-400 text-xs font-mono">OFFLINE</span>
    </div>
  )
}

export default function Navbar({ onToggleSidebar, status = 'connecting' }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="fixed top-0 left-0 right-0 z-50 h-14 border-b border-slate-800/80 px-4 flex items-center gap-4"
      style={{ background: 'rgba(8, 13, 26, 0.85)', backdropFilter: 'blur(12px)' }}
    >
      <button
        aria-label="Toggle sidebar"
        onClick={onToggleSidebar}
        className="p-2 rounded-lg hover:bg-slate-800/60 transition-colors text-slate-400 hover:text-slate-200"
      >
        <Menu className="w-5 h-5" />
      </button>

      <div className="flex items-center gap-2 bg-slate-800/40 border border-slate-700/40 rounded-lg px-3 py-1.5 flex-1 max-w-lg">
        <Search className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        <input
          placeholder="Search events, hashes, hosts…"
          className="bg-transparent outline-none placeholder:text-slate-600 text-slate-300 text-sm w-full"
        />
      </div>

      <div className="ml-auto flex items-center gap-3">
        <StatusPill status={status} />

        <button className="relative p-2 rounded-lg hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute -top-0.5 -right-0.5 text-[10px] bg-rose-500 text-white rounded-full w-4 h-4 flex items-center justify-center font-bold">3</span>
        </button>

        <button className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 transition-colors">
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center">
            <User className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-sm text-slate-300 hidden sm:inline">Analyst</span>
        </button>
      </div>
    </motion.header>
  )
}
