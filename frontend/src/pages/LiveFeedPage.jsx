import React from 'react'
import { Radio } from 'lucide-react'
import LiveEventFeed from '../components/Dashboard/LiveEventFeed'

export default function LiveFeedPage({ events }) {
  return (
    <div className="space-y-5 h-full flex flex-col min-h-[calc(100vh-140px)]">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Radio className="w-5 h-5 text-blue-400" />
            <h1 className="text-slate-100 font-bold text-xl">Live Telemetry Feed</h1>
          </div>
          <p className="text-slate-500 text-sm">Raw security event stream from all monitored endpoints</p>
        </div>
      </div>
      
      <div className="flex-1">
        <LiveEventFeed events={events} fullHeight={true} />
      </div>
    </div>
  )
}
