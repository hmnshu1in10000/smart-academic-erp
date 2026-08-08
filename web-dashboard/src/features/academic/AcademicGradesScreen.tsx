import React, { useState, useEffect } from 'react';
import { 
  GraduationCap, 
  Award, 
  TrendingUp, 
  BookOpen, 
  CalendarCheck, 
  UserCheck 
} from 'lucide-react';
import { apiClient } from '../../api/client';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import type { PersonalAcademicSummary, AcademicSubjectGrade } from '../../types';

interface AcademicGradesScreenProps {
  viewerRole: 'student' | 'parent' | string;
}

export const AcademicGradesScreen: React.FC<AcademicGradesScreenProps> = ({ viewerRole }) => {
  const [summary, setSummary] = useState<PersonalAcademicSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchGrades = async () => {
      setLoading(true);
      try {
        const endpoint = viewerRole === 'parent' ? '/parent/academic-summary' : '/student/academic-summary';
        const res = await apiClient.get(endpoint);
        setSummary(res.data);
      } catch (err) {
        console.error('Error fetching academic report card:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchGrades();
  }, [viewerRole]);

  if (loading) {
    return <LoadingSpinner text="Loading academic report card..." />;
  }

  if (!summary) {
    return (
      <div className="glass-panel p-8 rounded-2xl text-center text-slate-400 text-sm">
        No academic record found for this profile.
      </div>
    );
  }

  const grades = summary.report_card || [];
  const avgScore = grades.length > 0
    ? Math.round(grades.reduce((acc, curr) => acc + curr.score_pct, 0) / grades.length)
    : 0;

  return (
    <div className="space-y-6">
      {/* Student Profile & Overview Header */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <GraduationCap className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">
              {viewerRole === 'parent' ? "Child's Academic Report Card" : "My Academic Report Card"}
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Student: <strong className="text-white">{summary.student_name}</strong> • Roll #{summary.roll_number} • Section: <span className="text-amber-400 font-semibold">{summary.section}</span>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right">
            <div className="text-[10px] uppercase font-bold text-slate-400">Overall Average</div>
            <div className="text-2xl font-black text-emerald-400">{avgScore}%</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <Award className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Overall Attendance Rate</span>
            <CalendarCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">{summary.attendance_rate_pct}%</div>
          <p className="text-[11px] text-slate-500">Target requirement: ≥75%</p>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Enrolled Subjects</span>
            <BookOpen className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">{grades.length} Courses</div>
          <p className="text-[11px] text-slate-500">CBSE Curriculum Grade 10</p>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Timetable Classes / Week</span>
            <TrendingUp className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">{summary.timetable_count || 25} Periods</div>
          <p className="text-[11px] text-slate-500">Active class schedule</p>
        </div>
      </div>

      {/* Grades Table */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="font-bold text-sm text-white">Subject Evaluation & Grade Matrix</h3>
          <span className="text-[11px] font-semibold text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
            Academic Term 2026
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Subject</th>
                <th className="py-3 px-4">Teacher / Department</th>
                <th className="py-3 px-4 text-center">Score (%)</th>
                <th className="py-3 px-4 text-center">Grade</th>
                <th className="py-3 px-4 text-right">Performance Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {grades.map((item: AcademicSubjectGrade) => (
                <tr key={item.subject_name} className="hover:bg-slate-900/40 transition">
                  <td className="py-3.5 px-4 font-bold text-white flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                    <span>{item.subject_name}</span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">{item.teacher_name}</td>
                  <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-200">
                    {item.score_pct}%
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <span className={`inline-block px-2 py-0.5 rounded font-black text-xs ${
                      item.grade.startsWith('A')
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                    }`}>
                      {item.grade}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <span className="text-[11px] text-slate-400">
                      {item.score_pct >= 90 ? 'Outstanding' : item.score_pct >= 80 ? 'Proficient' : 'Standard'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
