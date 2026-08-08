import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Send,
  Bot,
  User,
  Terminal,
  Loader2,
  HelpCircle,
  Database,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { apiClient } from '../../api/client';
import type { AIQueryResponse } from '../../types';

// ── Types ──────────────────────────────────────────────────────────────────────

interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
  sql?: string; // set on assistant turns — enables multi-turn SQL context
}

interface Message {
  type: 'user' | 'assistant';
  text: string;
  response?: AIQueryResponse;
}

// ── Component ──────────────────────────────────────────────────────────────────

export const ChatQueryBox: React.FC = () => {
  const [query, setQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [showDevDetails, setShowDevDetails] = useState<boolean>(true);
  const [showDebugAccordion, setShowDebugAccordion] = useState<Record<number, boolean>>({});

  // Visual chat messages (what the user sees)
  const [messages, setMessages] = useState<Message[]>([
    {
      type: 'assistant',
      text: "Hello! I'm your AI Text-to-SQL Conversational Analytics Assistant. Ask me anything in plain English about students, teachers, attendance, or fee collections for Greenwood High — including multi-turn follow-ups like \"list their names\" after a count query!",
    },
  ]);

  // Conversation history sent to the backend for multi-turn context resolution
  const [chatHistory, setChatHistory] = useState<ChatTurn[]>([]);

  // Auto-scroll to bottom of chat
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const samplePrompts = [
    'List all teachers in my school',
    'How many students are in Class 10-A?',
    'List name of students whose fees is partially paid',
    'Which students were absent yesterday in Class 10-A?',
    'What is the total fee collection efficiency rate?',
    'Show all overdue fee invoices',
  ];

  // ── Send handler ─────────────────────────────────────────────────────────────

  const handleSend = async (userQuery?: string) => {
    const q = (userQuery || query).trim();
    if (!q || loading) return;

    setQuery('');
    const userMessage: Message = { type: 'user', text: q };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const res = await apiClient.post<AIQueryResponse>('/ai-analytics/ask', {
        query: q,
        chat_history: chatHistory.slice(-6).map((t) => ({
          role: t.role,
          content: t.content,
          sql: t.sql ?? null,
        })),
        debug_mode: showDevDetails,
      });

      const assistantMessage: Message = {
        type: 'assistant',
        text: res.data.summary_answer,
        response: res.data,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Persist turns into history for the next request
      setChatHistory((prev) => [
        ...prev,
        { role: 'user', content: q },
        {
          role: 'assistant',
          content: res.data.summary_answer,
          sql: res.data.generated_sql || undefined,
        },
      ]);
    } catch (err: any) {
      console.error('AI Analytics request error:', err);
      const errText = err.response?.data?.detail || err.message || 'Could not connect to AI Engine.';
      setMessages((prev) => [
        ...prev,
        { type: 'assistant', text: `⚠️ Error: ${errText}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // ── Reset conversation ────────────────────────────────────────────────────────

  const handleReset = () => {
    setMessages([
      {
        type: 'assistant',
        text: 'Conversation reset. Ask me a new question about students, teachers, attendance, or fees!',
      },
    ]);
    setChatHistory([]);
    setQuery('');
    setShowDebugAccordion({});
  };

  const toggleDebugAccordion = (idx: number) => {
    setShowDebugAccordion((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-3xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/60 via-purple-950/40 to-slate-900 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
          <div className="flex items-center space-x-3">
            <div className="p-3 rounded-2xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-lg">
              <Sparkles className="w-6 h-6 text-amber-400 animate-pulse" />
            </div>
            <div>
              <h2 className="text-xl font-black text-white tracking-tight flex items-center space-x-2">
                <span>AI Conversational Analytics Engine</span>
                <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full font-semibold">
                  Module 8.0 Live
                </span>
              </h2>
              <p className="text-xs text-indigo-200 mt-0.5">
                Multi-Turn Context · AST-Guarded SQL · PII-Safe · Local Interpolation
              </p>
            </div>
          </div>

          {/* Right Action Controls */}
          <div className="flex items-center space-x-2">
            {/* Dev Mode Toggle */}
            <button
              onClick={() => setShowDevDetails((prev) => !prev)}
              title="Toggle Developer SQL & Execution Log Panel"
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition ${
                showDevDetails
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm'
                  : 'bg-slate-900/80 text-slate-400 border-slate-700 hover:text-white'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>🛠️ Dev Mode ({showDevDetails ? 'SQL ON' : 'SQL OFF'})</span>
            </button>

            {/* Reset button */}
            <button
              onClick={handleReset}
              title="Reset conversation"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-700 hover:border-red-500/40 hover:text-red-400 text-slate-400 text-xs transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>New Chat</span>
            </button>
          </div>
        </div>

        {/* Turn counter badge */}
        {chatHistory.length > 0 && (
          <div className="mt-3 relative z-10">
            <span className="text-[11px] bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 px-2.5 py-0.5 rounded-full">
              🔗 {Math.floor(chatHistory.length / 2)} conversation turn{chatHistory.length > 2 ? 's' : ''} in context
            </span>
          </div>
        )}
      </div>

      {/* Suggested Quick Prompts */}
      <div className="glass-panel p-4 rounded-2xl border border-slate-800 space-y-2">
        <div className="text-xs font-semibold text-slate-400 flex items-center space-x-1.5 uppercase tracking-wider">
          <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
          <span>Suggested Questions (Click to ask):</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {samplePrompts.map((prompt, idx) => (
            <button
              key={idx}
              disabled={loading}
              onClick={() => handleSend(prompt)}
              className="px-3 py-1.5 rounded-xl bg-slate-900/90 hover:bg-indigo-950/80 border border-slate-800 hover:border-indigo-500/40 text-xs text-slate-300 hover:text-white transition duration-200 text-left disabled:opacity-50"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages Feed */}
      <div className="space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex items-start space-x-3 ${msg.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
          >
            {/* Avatar */}
            <div
              className={`w-9 h-9 rounded-2xl flex items-center justify-center shrink-0 ${
                msg.type === 'user'
                  ? 'bg-slate-800 text-slate-200 border border-slate-700'
                  : 'bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/20'
              }`}
            >
              {msg.type === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
            </div>

            {/* Message Bubble */}
            <div
              className={`flex-1 rounded-2xl p-5 border space-y-4 ${
                msg.type === 'user'
                  ? 'bg-indigo-950/80 border-indigo-500/40 text-white max-w-xl ml-auto'
                  : 'glass-panel border-slate-800 text-slate-200'
              }`}
            >
              {/* 1. Conversational Summary Answer Sentence */}
              <div className="text-sm font-medium leading-relaxed flex items-start space-x-2">
                {msg.type === 'assistant' && msg.response && (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                )}
                <span>{msg.text}</span>
              </div>

              {/* 2. PRIMARY DATA TABLE — ALWAYS VISIBLE TO ALL USERS BELOW INTRO */}
              {msg.response && msg.response.rows && msg.response.rows.length > 0 && msg.response.columns && msg.response.columns.length > 0 && (
                <div className="rounded-2xl border border-slate-800 overflow-hidden bg-slate-950/90 shadow-xl">
                  <div className="px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 text-xs font-semibold text-slate-300 flex items-center justify-between">
                    <span className="flex items-center space-x-2 text-indigo-300">
                      <Database className="w-4 h-4 text-amber-400" />
                      <span>Query Results Table</span>
                    </span>
                    <span className="text-[11px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-full font-mono">
                      {msg.response.rows.length} Record{msg.response.rows.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="overflow-x-auto max-h-80">
                    <table className="w-full text-left text-xs text-slate-200">
                      <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] tracking-wider font-bold border-b border-slate-800 sticky top-0 z-10">
                        <tr>
                          {msg.response.columns.map((col, cIdx) => (
                            <th key={cIdx} className="px-4 py-3 whitespace-nowrap">
                              {col.replace(/_/g, ' ')}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-sans text-xs">
                        {msg.response.rows.map((row, rIdx) => (
                          <tr
                            key={rIdx}
                            className={`hover:bg-indigo-950/30 transition ${
                              rIdx % 2 === 0 ? 'bg-slate-950' : 'bg-slate-900/40'
                            }`}
                          >
                            {row.map((cell: any, cIdx: number) => (
                              <td key={cIdx} className="px-4 py-2.5 whitespace-nowrap text-slate-200">
                                {cell === null ? (
                                  <span className="text-slate-600 font-mono italic">NULL</span>
                                ) : typeof cell === 'number' ? (
                                  <span className="font-mono text-emerald-300 font-semibold">{cell}</span>
                                ) : (
                                  String(cell)
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* 3. CONDITIONAL DEVELOPER DEBUG ACCORDION (Visible ONLY when showDevDetails is ON) */}
              {showDevDetails && msg.response && msg.response.generated_sql && (
                <div className="border-t border-slate-800/80 pt-3">
                  <button
                    onClick={() => toggleDebugAccordion(idx)}
                    className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-indigo-300 font-semibold transition"
                  >
                    <Terminal className="w-3.5 h-3.5 text-amber-400" />
                    <span>View Generated SQL &amp; Execution Details</span>
                    {msg.response.execution_time_ms !== undefined && (
                      <span className="text-[10px] text-slate-500 font-mono flex items-center space-x-0.5 ml-2">
                        <Clock className="w-3 h-3" />
                        <span>{msg.response.execution_time_ms}ms</span>
                      </span>
                    )}
                    {showDebugAccordion[idx] ? (
                      <ChevronUp className="w-3.5 h-3.5 ml-1" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 ml-1" />
                    )}
                  </button>

                  {showDebugAccordion[idx] && (
                    <div className="mt-3 space-y-3">
                      {/* SQL Code Block */}
                      <div className="rounded-xl bg-slate-950 p-4 border border-slate-800 space-y-2 font-mono text-xs">
                        <div className="flex items-center justify-between text-[11px] text-slate-400">
                          <span className="text-indigo-400 font-semibold">SQLite Executed Statement:</span>
                          <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                            {msg.response.row_count} Row(s) Returned
                          </span>
                        </div>
                        <div className="p-3 rounded-lg bg-slate-900 text-amber-300 font-semibold text-[11px] overflow-x-auto border border-slate-800 leading-relaxed">
                          {msg.response.generated_sql}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-center space-x-3 text-slate-400 text-xs p-4 glass-panel rounded-2xl max-w-md">
            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
            <span>AI Engine querying database records…</span>
          </div>
        )}

        {/* Auto-scroll anchor */}
        <div ref={bottomRef} />
      </div>

      {/* Query Input Box */}
      <div className="glass-panel p-3 rounded-2xl border border-slate-800 flex items-center space-x-3 sticky bottom-4 shadow-2xl">
        <input
          type="text"
          id="ai-analytics-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={loading}
          placeholder={
            chatHistory.length > 0
              ? "Ask a follow-up like 'list their names' or start a new question…"
              : "Ask about teachers, students, attendance, or fees (e.g. 'List all teachers in my school')…"
          }
          className="flex-1 bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
        />
        <button
          id="ai-analytics-send"
          disabled={!query.trim() || loading}
          onClick={() => handleSend()}
          className="p-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-95 text-white shadow-lg shadow-indigo-500/20 disabled:opacity-40 transition"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
