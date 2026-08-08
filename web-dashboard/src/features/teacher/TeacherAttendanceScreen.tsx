import React, { useState, useEffect } from 'react';
import { 
  ClipboardCheck, 
  Send, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  AlertCircle,
  FileText,
  ShieldCheck
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import type { Student } from '../../types';

export const TeacherAttendanceScreen: React.FC = () => {
  const { user } = useAuth();
  const assignedSections = user?.assigned_sections || ['10-A'];
  const [selectedSection, setSelectedSection] = useState<string>(assignedSections[0] || '10-A');
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [attendanceMap, setAttendanceMap] = useState<Record<string, 'P' | 'A' | 'L'>>({});
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Manual Override Modal state
  const [overrideStudent, setOverrideStudent] = useState<Student | null>(null);
  const [overrideStatus, setOverrideStatus] = useState<'P' | 'A' | 'L'>('P');
  const [overrideReason, setOverrideReason] = useState<string>('');

  useEffect(() => {
    const fetchStudents = async () => {
      setLoading(true);
      setSuccessMsg(null);
      try {
        const res = await apiClient.get(`/students?section=${selectedSection}&page_size=100`);
        const list: Student[] = res.data?.items || [];
        setStudents(list);

        // Default all to Present 'P'
        const initial: Record<string, 'P' | 'A' | 'L'> = {};
        list.forEach((s) => {
          initial[s.id] = 'P';
        });
        setAttendanceMap(initial);
      } catch (err) {
        console.error('Error fetching section students:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStudents();
  }, [selectedSection]);

  const handleStatusChange = (studentId: string, status: 'P' | 'A' | 'L') => {
    setAttendanceMap((prev) => ({ ...prev, [studentId]: status }));
  };

  const handleOpenOverride = (student: Student) => {
    setOverrideStudent(student);
    setOverrideStatus(attendanceMap[student.id] || 'P');
    setOverrideReason('');
  };

  const handleApplyOverride = () => {
    if (!overrideStudent || !overrideReason.trim()) return;
    setAttendanceMap((prev) => ({ ...prev, [overrideStudent.id]: overrideStatus }));
    setOverrideStudent(null);
  };

  const handleSubmitAttendance = async () => {
    setSubmitting(true);
    setSuccessMsg(null);
    try {
      const signals = students.map((s) => ({
        student_id: s.id,
        class_section_id: s.class_section,
        status: attendanceMap[s.id] || 'P',
        source: 'TEACHER_WEB_DASHBOARD',
        notes: `Section ${selectedSection} submitted by ${user?.full_name || 'Teacher'}`,
      }));

      const res = await apiClient.post('/attendance/submit', { signals });
      setSuccessMsg(`Successfully saved attendance for ${res.data.ingested_count || signals.length} students!`);
    } catch (err) {
      console.error('Error submitting attendance:', err);
      alert('Failed to submit attendance. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const presentCount = Object.values(attendanceMap).filter((v) => v === 'P').length;
  const absentCount = Object.values(attendanceMap).filter((v) => v === 'A').length;
  const lateCount = Object.values(attendanceMap).filter((v) => v === 'L').length;

  return (
    <div className="space-y-6">
      {/* Header & Section Selector */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <ClipboardCheck className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">Mark Class Attendance</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Teacher: <strong className="text-slate-200">{user?.full_name}</strong> • Low-Latency Fast Tap Grid
          </p>
        </div>

        {/* Section Restricter (Teacher assigned sections only) */}
        <div className="flex items-center space-x-3">
          <label className="text-xs text-slate-400 font-semibold uppercase">Assigned Section:</label>
          <select
            value={selectedSection}
            onChange={(e) => setSelectedSection(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs font-bold text-white focus:outline-none focus:border-indigo-500"
          >
            {assignedSections.map((sec) => (
              <option key={sec} value={sec}>
                Class {sec}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Quick Summary Pill Bar */}
      <div className="grid grid-cols-3 gap-3">
        <div className="glass-panel p-3.5 rounded-xl border border-emerald-500/20 bg-emerald-950/20 flex items-center justify-between">
          <span className="text-xs font-semibold text-emerald-400 flex items-center space-x-1.5">
            <CheckCircle2 className="w-4 h-4" />
            <span>Present:</span>
          </span>
          <span className="text-lg font-black text-emerald-300">{presentCount}</span>
        </div>
        <div className="glass-panel p-3.5 rounded-xl border border-rose-500/20 bg-rose-950/20 flex items-center justify-between">
          <span className="text-xs font-semibold text-rose-400 flex items-center space-x-1.5">
            <XCircle className="w-4 h-4" />
            <span>Absent:</span>
          </span>
          <span className="text-lg font-black text-rose-300">{absentCount}</span>
        </div>
        <div className="glass-panel p-3.5 rounded-xl border border-amber-500/20 bg-amber-950/20 flex items-center justify-between">
          <span className="text-xs font-semibold text-amber-400 flex items-center space-x-1.5">
            <Clock className="w-4 h-4" />
            <span>Late:</span>
          </span>
          <span className="text-lg font-black text-amber-300">{lateCount}</span>
        </div>
      </div>

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Student Attendance List */}
      {loading ? (
        <LoadingSpinner text="Loading class roster..." />
      ) : (
        <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
          <div className="divide-y divide-slate-800/60">
            {students.map((student) => {
              const currentStatus = attendanceMap[student.id] || 'P';
              return (
                <div
                  key={student.id}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-900/40 transition"
                >
                  <div className="flex items-center space-x-3">
                    <span className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-300">
                      {student.roll_number}
                    </span>
                    <div>
                      <h4 className="text-sm font-semibold text-white">{student.full_name}</h4>
                      <p className="text-xs text-slate-400">
                        Roll #{student.roll_number} • Guardian: {student.guardian_name || 'N/A'}
                      </p>
                    </div>
                  </div>

                  {/* Tri-State Action Buttons */}
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleStatusChange(student.id, 'P')}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                        currentStatus === 'P'
                          ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                          : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                      }`}
                    >
                      P
                    </button>
                    <button
                      onClick={() => handleStatusChange(student.id, 'A')}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                        currentStatus === 'A'
                          ? 'bg-rose-600 text-white shadow-md shadow-rose-600/30'
                          : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                      }`}
                    >
                      A
                    </button>
                    <button
                      onClick={() => handleStatusChange(student.id, 'L')}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                        currentStatus === 'L'
                          ? 'bg-amber-600 text-white shadow-md shadow-amber-600/30'
                          : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                      }`}
                    >
                      L
                    </button>

                    {/* Manual Override Button */}
                    <button
                      onClick={() => handleOpenOverride(student)}
                      title="Manual Override with Justification"
                      className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-amber-300 border border-slate-800"
                    >
                      <FileText className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Submit Action Footer */}
          <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
            <span className="text-xs text-slate-400">
              Total: <strong>{students.length}</strong> Students in Class {selectedSection}
            </span>
            <button
              onClick={handleSubmitAttendance}
              disabled={submitting || students.length === 0}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:opacity-95 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 flex items-center space-x-2 disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>{submitting ? 'Submitting...' : 'Submit Attendance'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Manual Override Dialog Modal */}
      {overrideStudent && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md p-6 rounded-3xl border border-slate-800 shadow-2xl space-y-4">
            <div className="flex items-center space-x-2 text-amber-400">
              <ShieldCheck className="w-5 h-5" />
              <h3 className="font-bold text-base text-white">Attendance Override Justification</h3>
            </div>
            <p className="text-xs text-slate-400">
              Student: <strong className="text-slate-200">{overrideStudent.full_name}</strong> (Roll #{overrideStudent.roll_number})
            </p>

            <div className="space-y-2">
              <label className="text-xs text-slate-300 font-semibold">New Status:</label>
              <div className="flex gap-2">
                {(['P', 'A', 'L'] as const).map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setOverrideStatus(st)}
                    className={`flex-1 py-2 rounded-xl text-xs font-bold border transition ${
                      overrideStatus === st
                        ? 'bg-indigo-600 text-white border-indigo-500'
                        : 'bg-slate-900 text-slate-400 border-slate-800'
                    }`}
                  >
                    {st === 'P' ? 'Present' : st === 'A' ? 'Absent' : 'Late'}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-slate-300 font-semibold">Reason for Override (Required):</label>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="e.g. Medical leave approved by principal..."
                rows={3}
                className="w-full p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setOverrideStudent(null)}
                className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 hover:text-white text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApplyOverride}
                disabled={!overrideReason.trim()}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold disabled:opacity-50"
              >
                Apply Override
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
