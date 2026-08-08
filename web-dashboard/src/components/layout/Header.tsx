import React, { useState, useEffect, useRef } from 'react';
import { 
  Bell, 
  LogOut, 
  Sparkles, 
  CheckCheck, 
  CalendarCheck, 
  CreditCard, 
  GraduationCap, 
  ShieldCheck, 
  AlertTriangle,
  Clock,
  ChevronRight
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTenant } from '../../config/ThemeProvider';
import { apiClient } from '../../api/client';
import type { NotificationItem } from '../../types';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();
  const { config } = useTenant();

  const [isNotificationOpen, setIsNotificationOpen] = useState<boolean>(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const popoverRef = useRef<HTMLDivElement>(null);
  const bellButtonRef = useRef<HTMLButtonElement>(null);

  // Fetch notifications on mount and when popover is opened
  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get<NotificationItem[]>('/notifications/inbox');
      setNotifications(res.data || []);
    } catch (err) {
      console.error('Error fetching notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  // Click-outside listener to close popover
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node) &&
        bellButtonRef.current &&
        !bellButtonRef.current.contains(event.target as Node)
      ) {
        setIsNotificationOpen(false);
      }
    };

    if (isNotificationOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isNotificationOpen]);

  const handleToggleNotifications = () => {
    if (!isNotificationOpen) {
      fetchNotifications();
    }
    setIsNotificationOpen((prev) => !prev);
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient.post('/notifications/mark-all-read');
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true, read: true }))
      );
    } catch (err) {
      console.error('Error marking all as read:', err);
      // Optimistic update
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true, read: true }))
      );
    }
  };

  const handleMarkItemRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true, read: true } : n))
    );
  };

  const unreadCount = notifications.filter((n) => !n.is_read && !n.read).length;

  const getCategoryIcon = (category: string) => {
    const cat = (category || '').toUpperCase();
    if (cat === 'ATTENDANCE') {
      return <CalendarCheck className="w-4 h-4 text-emerald-400" />;
    }
    if (cat === 'FEES') {
      return <CreditCard className="w-4 h-4 text-amber-400" />;
    }
    if (cat === 'ACADEMIC') {
      return <GraduationCap className="w-4 h-4 text-indigo-400" />;
    }
    if (cat === 'SYSTEM') {
      return <ShieldCheck className="w-4 h-4 text-purple-400" />;
    }
    return <AlertTriangle className="w-4 h-4 text-slate-400" />;
  };

  const getCategoryBadgeClass = (category: string) => {
    const cat = (category || '').toUpperCase();
    if (cat === 'ATTENDANCE') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    if (cat === 'FEES') return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    if (cat === 'ACADEMIC') return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
    if (cat === 'SYSTEM') return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    return 'bg-slate-800 text-slate-300 border-slate-700';
  };

  const formatRelativeTime = (timestampStr: string) => {
    try {
      const date = new Date(timestampStr);
      const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
      if (diffSec < 60) return 'Just now';
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)} mins ago`;
      if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} hours ago`;
      return `${Math.floor(diffSec / 86400)} days ago`;
    } catch {
      return 'Recent';
    }
  };

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
      case 'teacher-schedule':
        return 'Teacher Daily Schedule & Timetable';
      case 'teacher-attendance':
        return 'Classroom Attendance & Roll Call';
      case 'student-academics':
      case 'parent-academics':
        return 'Academic Report Card & Subject Grades';
      case 'student-attendance':
      case 'parent-attendance':
        return 'Personal Attendance History & Logs';
      case 'student-fees':
      case 'parent-fees':
        return 'Student Fee Ledger & Online Payments';
      default:
        return 'Academic ERP Portal';
    }
  };

  return (
    <header className="h-16 border-b border-slate-800 glass-panel px-6 flex items-center justify-between sticky top-0 z-40 select-none">
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
      <div className="flex items-center space-x-4 relative">
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

        {/* Interactive Notification Bell */}
        <div className="relative">
          <button
            ref={bellButtonRef}
            onClick={handleToggleNotifications}
            title="System Notifications & Alerts"
            className={`p-2 rounded-xl border transition relative duration-200 ${
              isNotificationOpen
                ? 'bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-600/30'
                : 'bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700/60 border-slate-800'
            }`}
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-amber-500 text-slate-950 text-[10px] font-black flex items-center justify-center shadow-md animate-pulse">
                {unreadCount}
              </span>
            )}
          </button>

          {/* Dynamic Notification Popover Dropdown */}
          {isNotificationOpen && (
            <div
              ref={popoverRef}
              className="absolute right-0 mt-3 w-96 glass-panel rounded-3xl border border-slate-800 shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
            >
              {/* Popover Header */}
              <div className="p-4 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <h3 className="font-bold text-sm text-white">Notifications</h3>
                  {unreadCount > 0 ? (
                    <span className="text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full font-bold">
                      {unreadCount} unread
                    </span>
                  ) : (
                    <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold">
                      All caught up
                    </span>
                  )}
                </div>

                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="flex items-center space-x-1 text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold transition"
                  >
                    <CheckCheck className="w-3.5 h-3.5" />
                    <span>Mark all read</span>
                  </button>
                )}
              </div>

              {/* Popover List Body */}
              <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60">
                {loading ? (
                  <div className="p-8 text-center text-xs text-slate-400">
                    Loading notifications...
                  </div>
                ) : notifications.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-400">
                    No notifications in inbox.
                  </div>
                ) : (
                  notifications.map((notif) => {
                    const isUnread = !notif.is_read && !notif.read;
                    return (
                      <div
                        key={notif.id}
                        onClick={() => handleMarkItemRead(notif.id)}
                        className={`p-3.5 px-4 flex items-start space-x-3 transition cursor-pointer ${
                          isUnread
                            ? 'bg-slate-900/70 hover:bg-slate-900'
                            : 'hover:bg-slate-900/40 opacity-75'
                        }`}
                      >
                        {/* Icon */}
                        <div className="p-2 rounded-xl bg-slate-800/80 border border-slate-700/60 shrink-0 mt-0.5">
                          {getCategoryIcon(notif.category || notif.notification_type)}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="flex items-center justify-between gap-2">
                            <h4 className="text-xs font-bold text-slate-200 line-clamp-1">
                              {notif.title}
                            </h4>
                            <span className="text-[10px] text-slate-500 font-mono whitespace-nowrap flex items-center space-x-0.5">
                              <Clock className="w-2.5 h-2.5" />
                              <span>{formatRelativeTime(notif.created_at)}</span>
                            </span>
                          </div>

                          <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                            {notif.message}
                          </p>

                          <div className="flex items-center space-x-2 pt-1">
                            <span
                              className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${getCategoryBadgeClass(
                                notif.category || notif.notification_type
                              )}`}
                            >
                              {notif.category || notif.notification_type || 'ALERT'}
                            </span>
                            {isUnread && (
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Popover Footer */}
              <div className="p-3 border-t border-slate-800 bg-slate-950/80 text-center">
                <button
                  onClick={() => {
                    setIsNotificationOpen(false);
                    if (user?.role === 'student') {
                      setActiveTab('student-attendance');
                    } else if (user?.role === 'parent') {
                      setActiveTab('parent-attendance');
                    } else {
                      setActiveTab('attendance');
                    }
                  }}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold inline-flex items-center space-x-1 transition"
                >
                  <span>View Attendance &amp; Activity Log</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>

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
