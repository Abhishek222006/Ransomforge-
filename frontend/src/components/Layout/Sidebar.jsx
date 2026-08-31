import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, ShieldAlert, Radio, Database, Settings, Shield, RotateCcw } from 'lucide-react'

const NAV = [
  { label: 'Overview',   to: '/',          icon: LayoutDashboard, exact: true },
  { label: 'Alerts',     to: '/alerts',    icon: ShieldAlert,     danger: true },
  { label: 'Live Feed',  to: '/live',      icon: Radio },
  { label: 'Assets',     to: '/assets',    icon: Database },
  { label: 'Recovery',   to: '/recovery',  icon: RotateCcw },
  { label: 'Settings',   to: '/settings',  icon: Settings },
]

export default function Sidebar({ collapsed }) {
  return (
    <aside
      className={`fixed top-14 left-0 bottom-0 z-40 w-64 transform transition-transform duration-200 ease-in-out border-r
        ${collapsed ? '-translate-x-full' : 'translate-x-0'}
        border-slate-800/80`}
      style={{ background: 'linear-gradient(180deg, #080d1a 0%, #0a1020 100%)' }}
    >
      {/* brand */}
      <div className="px-4 py-5 flex items-center gap-3 border-b border-slate-800/60">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-rose-600 to-violet-700 flex items-center justify-center shadow-lg">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="text-slate-100 font-bold text-sm tracking-wide">RansomForge</div>
          <div className="text-slate-500 text-xs font-mono">SOC · v1.0</div>
        </div>
      </div>

      {/* nav */}
      <nav className="p-3 space-y-0.5">
        {NAV.map(({ label, to, icon: Icon, danger, exact }) => (
          <NavLink
            key={label}
            to={to}
            end={exact}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors
              ${isActive ? 'bg-blue-600/20 text-blue-300 border border-blue-600/30' : ''}
              ${!isActive && danger ? 'text-rose-400 hover:bg-rose-900/20' : ''}
              ${!isActive && !danger ? 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200' : ''}
            `}
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span>{label}</span>
            {danger && (
              <span className="ml-auto w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
            )}
          </NavLink>
        ))}
      </nav>

      {/* bottom status */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-800/60">
        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Detection engine active
        </div>
      </div>
    </aside>
  )
}
