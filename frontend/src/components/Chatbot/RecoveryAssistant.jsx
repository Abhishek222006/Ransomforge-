import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Shield, X, Send, Loader, ShieldAlert, Activity, Database } from 'lucide-react';
import { api } from '../../services/api';

const SUGGESTIONS = [
  "What caused this attack?",
  "How do I restore safely?",
  "Explain quarantine state",
  "Should I restore latest snapshot?",
  "Summarize recent alerts",
];

export default function RecoveryAssistant({ threatScore, quarantined, networkIsolated, events }) {
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello. I am your Recovery AI Assistant. How can I help you investigate or recover from the current security events?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Adjust textarea height automatically
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSend = async (textOverride) => {
    const textToSend = typeof textOverride === 'string' ? textOverride : input;
    if (!textToSend.trim() || isLoading) return;

    const userMsg = { role: 'user', content: textToSend.trim() };
    setMessages(prev => [...prev, userMsg]);
    if (typeof textOverride !== 'string') {
      setInput('');
    }
    setIsLoading(true);

    // Format recent events for context
    const recentEventsStr = events.slice(0, 5).map(e => 
      `${e.time} | ${e.severity} | ${e.title} - ${e.description}`
    );

    try {
      const payload = {
        session_id: sessionId,
        message: userMsg.content,
        threat_score: threatScore,
        severity: threatScore >= 85 ? 'critical' : threatScore >= 65 ? 'high' : threatScore >= 35 ? 'medium' : 'low',
        recent_events: recentEventsStr
      };

      const res = await api.assistantChat(payload);
      
      if (res.session_id && !sessionId) {
        setSessionId(res.session_id);
      }

      setMessages(prev => [...prev, { role: 'assistant', content: res.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: '⚠️ Error: Unable to reach the AI service. Please check your connection or try again.' }]);
    } finally {
      setIsLoading(false);
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 0);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 z-50 p-4 rounded-full shadow-2xl flex items-center justify-center border border-indigo-500/40 group"
            style={{
              background: 'linear-gradient(135deg, rgba(49, 46, 129, 0.9), rgba(30, 27, 75, 0.9))',
              backdropFilter: 'blur(8px)',
              boxShadow: '0 0 20px rgba(67, 56, 202, 0.4)'
            }}
          >
            {/* Pulse effect */}
            <div className="absolute inset-0 rounded-full bg-indigo-500/20 animate-ping opacity-75"></div>
            <Bot className="w-6 h-6 text-indigo-300 relative z-10 group-hover:text-indigo-200 transition-colors" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="fixed bottom-6 right-6 z-50 w-[420px] max-w-[calc(100vw-2rem)] h-[650px] max-h-[85vh] flex flex-col rounded-2xl overflow-hidden border border-slate-700/60"
            style={{
              background: 'rgba(10, 15, 30, 0.85)',
              backdropFilter: 'blur(16px)',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 40px rgba(67, 56, 202, 0.15)'
            }}
          >
            {/* Header */}
            <div className="shrink-0 px-4 py-3 border-b border-slate-700/50 flex items-center justify-between"
                 style={{ background: 'linear-gradient(to right, rgba(30, 27, 75, 0.5), rgba(15, 23, 42, 0.5))' }}>
              <div className="flex items-center gap-3">
                <div className="p-1.5 rounded-lg bg-indigo-500/20 border border-indigo-500/30">
                  <Bot className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 tracking-wide">Recovery AI Assistant</h3>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></div>
                    <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Threat-aware</span>
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Context Panel */}
            <div className="shrink-0 px-4 py-2 border-b border-slate-700/30 bg-slate-900/40 grid grid-cols-3 gap-2 divide-x divide-slate-700/50">
              <div className="flex flex-col items-center justify-center">
                <span className="text-[10px] text-slate-500 uppercase font-mono tracking-tighter">Threat Score</span>
                <div className="flex items-center gap-1 mt-0.5">
                  <Activity className={`w-3 h-3 ${threatScore >= 85 ? 'text-rose-400' : threatScore >= 65 ? 'text-amber-400' : 'text-emerald-400'}`} />
                  <span className="text-xs font-bold text-slate-300">{threatScore}</span>
                </div>
              </div>
              <div className="flex flex-col items-center justify-center">
                <span className="text-[10px] text-slate-500 uppercase font-mono tracking-tighter">Quarantine</span>
                <div className="flex items-center gap-1 mt-0.5">
                  {quarantined || networkIsolated ? (
                    <ShieldAlert className="w-3 h-3 text-rose-400" />
                  ) : (
                    <Shield className="w-3 h-3 text-emerald-400" />
                  )}
                  <span className="text-xs font-bold text-slate-300">
                    {quarantined ? 'ACTIVE' : networkIsolated ? 'NETWORK' : 'SAFE'}
                  </span>
                </div>
              </div>
              <div className="flex flex-col items-center justify-center">
                <span className="text-[10px] text-slate-500 uppercase font-mono tracking-tighter">Recent Alerts</span>
                <div className="flex items-center gap-1 mt-0.5">
                  <Database className="w-3 h-3 text-blue-400" />
                  <span className="text-xs font-bold text-slate-300">{events?.length || 0}</span>
                </div>
              </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div 
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-[13px] leading-relaxed shadow-sm ${
                      msg.role === 'user' 
                        ? 'bg-indigo-600 text-white rounded-br-none' 
                        : 'bg-slate-800/80 border border-slate-700/50 text-slate-300 rounded-bl-none'
                    }`}
                  >
                    {msg.content.split('\n').map((line, idx) => {
                      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
                        return <div key={idx} className="flex gap-2 mt-1">
                          <span className="text-indigo-400">•</span>
                          <span>{line.replace(/^[-*]\s/, '')}</span>
                        </div>
                      }
                      return (
                        <React.Fragment key={idx}>
                          <span dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/`(.*?)`/g, '<code class="bg-slate-900/50 px-1 py-0.5 rounded text-indigo-300">$1</code>') }} />
                          {idx < msg.content.split('\n').length - 1 && <br />}
                        </React.Fragment>
                      )
                    })}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl rounded-bl-none bg-slate-800/80 border border-slate-700/50 px-4 py-3 flex items-center gap-3">
                    <Loader className="w-4 h-4 text-indigo-400 animate-spin" />
                    <span className="text-xs text-slate-400 font-medium tracking-wide">Analyzing context...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Suggestions */}
            {messages.length < 3 && !isLoading && (
              <div className="shrink-0 px-4 pb-3 overflow-x-auto whitespace-nowrap scrollbar-none flex gap-2">
                {SUGGESTIONS.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(suggestion)}
                    className="inline-block px-3 py-1.5 rounded-full border border-slate-700/50 bg-slate-800/40 text-[11px] text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            {/* Input Area */}
            <div className="shrink-0 p-3 bg-slate-900/80 border-t border-slate-700/50">
              <div className="relative flex items-end gap-2 bg-slate-800/50 rounded-xl border border-slate-700/50 focus-within:border-indigo-500/50 focus-within:bg-slate-800 transition-colors p-1.5">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask the AI analyst..."
                  className="w-full max-h-[120px] bg-transparent text-sm text-slate-200 placeholder-slate-500 resize-none outline-none py-2 px-2 scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-transparent"
                  rows={1}
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim() || isLoading}
                  className="p-2 mb-0.5 mr-0.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-2 text-center">
                <span className="text-[10px] text-slate-500 font-mono tracking-tighter">AI responses are generated based on local security context</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
