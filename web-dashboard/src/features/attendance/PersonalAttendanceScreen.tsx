import React, { useState, useEffect } from 'react';
import { 
  CalendarCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  UserCheck 
} from 'lucide-react';
import { apiClient } from '../../api/client';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

interface StudentAttendanceDay {
  date: string;
  status: string; // P / A / L
  source: string;
}

interface StudentAttendanceHistory {
  student_id: string;
  full_name: string;
  section: string;
  total_days: int;
  present: int;
  absent: int;
  late: int;
  attendance_pct: number;
  history: StudentAttendanceDay[];
}

interface PersonalAttendanceScreenProps {
  viewerRole: 'student' | 'parent' | string;
}

export const PersonalAttendanceScreen: React.FC<PersonalAttendanceScreenProps> = ({ viewerRole }) => {
  const [data, setData] = useState<StudentAttendanceHistory | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const endpoint = viewerRole === 'parent' ? '/attendance/my-child' : '/attendance/me';
        const res = await apiClient.get(endpoint);
        setData(res.data);
      } catch (err) {
        console.error('Error fetching personal attendance:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [viewerRole]);

  if (loading) {
    return <LoadingSpinner text="Loading attendance history..." />;
  }

  if (!data) {
    return (
      <div className="glass-panel p-8 rounded-2xl text-center text-slate-400 text-sm">
        No attendance record found for this profile.
      </div>
    );
  }

  const isChronic = data.absent >= 5;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <CalendarCheck className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">
              {viewerRole === 'parent' ? "Child's Attendance Record" : "My Attendance Record"}
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Student: <strong className="text-white">{data.full_name}</strong> • Section: <span className="text-amber-400 font-semibold">{data.section}</span>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right">
            <div className="text-[10px] uppercase font-bold text-slate-400">Attendance Rate</div>
            <div className={`text-2xl font-black ${data.attendance_pct >= 75 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {data.attendance_pct}%
            </div>
          </div>
        </div>
      </div>

      {/* Chronic Absentee Warning Banner */}
      {isChronic && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-3 shadow-lg shadow-rose-500/5">
          <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0" />
          <div>
            <strong className="font-bold">Chronic Absence Alert:</strong> You have {data.absent} recorded absences this term. School policy requires attendance above 75% for exam qualification.
          </div>
        </div>
      )}

      {/* KPI Counters */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass-panel p-4 rounded-2xl border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-semibold">Total Days Present</span>
            <div className="text-2xl font-black text-emerald-400 mt-0.5">{data.present}</div>
          </div>
          <CheckCircle2 className="w-6 h-6 text-emerald-500/40" />
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-semibold">Total Days Absent</span>
            <div className="text-2xl font-black text-rose-400 mt-0.5">{data.absent}</div>
          </div>
          <XCircle className="w-6 h-6 text-rose-500/40" />
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-semibold">Late Arrivals</span>
            <div className="text-2xl font-black text-amber-400 mt-0.5">{data.late}</div>
          </div>
          <Clock className="w-6 h-6 text-amber-500/40" />
        </div>
      </div>

      {/* Scrollable Daily Attendance Log */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="font-bold text-sm text-white">Daily Attendance Log (Last 30 Days)</h3>
          <span className="text-xs text-slate-400">{data.history.length} Sessions Logged</span>
        </div>

        <div className="divide-y divide-slate-800/60 max-h-96 overflow-y-auto">
          {data.history.map((day, idx) => (
            <div key={`${day.date}-${idx}`} className="p-3.5 px-5 flex items-center justify-between hover:bg-slate-900/40 transition">
              <div className="flex items-center space-x-3">
                <span className="font-mono text-xs text-slate-300 font-semibold">{day.date}</span>
                <span className="text-[11px] text-slate-500">Source: {day.source}</span>
              </div>
              <div>
                {day.status === 'P' ? (
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    PRESENT
                  </span>
                ) : day.status === 'A' ? (
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    ABSENT
                  </span>
                ) : (
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    LATE
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
