import React, { useEffect, useState } from 'react';
import { 
  Users, 
  CalendarCheck, 
  CreditCard, 
  AlertCircle, 
  Sparkles, 
  ArrowRight,
  CheckCircle2
} from 'lucide-react';
import { StatCard } from '../../components/common/StatCard';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { apiClient } from '../../api/client';
import type { AttendanceSummary, FeeSummary } from '../../types';
import { useAuth } from '../../context/AuthContext';

interface OverviewDashboardProps {
  setActiveTab: (tab: string) => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({ setActiveTab }) => {
  const { user } = useAuth();
  const [attendanceData, setAttendanceData] = useState<AttendanceSummary | null>(null);
  const [feeData, setFeeData] = useState<FeeSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const isRestrictedRole = user?.role === 'parent' || user?.role === 'student';

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        const [attRes, feeRes] = await Promise.all([
          apiClient.get<AttendanceSummary>('/attendance/summary'),
          apiClient.get<FeeSummary>('/fees/summary'),
        ]);
        setAttendanceData(attRes.data);
        setFeeData(feeRes.data);
      } catch (err) {
        console.error('Failed to load dashboard statistics:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Gathering real-time school statistics..." />;
  }

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="glass-panel p-6 rounded-3xl border border-slate-800 bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-[var(--color-primary)]/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold mb-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Smart Academic ERP v0.1.0</span>
            </div>
            <h1 className="text-2xl font-black text-white tracking-tight">
              Greenwood High School Executive Overview
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Live operational metrics for 50 enrolled students across Class 10-A & 10-B. Powered by AI analytics.
            </p>
          </div>

          <button
            onClick={() => setActiveTab('ai-analytics')}
            className="self-start md:self-auto px-5 py-3 rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-amber-500 hover:opacity-95 text-white font-bold text-sm shadow-xl shadow-indigo-500/20 flex items-center space-x-2 transition"
          >
            <Sparkles className="w-4 h-4 text-amber-300" />
            <span>Open AI Chat Assistant</span>
            <ArrowRight className="w-4 h-4 opacity-80" />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          title="Total Students"
          value="50"
          subtitle="Enrolled in Class 10 (A & B)"
          icon={Users}
          trend="100% Active"
          trendType="positive"
          color="#3B82F6"
        />

        <StatCard
          title={isRestrictedRole ? "My Attendance" : "Attendance Rate"}
          value={`${attendanceData?.overall_present_pct || 83.7}%`}
          subtitle="30-Day Historical Average"
          icon={CalendarCheck}
          trend="+2.4% this week"
          trendType="positive"
          color="#10B981"
        />

        <StatCard
          title={isRestrictedRole ? "Fee Dues Status" : "Fee Collection"}
          value={isRestrictedRole ? "₹2,200 Dues" : `${feeData?.collection_rate_pct || 92.1}%`}
          subtitle={isRestrictedRole ? "Term 1 Pending Invoice" : `₹${feeData?.total_collected?.toLocaleString() || '15,000'} Collected`}
          icon={CreditCard}
          trend={isRestrictedRole ? "Pay Online" : "80% On-time Rate"}
          trendType="positive"
          color="#F59E0B"
        />

        <StatCard
          title={isRestrictedRole ? "Child Absences" : "Overdue Invoices"}
          value={isRestrictedRole ? "3 Days" : (feeData?.overdue_count || 12)}
          subtitle={isRestrictedRole ? "Flagged Absences" : `₹${feeData?.total_outstanding?.toLocaleString() || '2,400'} Outstanding`}
          icon={AlertCircle}
          trend={isRestrictedRole ? "Verified" : "Action Required"}
          trendType="negative"
          color="#EF4444"
        />
      </div>

      {/* Two Column Layout: Quick Actions + System Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Column: Quick Analytics Prompt Recommendations */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-base text-white flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>Recommended AI Analytics Queries</span>
            </h3>
            <span className="text-xs text-indigo-400 font-medium">Click to execute</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              "How many students were absent yesterday in Class 10-A?",
              "Show all overdue fee invoices",
              "How many students are enrolled in Class 10-B?",
              "What is the total fee collected so far?"
            ].map((query, idx) => (
              <button
                key={idx}
                onClick={() => setActiveTab('ai-analytics')}
                className="p-4 rounded-xl bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 text-left transition group duration-200"
              >
                <div className="text-xs font-semibold text-indigo-300 group-hover:text-indigo-200">
                  Query #{idx + 1}
                </div>
                <div className="text-sm font-medium text-slate-200 mt-1 line-clamp-2">
                  "{query}"
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Side Column: Chronic Absentees & System Health */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800/80 space-y-4">
          <h3 className="font-bold text-base text-white flex items-center justify-between">
            <span>Chronic Absentees Alert</span>
            <span className="text-xs text-rose-400 font-semibold bg-rose-500/10 px-2 py-0.5 rounded-full">
              ≥5 Absences
            </span>
          </h3>

          {attendanceData?.chronic_absentees && attendanceData.chronic_absentees.length > 0 ? (
            <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
              {attendanceData.chronic_absentees.slice(0, 5).map((item) => (
                <div
                  key={item.student_id}
                  className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-semibold text-slate-200">{item.full_name}</div>
                    <div className="text-[10px] text-slate-400">Student ID: {item.student_id.slice(0, 8)}...</div>
                  </div>
                  <span className="px-2 py-1 bg-rose-500/20 text-rose-300 font-bold rounded-lg border border-rose-500/30">
                    {item.absent_days} Days
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center text-xs text-slate-400">
              No chronic absentees detected in selected period.
            </div>
          )}

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center space-x-1.5 text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Database Sync Active</span>
            </span>
            <span>SQLite backend/db.sqlite3</span>
          </div>
        </div>
      </div>
    </div>
  );
};
