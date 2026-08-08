// web-dashboard/src/config/roleNavigation.ts
// ============================================
// Single source of truth for role-based navigation configuration.
// Every routing decision in App.tsx and Sidebar.tsx reads from here.
// No inline role === '...' checks scattered across components.
import {
  LayoutDashboard,
  Users,
  CalendarCheck,
  CreditCard,
  Sparkles,
  ClipboardCheck,
  CalendarDays,
  GraduationCap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type AppRole = 'admin' | 'principal' | 'teacher' | 'student' | 'parent';

export interface NavItemConfig {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
  isAI?: boolean;
}

export const ROLE_NAV_CONFIG: Record<AppRole, NavItemConfig[]> = {
  admin: [
    { id: 'dashboard', label: 'Dashboard Overview', icon: LayoutDashboard },
    { id: 'students', label: 'Students & Roster', icon: Users },
    { id: 'attendance', label: 'Attendance Insights', icon: CalendarCheck },
    { id: 'fees', label: 'Fee Management', icon: CreditCard },
    { id: 'ai-analytics', label: 'AI Chat Query Engine', icon: Sparkles, badge: 'PRO', isAI: true },
  ],
  principal: [
    { id: 'dashboard', label: 'Dashboard Overview', icon: LayoutDashboard },
    { id: 'students', label: 'Students & Roster', icon: Users },
    { id: 'attendance', label: 'Attendance Insights', icon: CalendarCheck },
    { id: 'fees', label: 'Fee Management', icon: CreditCard },
    { id: 'ai-analytics', label: 'AI Chat Query Engine', icon: Sparkles, badge: 'PRO', isAI: true },
  ],
  teacher: [
    { id: 'teacher-schedule', label: 'My Schedule', icon: CalendarDays },
    { id: 'teacher-attendance', label: 'Mark Attendance', icon: ClipboardCheck },
    { id: 'ai-analytics', label: 'AI Chat Query Engine', icon: Sparkles, badge: 'PRO', isAI: true },
  ],
  student: [
    { id: 'student-academics', label: 'Academic & Grades', icon: GraduationCap },
    { id: 'student-attendance', label: 'My Attendance', icon: CalendarCheck },
    { id: 'student-fees', label: 'My Fee Account', icon: CreditCard },
    { id: 'ai-analytics', label: 'Ask About My Records', icon: Sparkles, isAI: true },
  ],
  parent: [
    { id: 'parent-academics', label: "Child's Academics", icon: GraduationCap },
    { id: 'parent-attendance', label: "Child's Attendance", icon: CalendarCheck },
    { id: 'parent-fees', label: "Child's Fee Account", icon: CreditCard },
    { id: 'ai-analytics', label: 'Ask About My Child', icon: Sparkles, isAI: true },
  ],
};

export const DEFAULT_TAB_BY_ROLE: Record<AppRole, string> = {
  admin: 'dashboard',
  principal: 'dashboard',
  teacher: 'teacher-schedule',
  student: 'student-academics',
  parent: 'parent-academics',
};

/**
 * Normalise a raw role string to a known AppRole.
 * Fails closed to 'student' (most restrictive non-admin role) — never to 'admin'.
 */
export function normalizeRole(rawRole: string | undefined): AppRole {
  const r = (rawRole || '').toLowerCase();
  if (r === 'admin' || r === 'principal' || r === 'teacher' || r === 'student' || r === 'parent') {
    return r as AppRole;
  }
  return 'student'; // fail closed
}
