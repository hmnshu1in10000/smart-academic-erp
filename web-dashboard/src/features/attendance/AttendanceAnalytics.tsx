import React, { useEffect, useState } from 'react';
import { CalendarCheck, AlertTriangle, UserX, CheckCircle, Clock } from 'lucide-react';
import { apiClient } from '../../api/client';
import type { AttendanceSummary } from '../../types';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

export const AttendanceAnalytics: React.FC = () => {
  const [data, setData] = useState<AttendanceSummary | null>(null);
  const [section, setSection] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  const fetchAttendance = async () => {
    setLoading(true);
    try {
      let url = '/attendance/summary';
      if (section) {
        url += `?section=${encodeURIComponent(section)}`;
      }
      const res = await apiClient.get<AttendanceSummary>(url);
      setData(res.data);
    } catch (err) {
      console.error('Failed to load attendance summary:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAttendance();
  }, [section]);

  if (loading) {
    return <LoadingSpinner message="Calculating 30-day attendance analytics..." />;
  }

  // Calculate total counts across all daily stats
  const totalPresent = data?.daily_stats.reduce((acc, d) => acc + d.present, 0) || 0;
  const totalAbsent = data?.daily_stats.reduce((acc, d) => acc + d.absent, 0) || 0;
  const totalLate = data?.daily_stats.reduce((acc, d) => acc + d.late, 0) || 0;
  const grandTotal = totalPresent + totalAbsent + totalLate;

  return (
    <div className="space-y-6">
      {/* Header & Filter Bar */}
      <div className="glass-panel p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <CalendarCheck className="w-5 h-5 text-emerald-400" />
            <span>30-Day Attendance Analytics</span>
          </h2>
          <p className="text-xs text-slate-400">
            Period: {data?.from_date} to {data?.to_date} &bull; Total Signals Logged: {grandTotal.toLocaleString()}
          </p>
        </div>

        {/* Section Filter Buttons */}
        <div className="flex items-center space-x-1.5 bg-slate-900/80 p-1 border border-slate-800 rounded-xl">
          {['', '10-A', '10-B'].map((sec) => (
            <button
              key={sec}
              onClick={() => setSection(sec)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                section === sec
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {sec ? `Class ${sec}` : 'Entire School'}
            </button>
          ))}
        </div>
      </div>

      {/* Top 3 Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex items-center space-x-4">
          <div className="p-3.5 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-semibold uppercase">Present Signals</div>
            <div className="text-2xl font-black text-white mt-0.5">{totalPresent.toLocaleString()}</div>
            <div className="text-[11px] text-emerald-400 font-medium">
              {grandTotal ? ((totalPresent / grandTotal) * 100).toFixed(1) : 0}% of Total
            </div>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex items-center space-x-4">
          <div className="p-3.5 rounded-2xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <UserX className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-semibold uppercase">Absent Signals</div>
            <div className="text-2xl font-black text-white mt-0.5">{totalAbsent.toLocaleString()}</div>
            <div className="text-[11px] text-rose-400 font-medium">
              {grandTotal ? ((totalAbsent / grandTotal) * 100).toFixed(1) : 0}% of Total
            </div>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex items-center space-x-4">
          <div className="p-3.5 rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-semibold uppercase">Late Arrivals</div>
            <div className="text-2xl font-black text-white mt-0.5">{totalLate.toLocaleString()}</div>
            <div className="text-[11px] text-amber-400 font-medium">
              {grandTotal ? ((totalLate / grandTotal) * 100).toFixed(1) : 0}% of Total
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Visual Breakdown & Chronic Absentees */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Daily Attendance Trend Bar List */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-white">Daily Attendance Breakdown</h3>
            <span className="text-xs text-slate-400">Green = Present, Red = Absent, Amber = Late</span>
          </div>

          <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
            {data?.daily_stats.map((item, idx) => {
              const pPct = item.total ? (item.present / item.total) * 100 : 0;
              const aPct = item.total ? (item.absent / item.total) * 100 : 0;
              const lPct = item.total ? (item.late / item.total) * 100 : 0;

              return (
                <div key={idx} className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1.5 text-xs">
                  <div className="flex items-center justify-between font-mono text-[11px]">
                    <span className="text-slate-200 font-semibold">{item.date} ({item.section})</span>
                    <span className="text-slate-400">
                      Rate: <strong className="text-emerald-400">{item.attendance_pct}%</strong> ({item.present}P / {item.absent}A / {item.late}L)
                    </span>
                  </div>
                  {/* Multi-segment Progress Bar */}
                  <div className="w-full h-2 rounded-full bg-slate-800 flex overflow-hidden">
                    <div style={{ width: `${pPct}%` }} className="bg-emerald-500 h-full"></div>
                    <div style={{ width: `${aPct}%` }} className="bg-rose-500 h-full"></div>
                    <div style={{ width: `${lPct}%` }} className="bg-amber-500 h-full"></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chronic Absentees Alert Table */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-bold text-sm text-white flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>Chronic Absentees Alert</span>
            </h3>
            <span className="text-[10px] bg-rose-500/20 text-rose-300 font-bold px-2 py-0.5 rounded-full border border-rose-500/30">
              ≥5 Absences
            </span>
          </div>

          <p className="text-xs text-slate-400">
            Students requiring parent counselling due to frequent absence streaks:
          </p>

          <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
            {data?.chronic_absentees && data.chronic_absentees.length > 0 ? (
              data.chronic_absentees.map((item) => (
                <div
                  key={item.student_id}
                  className="p-3.5 rounded-xl bg-slate-900/80 border border-rose-500/20 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-bold text-slate-200">{item.full_name}</div>
                    <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                      ID: {item.student_id.slice(0, 13)}...
                    </div>
                  </div>
                  <span className="px-2.5 py-1 bg-rose-500/20 text-rose-300 font-black rounded-lg border border-rose-500/40 text-xs">
                    {item.absent_days} Days
                  </span>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-slate-400">
                No students exceeded chronic absence threshold.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
