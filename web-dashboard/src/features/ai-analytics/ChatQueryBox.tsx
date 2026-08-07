import React, { useState } from 'react';
import { 
  Sparkles, 
  Send, 
  Bot, 
  User, 
  Terminal,
  Loader2,
  HelpCircle,
  Database
} from 'lucide-react';
import { apiClient } from '../../api/client';
import type { AIQueryResponse } from '../../types';

export const ChatQueryBox: React.FC = () => {
  const [query, setQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<Array<{
    type: 'user' | 'assistant';
    text: string;
    response?: AIQueryResponse;
  }>>([
    {
      type: 'assistant',
      text: "Hello! I am your AI Text-to-SQL Conversational Analytics Assistant. Ask me any question in plain English about students, attendance, or fee collections for Greenwood High!",
    }
  ]);

  const samplePrompts = [
    "How many students are in Class 10-A?",
    "How many students were absent in Class 10-A?",
    "Show all overdue fee invoices",
    "What is the attendance summary breakdown by status?",
    "List top 5 students by roll number",
    "How many fee invoices are paid?"
  ];

  const handleSend = async (userQuery?: string) => {
    const q = userQuery || query;
    if (!q.trim() || loading) return;

    const userMsg = q.trim();
    setQuery('');
    setMessages(prev => [...prev, { type: 'user', text: userMsg }]);
    setLoading(true);

    try {
      const res = await apiClient.post<AIQueryResponse>('/ai-analytics/ask', {
        query: userMsg,
      });

      setMessages(prev => [
        ...prev,
        {
          type: 'assistant',
          text: res.data.summary_answer,
          response: res.data,
        }
      ]);
    } catch (err: any) {
      console.error('AI Analytics request error:', err);
      setMessages(prev => [
        ...prev,
        {
          type: 'assistant',
          text: `Error processing query: ${err.response?.data?.detail || err.message || 'Could not connect to AI Engine.'}`,
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-3xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/60 via-purple-950/40 to-slate-900 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

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
                Translates plain English to AST-Guarded SQL &bull; Read-Only Execution &bull; 500 Row Limit Cap
              </p>
            </div>
          </div>
        </div>
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
              "{prompt}"
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages Feed */}
      <div className="space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex items-start space-x-3 ${
              msg.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''
            }`}
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
              className={`flex-1 rounded-2xl p-5 border space-y-3 ${
                msg.type === 'user'
                  ? 'bg-indigo-950/80 border-indigo-500/40 text-white max-w-xl ml-auto'
                  : 'glass-panel border-slate-800 text-slate-200'
              }`}
            >
              <div className="text-sm font-medium leading-relaxed">
                {msg.text}
              </div>

              {/* Rich Response Details (Generated SQL + Formatted Data Table) */}
              {msg.response && (
                <div className="mt-4 space-y-4 border-t border-slate-800/80 pt-4">
                  {/* SQL Badge Container */}
                  <div className="rounded-xl bg-slate-950 p-4 border border-slate-800 space-y-2 font-mono text-xs">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="flex items-center space-x-1.5 text-indigo-400 font-semibold">
                        <Terminal className="w-3.5 h-3.5" />
                        <span>Generated & Executed SQL Query:</span>
                      </span>
                      <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        {msg.response.row_count} Row(s) Returned
                      </span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-900 text-amber-300 font-semibold text-[11px] overflow-x-auto border border-slate-800">
                      {msg.response.generated_sql}
                    </div>
                  </div>

                  {/* Result Data Table */}
                  {msg.response.rows && msg.response.rows.length > 0 && (
                    <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950">
                      <div className="px-4 py-2 bg-slate-900 border-b border-slate-800 text-[11px] font-semibold text-slate-400 flex items-center justify-between">
                        <span className="flex items-center space-x-1.5">
                          <Database className="w-3.5 h-3.5 text-amber-400" />
                          <span>QueryResult Data Table</span>
                        </span>
                        <span>Columns: {msg.response.columns.join(', ')}</span>
                      </div>
                      <div className="overflow-x-auto max-h-64">
                        <table className="w-full text-left text-xs text-slate-300">
                          <thead className="bg-slate-900/90 text-slate-400 uppercase text-[10px] tracking-wider font-semibold border-b border-slate-800">
                            <tr>
                              {msg.response.columns.map((col, cIdx) => (
                                <th key={cIdx} className="px-4 py-2.5">{col}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                            {msg.response.rows.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-slate-900/60 transition">
                                {row.map((cell: any, cIdx: number) => (
                                  <td key={cIdx} className="px-4 py-2 text-slate-200">
                                    {cell === null ? <span className="text-slate-600">NULL</span> : String(cell)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-3 text-slate-400 text-xs p-4 glass-panel rounded-2xl max-w-md">
            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
            <span>AI Engine translating natural language query into SQL...</span>
          </div>
        )}
      </div>

      {/* Query Input Box */}
      <div className="glass-panel p-3 rounded-2xl border border-slate-800 flex items-center space-x-3 sticky bottom-4 shadow-2xl">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={loading}
          placeholder="Ask a question about students, attendance, or fees (e.g. 'How many students were absent yesterday in Class 10-A?')..."
          className="flex-1 bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
        />
        <button
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
