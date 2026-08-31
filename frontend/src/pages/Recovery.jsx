import React, { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Database, History, RefreshCcw, ShieldCheck, AlertCircle, Clock,
  ArrowUpRight, Download, CheckCircle2, ShieldAlert, Loader,
  Trash2, Search, Filter, Calendar, Activity, Server, FileText, ChevronRight,
  Zap, Info, CheckCircle, XCircle
} from 'lucide-react'
import { api } from '../services/api'
import { listen } from '../services/socket'

// ── Components ───────────────────────────────────────────────────────────────

function RecoveryMetricCard({ label, value, icon: Icon, color, delay, loading }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="p-4 rounded-xl border border-slate-800/60 flex items-center gap-4 group hover:border-slate-700/80 transition-all cursor-default"
      style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
    >
      <div className={`p-2.5 rounded-lg border border-slate-700/50 ${color} bg-slate-900/50 group-hover:scale-110 transition-transform`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <div className="text-slate-500 text-xs font-mono uppercase tracking-wider">{label}</div>
        {loading ? (
          <div className="h-6 w-16 bg-slate-800/50 animate-pulse rounded mt-1" />
        ) : (
          <div className="text-slate-200 font-bold text-lg mt-0.5">{value}</div>
        )}
      </div>
    </motion.div>
  )
}

function RestoreModal({ backup, isOpen, onClose, onConfirm, loading }) {
  if (!isOpen) return null
  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        />
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="relative w-full max-w-md rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-2xl"
        >
          <div className="flex items-center gap-3 text-amber-400 mb-4">
            <ShieldAlert className="w-6 h-6" />
            <h3 className="text-lg font-bold">Confirm System Restore</h3>
          </div>
          <p className="text-slate-400 text-sm leading-relaxed mb-6">
            You are about to restore snapshot <span className="text-slate-200 font-mono text-xs bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">#{String(backup?.id ?? "").substring(0, 8)}</span>.
            This will overwrite current system files with the selected backup state. This action cannot be undone.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2.5 rounded-lg border border-slate-800 text-slate-400 text-sm font-medium hover:bg-slate-900 hover:text-slate-200 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={() => onConfirm(backup.id)}
              disabled={loading}
              className="px-4 py-2.5 rounded-lg bg-amber-600/20 border border-amber-600/30 text-amber-300 text-sm font-medium hover:bg-amber-600/30 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? <Loader className="w-4 h-4 animate-spin" /> : <RefreshCcw className="w-4 h-4" />}
              Begin Restore
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

function LogsModal({ isOpen, onClose, logs, loading }) {
  const [search, setSearch] = useState('')
  if (!isOpen) return null

  const filteredLogs = logs.filter(log =>
    String(log.event_type || "").toLowerCase().includes(search.toLowerCase()) ||
    String(log.message || "").toLowerCase().includes(search.toLowerCase())
  )

  const renderSafe = (val) => {
    if (typeof val === 'string') return val;
    if (typeof val === 'number') return String(val);
    if (!val) return '';
    if (typeof val === 'object') {
      return val.message || val.raw || JSON.stringify(val);
    }
    return String(val);
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        />
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="relative w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-2xl flex flex-col max-h-[80vh]"
        >
          <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3 shrink-0">
            <div className="flex items-center gap-3 text-violet-400">
              <Clock className="w-5 h-5" />
              <h3 className="text-lg font-bold text-slate-100">System Recovery Logs</h3>
            </div>
            <button 
              onClick={onClose} 
              className="p-1 rounded-lg border border-slate-800 hover:bg-slate-900 text-slate-400 transition-colors"
            >
              <XCircle className="w-5 h-5 text-slate-500 hover:text-rose-400" />
            </button>
          </div>

          <div className="mb-4 shrink-0">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search logs by type or message..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-800 rounded-lg py-2 pl-10 pr-4 text-sm text-slate-300 focus:outline-none focus:border-violet-600/50 transition-colors font-mono"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto pr-1 space-y-3 min-h-[200px]">
            {loading ? (
              [...Array(4)].map((_, i) => (
                <div key={i} className="flex gap-4 animate-pulse p-3.5 border border-slate-900 rounded-xl">
                  <div className="h-8 w-8 rounded-full bg-slate-800" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-slate-800 rounded w-1/4" />
                    <div className="h-3 bg-slate-800 rounded w-3/4" />
                  </div>
                </div>
              ))
            ) : filteredLogs.length === 0 ? (
              <div className="flex flex-col items-center justify-center text-slate-600 py-16 gap-3">
                <Clock className="w-12 h-12 opacity-20" />
                <p className="text-sm font-mono uppercase tracking-widest">No recovery events found</p>
              </div>
            ) : (
              filteredLogs.map((log, idx) => {
                const isSuccess = log.status === 'success' || log.status === 'clean'
                return (
                  <div key={log.id || idx} className="p-3.5 rounded-xl border border-slate-900 bg-slate-900/20 hover:border-slate-800/80 transition-all flex items-start gap-4 group">
                    <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-slate-800 bg-slate-950 shadow group-hover:scale-105 transition-transform`}>
                      {log.event_type?.includes('restore') ? <Activity className="w-3.5 h-3.5 text-amber-400" /> : <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-4 mb-1">
                        <div className="text-slate-200 font-bold text-xs tracking-wide font-mono uppercase truncate">
                          {log.event_type?.replace(/_/g, ' ') || 'SYSTEM EVENT'}
                        </div>
                        <div className="text-slate-500 text-[10px] font-mono shrink-0">
                          {new Date(log.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <p className="text-slate-400 text-xs leading-relaxed mb-2 font-medium break-words">
                        {log.message || renderSafe(log.details) || 'Integrity verified and logged.'}
                      </p>
                      <span className={`inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded border ${
                        isSuccess ? 'text-emerald-400 bg-emerald-400/5 border-emerald-500/20' : 'text-rose-400 bg-rose-400/5 border-rose-500/20'
                      }`}>
                        {isSuccess ? <CheckCircle2 className="w-2.5 h-2.5" /> : <AlertCircle className="w-2.5 h-2.5" />}
                        {log.status || 'Verified'}
                      </span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function Recovery() {
  const [backups, setBackups] = useState([])
  const [stats, setStats] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [opLoading, setOpLoading] = useState({ create: false, restore: false, emergency: false, latest: false })
  const [selectedBackup, setSelectedBackup] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false)
  const [notification, setNotification] = useState(null)
  const [feed, setFeed] = useState([])
  const [searchQuery, setSearchQuery] = useState('')

  const triggerNotification = useCallback((title, message, type) => {
    setNotification({ title, message, type })
  }, [])

  // Auto-dismiss notification after 6s
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 6000)
      return () => clearTimeout(timer)
    }
  }, [notification])

  const formatDate = (isoStr) => {
    if (!isoStr) return '—'
    const d = new Date(isoStr)
    if (isNaN(d.getTime())) return '—'
    return d.toLocaleDateString()
  }

  const getRelativeTime = useCallback((isoStr) => {
    if (!isoStr || typeof isoStr !== 'string') return '—'
    const d = new Date(isoStr)
    if (isNaN(d.getTime())) return '—'
    const diff = Date.now() - d.getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    return formatDate(isoStr)
  }, [])

  const fetchAllData = useCallback(async () => {
    try {
      const [backupsData, statsData, logsData] = await Promise.all([
        api.listBackups(),
        api.getRecoveryStats(),
        api.getRecoveryLogs()
      ])
      setBackups(Array.isArray(backupsData.backups) ? backupsData.backups : [])
      setStats(statsData)
      setLogs(Array.isArray(logsData.logs) ? logsData.logs : [])

      if (Array.isArray(logsData.logs)) {
        const initialFeed = logsData.logs.map(log => {
          let logType = 'event'
          if (log.event_type) {
            logType = log.event_type.replace('snapshot_', '').replace('_failed', '')
          }
          return {
            id: log.id || Math.random(),
            type: logType,
            message: log.message || (typeof log.details === 'object' ? log.details?.message : log.details) || 'Recovery action logged.',
            time: getRelativeTime(log.timestamp),
            status: log.status === 'failed' ? 'critical' : (log.event_type?.includes('restore') ? 'warning' : 'success')
          }
        })
        setFeed(initialFeed.slice(0, 20))
      }
    } catch (err) {
      console.error('Failed to fetch recovery data:', err)
    } finally {
      setLoading(false)
    }
  }, [getRelativeTime])

  useEffect(() => {
    fetchAllData()

    const unlisten = listen((msg) => {
      if (['RECOVERY_CREATED', 'RECOVERY_RESTORED', 'RECOVERY_FAILED'].includes(msg.type)) {
        fetchAllData()
        const payload = msg.payload || msg.data || {}
        setFeed(prev => {
          const messageText = payload.message || 'Recovery event received'
          return [{
            id: Date.now() + Math.random(),
            type: msg.type.split('_')[1].toLowerCase(),
            message: messageText,
            time: 'Just now',
            status: msg.type === 'RECOVERY_FAILED' ? 'critical' : (msg.type === 'RECOVERY_RESTORED' ? 'warning' : 'success')
          }, ...prev].slice(0, 20)
        })
      }
    })

    return () => unlisten()
  }, [fetchAllData])

  const handleCreateSnapshot = async () => {
    setOpLoading(prev => ({ ...prev, create: true }))
    try {
      await api.createBackup()
      triggerNotification('Snapshot Created', 'A new clean system snapshot has been stored successfully.', 'success')
      await fetchAllData()
    } catch (err) {
      console.error('Snapshot creation failed:', err)
      triggerNotification('Snapshot Failed', err.message || 'Unable to create system snapshot.', 'error')
    } finally {
      setOpLoading(prev => ({ ...prev, create: false }))
    }
  }

  const handleRestore = async (id) => {
    setOpLoading(prev => ({ ...prev, restore: true }))
    try {
      await api.restoreBackup(id)
      setIsModalOpen(false)
      triggerNotification('System Restored', `Snapshot #${String(id).substring(0, 8)} restored successfully.`, 'success')
      await fetchAllData()
    } catch (err) {
      console.error('Restore failed:', err)
      triggerNotification('Restore Failed', err.message || 'Unable to restore system state.', 'error')
    } finally {
      setOpLoading(prev => ({ ...prev, restore: false }))
    }
  }

  const handleRestoreLatest = async () => {
    setOpLoading(prev => ({ ...prev, latest: true }))
    try {
      await api.restoreLatest()
      triggerNotification('Latest Restored', 'Latest clean snapshot restored successfully.', 'success')
      await fetchAllData()
    } catch (err) {
      console.error('Restore latest failed:', err)
      triggerNotification('Restore Failed', err.message || 'Unable to restore latest snapshot.', 'error')
    } finally {
      setOpLoading(prev => ({ ...prev, latest: false }))
    }
  }

  const handleEmergencyBoot = async () => {
    if (!confirm("EMERGENCY RECOVERY: This will perform an immediate restoration to the last clean state and reset system security flags. Continue?")) return
    
    setOpLoading(prev => ({ ...prev, emergency: true }))
    try {
      await api.emergencyBoot()
      triggerNotification('Emergency Recovery Active', 'System restored to last clean state and risk score reset.', 'success')
      await fetchAllData()
    } catch (err) {
      console.error('Emergency boot failed:', err)
      triggerNotification('Recovery Failed', err.message || 'Emergency recovery could not be completed.', 'error')
    } finally {
      setOpLoading(prev => ({ ...prev, emergency: false }))
    }
  }

  const handleGenerateReport = async () => {
    setOpLoading(prev => ({ ...prev, report: true }))
    try {
      const blob = await api.generateReport()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_').split('-Z')[0]
      a.download = `ransomforge_incident_report_${timestamp}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      triggerNotification('Report Generated', 'Incident report generated successfully', 'success')
      
      setFeed(prev => [{
        id: Date.now() + Math.random(),
        type: 'report',
        message: 'Incident report generated',
        time: 'Just now',
        status: 'success'
      }, ...prev].slice(0, 20))

    } catch (err) {
      console.error('Report generation failed:', err)
      triggerNotification('Report Failed', err.message || 'Unable to generate incident report.', 'error')
    } finally {
      setOpLoading(prev => ({ ...prev, report: false }))
    }
  }

  const openRestoreModal = (backup) => {
    setSelectedBackup(backup)
    setIsModalOpen(true)
  }

  const formatSize = (bytes) => {
    if (!bytes || isNaN(bytes)) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatTime = (isoStr) => {
    if (!isoStr) return '—'
    const d = new Date(isoStr)
    if (isNaN(d.getTime())) return '—'
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const renderSafe = (val) => {
    if (typeof val === 'string') return val;
    if (typeof val === 'number') return String(val);
    if (!val) return '';
    if (typeof val === 'object') {
      return val.message || val.raw || JSON.stringify(val);
    }
    return String(val);
  };

  const filteredBackups = backups.filter(b => 
    String(b.id || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
    String(b.status || "").toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto">
      
      {/* ── 1. HERO RECOVERY STATUS CARD ────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative overflow-hidden rounded-2xl border border-slate-800/80 p-8 shadow-2xl"
        style={{ background: 'linear-gradient(135deg, #0a0f1e 0%, #0d1428 100%)' }}
      >
        {/* Animated background glow */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/10 rounded-full blur-[100px] -mr-48 -mt-48 pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-emerald-600/5 rounded-full blur-[80px] -ml-32 -mb-32 pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-blue-600/20 border border-blue-600/30 text-blue-400">
                <Database className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Recovery Center</h1>
                <p className="text-emerald-400 text-xs font-mono flex items-center gap-1.5 uppercase tracking-widest mt-0.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  System Recovery Ready
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 pt-2">
              <div className="space-y-1">
                <div className="text-slate-500 text-[10px] font-mono uppercase tracking-tighter">Backup Health</div>
                <div className="text-xl font-bold text-slate-200">
                  {loading ? '---' : `${stats?.backup_health ?? 0}%`}
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-slate-500 text-[10px] font-mono uppercase tracking-tighter">Last Snapshot</div>
                <div className="text-xl font-bold text-slate-200">
                  {loading ? '---' : getRelativeTime(stats?.last_snapshot)}
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-slate-500 text-[10px] font-mono uppercase tracking-tighter">Total Assets</div>
                <div className="text-xl font-bold text-slate-200">
                  {loading ? '---' : (stats?.total_assets ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-slate-500 text-[10px] font-mono uppercase tracking-tighter">Ransomware Immunity</div>
                <div className={`text-xl font-bold ${stats?.ransomware_immunity === 'ACTIVE' ? 'text-emerald-400' : 'text-slate-500'}`}>
                  {loading ? '---' : stats?.ransomware_immunity ?? 'INACTIVE'}
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleCreateSnapshot}
              disabled={opLoading.create}
              className="px-6 py-3 rounded-xl bg-blue-600 text-white font-semibold text-sm shadow-lg shadow-blue-600/20 flex items-center gap-2 hover:bg-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {opLoading.create ? <Loader className="w-4 h-4 animate-spin" /> : <ArrowUpRight className="w-4 h-4" />}
              Create System Snapshot
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setIsLogsModalOpen(true)}
              className="px-6 py-3 rounded-xl border border-slate-700 bg-slate-900/40 text-slate-300 font-semibold text-sm hover:bg-slate-800 transition-all flex items-center gap-2"
            >
              <History className="w-4 h-4" />
              Recovery Logs
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleGenerateReport}
              disabled={opLoading.report}
              className="px-6 py-3 rounded-xl border border-violet-700/50 bg-violet-600/10 text-violet-300 font-semibold text-sm hover:bg-violet-600/20 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {opLoading.report ? <Loader className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
              {opLoading.report ? "Generating Report..." : "Incident Report"}
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* ── 5. RECOVERY METRICS ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <RecoveryMetricCard 
          label="Total Snapshots" 
          value={stats?.total_snapshots ?? 0} 
          icon={Database} 
          color="text-blue-400"
          delay={0.1}
          loading={loading}
        />
        <RecoveryMetricCard 
          label="Successful Restores" 
          value={stats?.successful_restores ?? 0} 
          icon={CheckCircle2} 
          color="text-emerald-400"
          delay={0.2}
          loading={loading}
        />
        <RecoveryMetricCard 
          label="Failed Restores" 
          value={stats?.failed_restores ?? 0} 
          icon={ShieldAlert} 
          color="text-rose-400"
          delay={0.3}
          loading={loading}
        />
        <RecoveryMetricCard 
          label="Protected Assets" 
          value={stats?.total_assets ?? 0} 
          icon={ShieldCheck} 
          color="text-violet-400"
          delay={0.4}
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <div className="lg:col-span-2 space-y-6">
          {/* ── 3. BACKUP SNAPSHOT TABLE ────────────────────────────────────────── */}
          <section className="rounded-xl border border-slate-800/80 overflow-hidden" style={{ background: '#080d1a' }}>
            <div className="px-5 py-4 border-b border-slate-800/60 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <History className="w-4 h-4 text-blue-400" />
                <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Backup History</h3>
              </div>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                  <input 
                    type="text" 
                    placeholder="Search snapshots..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-slate-900/50 border border-slate-800 rounded-lg py-1.5 pl-8 pr-3 text-xs text-slate-300 focus:outline-none focus:border-blue-600/50 transition-colors w-48"
                  />
                </div>
                <button className="p-1.5 rounded-lg border border-slate-800 hover:bg-slate-900 text-slate-500 transition-colors">
                  <Filter className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="overflow-x-auto min-h-[300px]">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800/40 text-[10px] font-mono text-slate-500 uppercase tracking-widest bg-slate-900/20">
                    <th className="px-5 py-4 font-medium">Snapshot ID</th>
                    <th className="px-5 py-4 font-medium">Timestamp</th>
                    <th className="px-5 py-4 font-medium text-center">Assets</th>
                    <th className="px-5 py-4 font-medium text-center">Size</th>
                    <th className="px-5 py-4 font-medium">Status</th>
                    <th className="px-5 py-4 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/30">
                  {loading ? (
                    [...Array(5)].map((_, i) => (
                      <tr key={i} className="animate-pulse">
                        <td colSpan="6" className="px-5 py-4"><div className="h-4 bg-slate-800/40 rounded w-full" /></td>
                      </tr>
                    ))
                  ) : filteredBackups.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="px-5 py-16 text-center text-slate-600">
                        <div className="flex flex-col items-center gap-2">
                          <Database className="w-8 h-8 opacity-20" />
                          <p className="text-sm font-medium">No system snapshots found</p>
                          <p className="text-xs">Create your first backup to enable recovery protection</p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredBackups.map((b) => (
                      <tr key={b.id} className="hover:bg-blue-600/5 transition-colors group">
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-2">
                            <span className="text-slate-300 font-mono text-xs">{String(b.id).substring(0, 8)}</span>
                            <div className={`w-1.5 h-1.5 rounded-full ${b.status === 'clean' ? 'bg-blue-500' : 'bg-rose-500'}`} />
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="text-slate-300 text-xs font-medium">
                            {formatDate(b.timestamp)}
                          </div>
                          <div className="text-slate-500 text-[10px] font-mono mt-0.5">
                            {formatTime(b.timestamp)}
                          </div>
                        </td>
                        <td className="px-5 py-4 text-center">
                          <span className="text-slate-400 text-xs font-mono">{b.file_count?.toLocaleString()}</span>
                        </td>
                        <td className="px-5 py-4 text-center">
                          <span className="text-slate-400 text-xs font-mono">{formatSize(b.size_bytes)}</span>
                        </td>
                        <td className="px-5 py-4">
                          <span className={`text-[10px] font-bold tracking-widest px-2 py-0.5 rounded border uppercase ${
                            b.status === 'clean' ? 'bg-emerald-900/20 border-emerald-700/30 text-emerald-400' : 
                            b.status === 'restored' ? 'bg-blue-900/20 border-blue-700/30 text-blue-400' :
                            'bg-rose-900/20 border-rose-700/30 text-rose-400'
                          }`}>
                            {b.status || 'CLEAN'}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-right">
                          <button 
                            onClick={() => openRestoreModal(b)}
                            disabled={opLoading.restore}
                            className="inline-flex items-center gap-1.5 text-[11px] font-bold text-blue-400 hover:text-blue-300 uppercase tracking-wider transition-colors disabled:opacity-40"
                          >
                            Restore <RefreshCcw className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* ── 2. RECOVERY LOGS ────────────────────────────────────────────── */}
          <section className="rounded-xl border border-slate-800/80 p-6" style={{ background: '#080d1a' }}>
            <div className="flex items-center gap-3 mb-8">
              <Clock className="w-4 h-4 text-violet-400" />
              <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Recovery Events</h3>
            </div>
            
            <div className="relative space-y-8 before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-blue-600/50 before:via-violet-600/50 before:to-transparent">
              {loading ? (
                [...Array(3)].map((_, i) => (
                  <div key={i} className="flex gap-8 animate-pulse">
                    <div className="h-10 w-10 rounded-full bg-slate-800" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-slate-800 rounded w-1/4" />
                      <div className="h-3 bg-slate-800 rounded w-3/4" />
                    </div>
                  </div>
                ))
              ) : logs.length === 0 ? (
                <div className="text-slate-500 text-xs italic pl-14">No recovery logs recorded.</div>
              ) : (
                logs.slice(0, 5).map((log, idx) => (
                  <div key={log.id || idx} className="relative flex items-start gap-8 group">
                    <div className={`mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-800 bg-slate-950 shadow-lg group-hover:scale-110 transition-transform ${idx === 0 ? 'ring-2 ring-blue-600/30 ring-offset-2 ring-offset-slate-950' : ''}`}>
                      {log.event_type?.includes('restore') ? <Activity className="w-4 h-4 text-amber-400" /> : <ShieldCheck className="w-4 h-4 text-blue-400" />}
                    </div>
                    <div className="flex-1 pb-2">
                      <div className="flex items-center justify-between mb-1">
                        <div className="text-slate-200 font-bold text-sm">
                          {log.event_type?.replace(/_/g, ' ').toUpperCase() || 'SYSTEM EVENT'}
                        </div>
                        <div className="text-slate-500 text-xs font-mono">{getRelativeTime(log.timestamp)}</div>
                      </div>
                      <p className="text-slate-400 text-xs mb-3 font-medium">
                        {log.message || renderSafe(log.details) || 'Integrity verified and logged.'}
                      </p>
                      <div className="flex items-center gap-2">
                        <span className={`flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded border ${
                          log.status === 'success' || log.status === 'clean' ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' : 'text-rose-400 bg-rose-400/10 border-rose-400/20'
                        }`}>
                          {log.status === 'success' || log.status === 'clean' ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                          {log.status || 'Verified'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          {/* ── 4. QUICK ACTION PANEL ────────────────────────────────────────────── */}
          <section 
            className="rounded-xl border border-slate-800/80 overflow-hidden flex flex-col"
            style={{ background: 'linear-gradient(160deg, #0a0f1e 0%, #0b1221 100%)' }}
          >
            <div className="px-5 py-4 border-b border-slate-800/60 flex items-center justify-between">
              <div>
                <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Rapid Recovery</h3>
                <p className="text-slate-500 text-[10px] mt-0.5 font-mono">One-click mitigation actions</p>
              </div>
            </div>
            
            <div className="p-4 space-y-3">
              <button 
                onClick={handleCreateSnapshot}
                disabled={opLoading.create}
                className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-800 bg-slate-900/40 hover:bg-slate-800 hover:border-slate-700 transition-all group disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-600/10 text-blue-400 group-hover:bg-blue-600/20 transition-colors">
                    <RefreshCcw className={`w-4 h-4 ${opLoading.create ? 'animate-spin' : ''}`} />
                  </div>
                  <div className="text-left">
                    <div className="text-slate-200 text-sm font-bold">New Snapshot</div>
                    <div className="text-slate-500 text-[10px]">Instant system state capture</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-300 transition-colors" />
              </button>

              <button 
                onClick={handleRestoreLatest}
                disabled={opLoading.latest || !stats?.last_snapshot}
                className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-800 bg-slate-900/40 hover:bg-emerald-950/20 hover:border-emerald-800/50 transition-all group disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-600/10 text-emerald-400 group-hover:bg-emerald-600/20 transition-colors">
                    {opLoading.latest ? <Loader className="w-4 h-4 animate-spin" /> : <History className="w-4 h-4" />}
                  </div>
                  <div className="text-left">
                    <div className="text-slate-200 text-sm font-bold">Restore Latest</div>
                    <div className="text-slate-500 text-[10px]">Jump to last known good state</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-emerald-400 transition-colors" />
              </button>

              <button 
                onClick={handleEmergencyBoot}
                disabled={opLoading.emergency}
                className="w-full flex items-center justify-between p-4 rounded-xl border border-rose-900/30 bg-rose-950/5 hover:bg-rose-950/20 hover:border-rose-800 transition-all group disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-rose-600/10 text-rose-400 group-hover:bg-rose-600/20 transition-colors">
                    {opLoading.emergency ? <Loader className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                  </div>
                  <div className="text-left">
                    <div className="text-slate-200 text-sm font-bold text-rose-400">Emergency Boot</div>
                    <div className="text-rose-900 text-[10px] font-bold uppercase tracking-widest">High Priority</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-rose-900 group-hover:text-rose-400 transition-colors" />
              </button>
            </div>
          </section>

          {/* ── 6. RECOVERY ACTIVITY FEED ────────────────────────────────────────── */}
          <section 
            className="rounded-xl border border-slate-800/80 overflow-hidden flex flex-col h-[500px]"
            style={{ background: '#080d1a' }}
          >
            <div className="px-5 py-4 border-b border-slate-800/60 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Activity className="w-4 h-4 text-emerald-400" />
                <h3 className="text-slate-200 text-sm font-semibold tracking-wide uppercase">Recovery Feed</h3>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <AnimatePresence initial={false}>
                {feed.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-3">
                    <Info className="w-8 h-8 opacity-20" />
                    <p className="text-xs font-mono uppercase tracking-widest">Waiting for recovery events...</p>
                  </div>
                ) : (
                  feed.map((item) => (
                    <motion.div 
                      key={item.id} 
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="relative pl-6 before:absolute before:left-0 before:top-2 before:w-1.5 before:h-1.5 before:rounded-full before:bg-slate-700"
                    >
                      <div className="flex items-center justify-between mb-0.5">
                        <span className={`text-[10px] font-bold tracking-tighter uppercase flex items-center gap-1 ${
                          item.status === 'success' ? 'text-emerald-400' : item.status === 'warning' ? 'text-amber-400' : 'text-rose-400'
                        }`}>
                          {item.status === 'success' ? <CheckCircle className="w-3 h-3" /> : 
                           item.status === 'warning' ? <RefreshCcw className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                          {item.type}
                        </span>
                        <span className="text-[10px] text-slate-600 font-mono">{item.time}</span>
                      </div>
                      <div className="text-xs text-slate-300 font-medium leading-snug">
                        {renderSafe(item.message) || 'Recovery action verified.'}
                      </div>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>
          </section>
        </div>
      </div>

      {/* Restore Confirmation Modal */}
      <RestoreModal 
        backup={selectedBackup}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConfirm={handleRestore}
        loading={opLoading.restore}
      />

      {/* Logs Viewer Modal */}
      <LogsModal 
        isOpen={isLogsModalOpen}
        onClose={() => setIsLogsModalOpen(false)}
        logs={logs}
        loading={loading}
      />

      {/* Floating System Alert/Notification */}
      <AnimatePresence>
        {notification && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className={`fixed top-20 right-6 z-[120] max-w-sm rounded-xl border p-4 shadow-2xl flex items-start gap-3 backdrop-blur-md ${
              notification.type === 'success' 
                ? 'bg-emerald-950/90 border-emerald-500/30 text-emerald-200 shadow-emerald-900/20' 
                : 'bg-rose-950/90 border-rose-500/30 text-rose-200 shadow-rose-900/20'
            }`}
          >
            <div className={`p-1.5 rounded-lg border ${
              notification.type === 'success' ? 'bg-emerald-900/30 border-emerald-500/20' : 'bg-rose-900/30 border-rose-500/20'
            }`}>
              {notification.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <AlertCircle className="w-5 h-5 text-rose-400" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold tracking-tight">{notification.title}</div>
              <div className="text-xs opacity-90 mt-0.5 leading-relaxed">{notification.message}</div>
            </div>
            <button onClick={() => setNotification(null)} className="text-slate-500 hover:text-slate-300 transition-colors shrink-0">
              <XCircle className="w-4 h-4 text-slate-500 hover:text-rose-400" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}
