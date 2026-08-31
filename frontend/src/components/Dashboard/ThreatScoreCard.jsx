import React, { useMemo, useRef, useEffect } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { ShieldAlert, ShieldCheck, Shield, TrendingUp, TrendingDown, Minus } from 'lucide-react'

// ── severity config ───────────────────────────────────────────────────────────
function getSeverity(score) {
  if (score >= 90) return { label: 'CRITICAL',  color: '#ef4444', glow: 'rgba(239,68,68,0.35)',  ring: 'border-red-500/60',    text: 'text-red-400',    bg: 'bg-red-950/40',    trackColor: '#1f0000' }
  if (score >= 75) return { label: 'HIGH',       color: '#f97316', glow: 'rgba(249,115,22,0.30)', ring: 'border-orange-500/50', text: 'text-orange-400', bg: 'bg-orange-950/30', trackColor: '#1c0a00' }
  if (score >= 50) return { label: 'ELEVATED',   color: '#eab308', glow: 'rgba(234,179,8,0.25)',  ring: 'border-yellow-500/40', text: 'text-yellow-400', bg: 'bg-yellow-950/20', trackColor: '#1a1400' }
  if (score >= 25) return { label: 'MODERATE',   color: '#3b82f6', glow: 'rgba(59,130,246,0.20)', ring: 'border-blue-500/40',   text: 'text-blue-400',   bg: 'bg-blue-950/20',   trackColor: '#00081a' }
  return              { label: 'NORMAL',     color: '#22c55e', glow: 'rgba(34,197,94,0.20)',  ring: 'border-emerald-500/40', text: 'text-emerald-400', bg: 'bg-emerald-950/20', trackColor: '#001a06' }
}

// ── SVG arc gauge ─────────────────────────────────────────────────────────────
const GAUGE_R   = 80
const GAUGE_CX  = 100
const GAUGE_CY  = 100
const START_DEG = 220
const SWEEP_DEG = 280

function polarToXY(cx, cy, r, deg) {
  const rad = ((deg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(cx, cy, r, startDeg, endDeg) {
  const start  = polarToXY(cx, cy, r, endDeg)
  const end    = polarToXY(cx, cy, r, startDeg)
  const large  = endDeg - startDeg > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 0 ${end.x} ${end.y}`
}

function ThreatGauge({ score, severity }) {
  const circumference = (SWEEP_DEG / 360) * (2 * Math.PI * GAUGE_R)
  const fraction      = Math.min(score / 100, 1)

  // track arc (background)
  const trackD = describeArc(GAUGE_CX, GAUGE_CY, GAUGE_R, START_DEG, START_DEG + SWEEP_DEG)

  // value arc end angle
  const endDeg  = START_DEG + SWEEP_DEG * fraction
  const valueD  = fraction > 0.005
    ? describeArc(GAUGE_CX, GAUGE_CY, GAUGE_R, START_DEG, endDeg)
    : ''

  // animated needle dot
  const dot = polarToXY(GAUGE_CX, GAUGE_CY, GAUGE_R, endDeg)

  return (
    <svg viewBox="0 0 200 175" className="w-full" style={{ maxHeight: 175 }}>
      <defs>
        <filter id="glowFilter" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3.5" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <linearGradient id="arcGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor={severity.color} stopOpacity="0.7" />
          <stop offset="100%" stopColor={severity.color} stopOpacity="1" />
        </linearGradient>
      </defs>

      {/* track */}
      <path d={trackD} fill="none" stroke={severity.trackColor} strokeWidth="12" strokeLinecap="round" />

      {/* value arc */}
      {valueD && (
        <motion.path
          d={valueD}
          fill="none"
          stroke={`url(#arcGrad)`}
          strokeWidth="12"
          strokeLinecap="round"
          filter="url(#glowFilter)"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: fraction }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      )}

      {/* needle dot */}
      {valueD && (
        <motion.circle
          cx={dot.x}
          cy={dot.y}
          r="7"
          fill={severity.color}
          filter="url(#glowFilter)"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.6, duration: 0.3 }}
        />
      )}

      {/* center text */}
      <text x={GAUGE_CX} y={GAUGE_CY - 2} textAnchor="middle" dominantBaseline="middle"
        fontSize="34" fontWeight="800" fill={severity.color} fontFamily="monospace">
        {score}
      </text>
      <text x={GAUGE_CX} y={GAUGE_CY + 26} textAnchor="middle" dominantBaseline="middle"
        fontSize="11" fill="#64748b" letterSpacing="2" fontFamily="monospace">
        /100
      </text>
    </svg>
  )
}

// ── trend indicator ───────────────────────────────────────────────────────────
function TrendBadge({ score, prevScore }) {
  const delta = score - prevScore
  if (Math.abs(delta) < 2) return <span className="flex items-center gap-1 text-slate-400 text-xs"><Minus className="w-3 h-3" />Stable</span>
  if (delta > 0) return <span className="flex items-center gap-1 text-rose-400 text-xs"><TrendingUp className="w-3 h-3" />+{delta} rising</span>
  return <span className="flex items-center gap-1 text-emerald-400 text-xs"><TrendingDown className="w-3 h-3" />{delta} falling</span>
}

// ── main component ────────────────────────────────────────────────────────────
export default function ThreatScoreCard({ score = 68 }) {
  const prevScoreRef = useRef(score)
  const prevScore    = prevScoreRef.current
  const sev          = getSeverity(score)
  const isCritical   = score >= 90

  useEffect(() => {
    const t = setTimeout(() => { prevScoreRef.current = score }, 800)
    return () => clearTimeout(t)
  }, [score])

  const ShieldIcon = isCritical ? ShieldAlert : score >= 50 ? Shield : ShieldCheck

  return (
    <motion.div
      layout
      className={`relative rounded-xl border ${sev.ring} overflow-hidden h-full flex flex-col`}
      style={{
        background: 'linear-gradient(135deg, #0b0f1a 0%, #0f172a 60%, #0b0f1a 100%)',
        boxShadow: `0 0 40px ${sev.glow}, 0 0 1px rgba(255,255,255,0.04) inset`,
      }}
      animate={{ boxShadow: isCritical
        ? [`0 0 40px ${sev.glow}`, `0 0 70px ${sev.glow}`, `0 0 40px ${sev.glow}`]
        : `0 0 40px ${sev.glow}`
      }}
      transition={{ duration: 1.4, repeat: isCritical ? Infinity : 0, ease: 'easeInOut' }}
    >
      {/* top header bar */}
      <div className={`px-5 pt-5 pb-2 flex items-center justify-between`}>
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <ShieldIcon className={`w-4 h-4 ${sev.text}`} />
            <span className="text-slate-300 text-sm font-semibold tracking-wide uppercase">Threat Score</span>
          </div>
          <p className="text-slate-500 text-xs">Real-time endpoint risk level</p>
        </div>

        <motion.div
          key={sev.label}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className={`px-3 py-1 rounded-full text-xs font-bold tracking-widest ${sev.text} ${sev.bg} border ${sev.ring}`}
        >
          {sev.label}
        </motion.div>
      </div>

      {/* gauge */}
      <div className="px-6 pt-1 pb-0 flex-1 flex items-center justify-center">
        <ThreatGauge score={score} severity={sev} />
      </div>

      {/* footer row */}
      <div className="px-5 pb-5 pt-1 flex items-center justify-between">
        <TrendBadge score={score} prevScore={prevScore} />

        {isCritical ? (
          <motion.div
            className="flex items-center gap-1.5 text-xs text-red-400 font-semibold"
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" />
            QUARANTINE READY
          </motion.div>
        ) : (
          <span className="text-slate-500 text-xs font-mono">Updated live</span>
        )}
      </div>

      {/* critical vignette overlay */}
      {isCritical && (
        <motion.div
          className="absolute inset-0 pointer-events-none rounded-xl"
          animate={{ opacity: [0, 0.08, 0] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
          style={{ background: 'radial-gradient(ellipse at center, rgba(239,68,68,0.3) 0%, transparent 70%)' }}
        />
      )}
    </motion.div>
  )
}
