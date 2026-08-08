import React from 'react';
import { 
  GraduationCap,
  ChevronRight,
  ShieldAlert
} from 'lucide-react';
import { useTenant } from '../../config/ThemeProvider';
import { useAuth } from '../../context/AuthContext';
import { ROLE_NAV_CONFIG, normalizeRole } from '../../config/roleNavigation';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const { config } = useTenant();
  const { user } = useAuth();
  const role = normalizeRole(user?.role);
  const navItems = ROLE_NAV_CONFIG[role] || ROLE_NAV_CONFIG.student;

  return (
    <aside className="w-64 glass-panel flex flex-col border-r border-slate-800 h-screen sticky top-0 select-none z-30">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-800/80 flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[var(--color-primary)] to-[var(--color-secondary)] p-0.5 flex items-center justify-center shadow-lg shadow-[var(--color-primary)]/20">
          <div className="w-full h-full bg-slate-900 rounded-[10px] flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-[var(--color-secondary)]" />
          </div>
        </div>
        <div>
          <h1 className="font-bold text-base tracking-wide text-white leading-snug line-clamp-1">
            {config?.school_name || 'Greenwood High'}
          </h1>
          <p className="text-xs text-amber-400 font-medium">
            {config?.tagline || 'Excellence in Education'}
          </p>
        </div>
      </div>

      {/* Tenant Indicator Badge */}
      <div className="px-4 py-3 mx-4 my-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center space-x-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Tenant: <strong className="text-slate-200">{config?.tenant_id || user?.tenant_id || 'greenwood-high-001'}</strong></span>
        </span>
        <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded uppercase font-semibold">
          {user?.role ? user.role.toUpperCase() : config?.board || 'CBSE'}
        </span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-2 space-y-1.5 overflow-y-auto">
        <div className="px-3 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          {role.toUpperCase()} MENU
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          if (item.isAI) {
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-3 rounded-xl font-medium text-sm transition-all duration-200 group relative ${
                  isActive
                    ? 'bg-gradient-to-r from-indigo-600/90 via-purple-600/90 to-amber-500/90 text-white shadow-lg shadow-indigo-500/20'
                    : 'text-indigo-300 hover:text-white bg-indigo-950/40 hover:bg-indigo-900/50 border border-indigo-500/30'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-amber-400 group-hover:scale-110'} transition-transform duration-200`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="bg-amber-400 text-slate-950 text-[10px] font-black px-1.5 py-0.5 rounded-full shadow-sm">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          }

          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 ${
                isActive
                  ? 'bg-[var(--color-primary)] text-white shadow-md shadow-[var(--color-primary)]/30 border border-white/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {isActive && <ChevronRight className="w-4 h-4 opacity-70" />}
            </button>
          );
        })}
      </nav>

      {/* Feature Flags Indicator Footer */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40 text-xs text-slate-400 space-y-2">
        <div className="flex items-center justify-between text-[11px]">
          <span className="flex items-center space-x-1">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            <span>AI Conversational</span>
          </span>
          <span className="text-emerald-400 font-semibold">ACTIVE</span>
        </div>
        <div className="flex items-center justify-between text-[11px]">
          <span>Role Guardrails</span>
          <span className="text-emerald-400 font-mono">ENFORCED</span>
        </div>
      </div>
    </aside>
  );
};
