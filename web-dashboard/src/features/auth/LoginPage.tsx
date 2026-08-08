import React, { useState } from 'react';
import { GraduationCap, Lock, Mail, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTenant } from '../../config/ThemeProvider';
import axios from 'axios';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { config } = useTenant();

  const [username, setUsername] = useState('admin@demo.school');
  const [password, setPassword] = useState('Demo@1234!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);

      const response = await axios.post('http://localhost:8000/api/v1/auth/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const data = response.data;
      login(data.access_token, {
        sub: username,
        role: data.role,
        full_name: data.full_name,
        tenant_id: data.tenant_id,
        assigned_sections: data.assigned_sections || [],
      });
    } catch (err: any) {
      console.error('Login error:', err);
      setError(err.response?.data?.detail || 'Invalid username or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Dynamic Background Glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[var(--color-primary)]/20 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[var(--color-secondary)]/15 rounded-full blur-3xl pointer-events-none"></div>

      <div className="w-full max-w-md relative z-10">
        {/* Brand Logo Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-[var(--color-primary)] to-[var(--color-secondary)] p-1 shadow-xl shadow-[var(--color-primary)]/30 mb-4">
            <div className="w-full h-full bg-slate-900 rounded-xl flex items-center justify-center">
              <GraduationCap className="w-8 h-8 text-[var(--color-secondary)]" />
            </div>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            {config?.school_name || 'Greenwood High'}
          </h1>
          <p className="text-xs text-amber-400 font-medium mt-1">
            {config?.tagline || 'AI-Powered Smart Academic ERP Portal'}
          </p>
        </div>

        {/* Login Card */}
        <div className="glass-panel p-8 rounded-3xl border border-slate-800 shadow-2xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-lg font-bold text-white">Sign In to Dashboard</h2>
              <p className="text-xs text-slate-400">Phase 1 & 2 Demo Environment</p>
            </div>
            <span className="flex items-center space-x-1 text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold">
              <ShieldCheck className="w-3 h-3" />
              <span>ONLINE</span>
            </span>
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                User Email / Username
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="email"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="admin@demo.school"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[var(--color-primary)] transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[var(--color-primary)] transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-accent)] hover:opacity-95 text-white font-semibold text-sm shadow-lg shadow-[var(--color-primary)]/30 flex items-center justify-center space-x-2 transition duration-200 disabled:opacity-50"
            >
              {loading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In to Admin Portal</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Credential Helper */}
          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-400 space-y-1.5">
            <div className="font-semibold text-slate-300 flex items-center space-x-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Demo Login Credentials:</span>
            </div>
            <div className="font-mono text-[11px] text-indigo-300">
              User: <span className="text-white">admin@demo.school</span>
            </div>
            <div className="font-mono text-[11px] text-indigo-300">
              Pass: <span className="text-white">Demo@1234!</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
