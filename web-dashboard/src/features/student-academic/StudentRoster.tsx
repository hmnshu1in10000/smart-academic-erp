import React, { useEffect, useState } from 'react';
import { Search, Calendar, Users, UserCheck, ChevronLeft, ChevronRight } from 'lucide-react';
import { apiClient } from '../../api/client';
import type { Student, TimetableEntry } from '../../types';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

export const StudentRoster: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [sectionFilter, setSectionFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [timetable, setTimetable] = useState<TimetableEntry[] | null>(null);
  const [timetableLoading, setTimetableLoading] = useState<boolean>(false);

  const fetchStudents = async () => {
    setLoading(true);
    try {
      let url = `/students?page=${page}&page_size=10`;
      if (sectionFilter) {
        url += `&section=${encodeURIComponent(sectionFilter)}`;
      }
      const res = await apiClient.get(url);
      setStudents(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      console.error('Failed to fetch students:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, [page, sectionFilter]);

  const handleSelectStudent = async (student: Student) => {
    setSelectedStudent(student);
    setTimetableLoading(true);
    try {
      const res = await apiClient.get<TimetableEntry[]>(`/students/${student.id}/timetable`);
      setTimetable(res.data);
    } catch (err) {
      console.error('Failed to load timetable:', err);
    } finally {
      setTimetableLoading(false);
    }
  };

  const filteredStudents = students.filter(s => 
    s.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.roll_number.toString().includes(searchQuery)
  );

  return (
    <div className="space-y-6">
      {/* Top Filter Bar */}
      <div className="glass-panel p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          {/* Search Box */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by student name..."
              className="w-full pl-9 pr-4 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[var(--color-primary)] transition"
            />
          </div>

          {/* Section Filter */}
          <div className="flex items-center space-x-1.5 bg-slate-900/80 p-1 border border-slate-800 rounded-xl">
            {['', '10-A', '10-B'].map((sec) => (
              <button
                key={sec}
                onClick={() => { setSectionFilter(sec); setPage(1); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  sectionFilter === sec
                    ? 'bg-[var(--color-primary)] text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {sec ? `Class ${sec}` : 'All Sections'}
              </button>
            ))}
          </div>
        </div>

        <div className="text-xs text-slate-400 font-medium">
          Showing <strong className="text-white">{filteredStudents.length}</strong> of {total} Students
        </div>
      </div>

      {/* Main Grid: Student Table + Timetable Side Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Roster Table */}
        <div className="lg:col-span-2 glass-panel rounded-2xl border border-slate-800/80 overflow-hidden flex flex-col">
          <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="font-bold text-sm text-white flex items-center space-x-2">
              <Users className="w-4 h-4 text-[var(--color-secondary)]" />
              <span>Student Roster Directory</span>
            </h3>
            <span className="text-xs text-slate-400">Click a student to view timetable</span>
          </div>

          {loading ? (
            <LoadingSpinner message="Fetching student records..." />
          ) : (
            <div className="overflow-x-auto flex-1">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider font-semibold border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-3">Roll</th>
                    <th className="px-6 py-3">Student Name</th>
                    <th className="px-6 py-3">Class</th>
                    <th className="px-6 py-3">Guardian</th>
                    <th className="px-6 py-3">Contact</th>
                    <th className="px-6 py-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredStudents.map((student) => {
                    const isSelected = selectedStudent?.id === student.id;
                    return (
                      <tr
                        key={student.id}
                        onClick={() => handleSelectStudent(student)}
                        className={`cursor-pointer transition hover:bg-slate-800/50 ${
                          isSelected ? 'bg-slate-800/80 border-l-4 border-l-[var(--color-secondary)]' : ''
                        }`}
                      >
                        <td className="px-6 py-3.5 font-mono font-bold text-slate-400">
                          #{String(student.roll_number).padStart(2, '0')}
                        </td>
                        <td className="px-6 py-3.5 font-semibold text-white">
                          {student.full_name}
                        </td>
                        <td className="px-6 py-3.5">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-indigo-300 text-[11px] font-medium border border-slate-700">
                            {student.class_section}
                          </span>
                        </td>
                        <td className="px-6 py-3.5 text-slate-400">
                          {student.guardian_name || 'N/A'}
                        </td>
                        <td className="px-6 py-3.5 text-slate-400 font-mono text-[11px]">
                          {student.guardian_phone || 'N/A'}
                        </td>
                        <td className="px-6 py-3.5 text-right">
                          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-bold border border-emerald-500/20">
                            {student.enrollment_status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          <div className="p-4 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between text-xs text-slate-400">
            <span>Page {page} of {Math.ceil(total / 10)}</span>
            <div className="flex space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={page >= Math.ceil(total / 10)}
                onClick={() => setPage(p => p + 1)}
                className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Timetable Schedule View Panel */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-bold text-sm text-white flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-amber-400" />
              <span>Academic Timetable</span>
            </h3>
            {selectedStudent && (
              <span className="text-xs text-indigo-300 font-medium">
                {selectedStudent.class_section}
              </span>
            )}
          </div>

          {selectedStudent ? (
            timetableLoading ? (
              <LoadingSpinner message="Loading timetable..." />
            ) : timetable ? (
              <div className="space-y-3">
                <div className="text-xs font-semibold text-white bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                  Timetable Schedule for: <strong className="text-amber-400">{selectedStudent.full_name}</strong>
                </div>

                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {timetable.map((t, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between text-xs"
                    >
                      <div>
                        <div className="font-bold text-white flex items-center space-x-2">
                          <span className="w-10 text-[10px] bg-slate-800 text-amber-400 px-1.5 py-0.5 rounded text-center">
                            {t.day} P{t.period}
                          </span>
                          <span>{t.subject}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 mt-1">
                          Teacher: {t.teacher} &bull; Room: {t.room}
                        </div>
                      </div>
                      <span className="font-mono text-[10px] text-slate-400 bg-slate-950 px-2 py-1 rounded">
                        {t.start_time}-{t.end_time}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null
          ) : (
            <div className="py-16 text-center text-xs text-slate-400 space-y-2">
              <UserCheck className="w-8 h-8 mx-auto text-slate-600" />
              <p>Select any student from the roster table to view their weekly timetable schedule.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
