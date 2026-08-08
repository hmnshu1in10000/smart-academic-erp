import React, { useState, useEffect } from 'react';
import { CalendarDays, Clock, MapPin, BookOpen, User, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import type { TimetableEntry } from '../../types';

export const TeacherScheduleScreen: React.FC = () => {
  const { user } = useAuth();
  const [schedule, setSchedule] = useState<TimetableEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeDay, setActiveDay] = useState<string>('MON');

  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  const teacherSections = user?.assigned_sections || ['10-A'];

  useEffect(() => {
    const fetchTimetable = async () => {
      setLoading(true);
      try {
        // Fetch first student in teacher's section to retrieve class timetable
        const res = await apiClient.get(`/students?section=${teacherSections[0]}&page_size=1`);
        const firstStudent = res.data?.items?.[0];
        if (firstStudent) {
          const ttRes = await apiClient.get(`/students/${firstStudent.id}/timetable`);
          setSchedule(ttRes.data || []);
        }
      } catch (err) {
        console.error('Error fetching timetable:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTimetable();
  }, [teacherSections]);

  const filteredSchedule = schedule.filter((item) => item.day === activeDay);

  // Check if period is currently active based on client local time
  const isPeriodNow = (startTime: string, endTime: string): boolean => {
    const now = new Date();
    const [startH, startM] = startTime.split(':').map(Number);
    const [endH, endM] = endTime.split(':').map(Number);
    const curMinutes = now.getHours() * 60 + now.getMinutes();
    const startMinutes = startH * 60 + startM;
    const endMinutes = endH * 60 + endM;
    return curMinutes >= startMinutes && curMinutes <= endMinutes;
  };

  if (loading) {
    return <LoadingSpinner text="Loading teacher schedule..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <CalendarDays className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">Teacher Daily Timetable</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Instructor: <strong className="text-indigo-300">{user?.full_name || 'Rajesh Kumar'}</strong> • Assigned Section: <span className="text-amber-400 font-semibold">{teacherSections.join(', ')}</span>
          </p>
        </div>

        {/* Day Selector Tabs */}
        <div className="flex bg-slate-900/80 p-1 rounded-xl border border-slate-800 gap-1 overflow-x-auto">
          {days.map((d) => (
            <button
              key={d}
              onClick={() => setActiveDay(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeDay === d
                  ? 'bg-[var(--color-primary)] text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Schedule Period Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredSchedule.length === 0 ? (
          <div className="col-span-full glass-panel p-8 rounded-2xl text-center text-slate-400 text-sm">
            No class periods scheduled for {activeDay}.
          </div>
        ) : (
          filteredSchedule.map((entry) => {
            const active = isPeriodNow(entry.start_time, entry.end_time);
            return (
              <div
                key={`${entry.day}-${entry.period}`}
                className={`glass-panel p-5 rounded-2xl border transition-all duration-200 ${
                  active
                    ? 'border-emerald-500/60 bg-emerald-950/20 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/40'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="px-2 py-0.5 rounded-md bg-slate-800 text-[11px] font-bold text-slate-300">
                    Period {entry.period}
                  </span>
                  {active ? (
                    <span className="flex items-center space-x-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/30 animate-pulse">
                      <Sparkles className="w-3 h-3" />
                      <span>IN PROGRESS</span>
                    </span>
                  ) : (
                    <span className="text-[11px] font-mono text-slate-400 flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{entry.start_time} - {entry.end_time}</span>
                    </span>
                  )}
                </div>

                <div className="space-y-2">
                  <h3 className="font-bold text-white text-base flex items-center space-x-2">
                    <BookOpen className="w-4 h-4 text-indigo-400" />
                    <span>{entry.subject}</span>
                  </h3>
                  <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/60">
                    <span className="flex items-center space-x-1">
                      <MapPin className="w-3.5 h-3.5 text-amber-400" />
                      <span>Room: <strong className="text-slate-200">{entry.room}</strong></span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <User className="w-3.5 h-3.5 text-slate-400" />
                      <span>{entry.teacher}</span>
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
