import React from 'react';
import { Bell, LogOut, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTenant } from '../../config/ThemeProvider';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();
  const { config } = useTenant();

  const getTitle = () => {
    switch (activeTab) {
      case 'dashboard':
        return 'Executive Overview Dashboard';
      case 'students':
        return 'Student Directory & Academic Timetable';
      case 'attendance':
        return 'Attendance Analytics & Absence Insights';
      case 'fees':
        return 'Fee Collection & Financial Management';
      case 'ai-analytics':
        return 'AI Conversational Analytics Engine';
      default:
        return 'Dashboard';
    }
  };

  return (
    <header className="h-16 border-b border-slate-800 glass-panel px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Page Title & Breadcrumbs */}
      <div>
        <h2 className="text-lg font-bold text-white flex items-center space-x-2">
          <span>{getTitle()}</span>
          {activeTab === 'ai-analytics' && (
            <span className="flex items-center space-x-1 text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-2 py-0.5 rounded-full font-medium">
              <Sparkles className="w-3 h-3 text-amber-400" />
              <span>LLM Powered</span>
            </span>
          )}
        </h2>
        <p className="text-xs text-slate-400">
          Academic Session 2024-25 &bull; {config?.city || 'Kanpur'}, {config?.country || 'IN'}
        </p>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-4">
        {/* Quick AI Trigger Button */}
        {activeTab !== 'ai-analytics' && (
          <button
            onClick={() => setActiveTab('ai-analytics')}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-indigo-950/60 hover:bg-indigo-900/80 border border-indigo-500/40 text-indigo-200 text-xs font-medium transition duration-200 shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
            <span>Ask AI Assistant</span>
          </button>
        )}

        {/* Notifications */}
        <button className="p-2 rounded-lg bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700/60 transition relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-500"></span>
        </button>

        {/* Divider */}
        <div className="h-6 w-px bg-slate-800"></div>

        {/* User Badge & Logout */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-semibold text-xs">
            {user?.full_name ? user.full_name.charAt(0) : 'A'}
          </div>
          <div className="text-xs hidden sm:block">
            <div className="font-semibold text-slate-200 line-clamp-1">
              {user?.full_name || 'System Admin'}
            </div>
            <div className="text-[10px] text-slate-400 capitalize">
              Role: {user?.role || 'admin'}
            </div>
          </div>
          <button
            onClick={logout}
            title="Logout"
            className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
