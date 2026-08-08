// Shared Type Definitions for Smart Academic ERP Dashboard

export type AppRole = 'admin' | 'principal' | 'teacher' | 'student' | 'parent';

export interface ThemeTokens {
  primary: string;
  secondary: string;
  accent: string;
  success: string;
  warning: string;
  error: string;
  font_family_heading: string;
  font_family_body: string;
  logo_url: string;
  favicon_url: string;
}

export interface FeatureFlags {
  biometric_attendance_enabled: boolean;
  ai_analytics_enabled: boolean;
  parent_mobile_app_enabled: boolean;
  online_fee_payment_enabled: boolean;
  library_module_enabled: boolean;
}

export interface TenantConfig {
  tenant_id: string;
  school_name: string;
  tagline: string | null;
  city: string;
  country: string;
  board: string;
  academic_year: string;
  currency_symbol: string;
  timezone: string;
  theme: ThemeTokens;
  features: FeatureFlags;
}

export interface User {
  sub: string;
  role: AppRole;
  full_name: string;
  tenant_id: string;
  assigned_sections?: string[];  // present only for role === 'teacher'
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

export interface Student {
  id: string;
  roll_number: number;
  full_name: string;
  gender: string;
  class_section: string;
  guardian_name?: string;
  guardian_phone?: string;
  enrollment_status: string;
  dob?: string;
  blood_group?: string;
  phone?: string;
  email?: string;
  address?: string;
}

export interface TimetableEntry {
  day: string;
  period: number;
  subject: string;
  teacher: string;
  start_time: string;
  end_time: string;
  room: string;
}

export interface DailyAttendanceStat {
  date: string;
  section: string;
  total: number;
  present: number;
  absent: number;
  late: number;
  attendance_pct: number;
}

export interface ChronicAbsentee {
  student_id: string;
  full_name: string;
  absent_days: number;
}

export interface AttendanceSummary {
  tenant_id: string;
  section?: string;
  from_date: string;
  to_date: string;
  daily_stats: DailyAttendanceStat[];
  overall_present_pct: number;
  chronic_absentees: ChronicAbsentee[];
}

export interface FeeInvoice {
  id: string;
  student_id: string;
  student_name: string;
  section: string;
  fee_head: string;
  term_label: string;
  amount_due: number;
  amount_paid: number;
  outstanding: number;
  due_date: string;
  paid_date?: string;
  status: 'PAID' | 'PENDING' | 'OVERDUE' | 'PARTIAL';
  payment_method?: string;
  transaction_ref?: string;
}

export interface FeeSummary {
  tenant_id: string;
  total_billed: number;
  total_collected: number;
  total_outstanding: number;
  collection_rate_pct: number;
  paid_count: number;
  pending_count: number;
  overdue_count: number;
  partial_count: number;
}

// ── AI Analytics types (correction.md §4.4) ─────────────────────────────────

export interface ChatTurnPayload {
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
}

export interface AskQueryRequest {
  query: string;
  chat_history: ChatTurnPayload[];
  debug_mode: boolean;
}

export interface RawDataTable {
  columns: string[];
  rows: any[][];
}

export interface AIQueryResponse {
  question: string;
  summary_answer: string;
  columns: string[];
  rows: any[][];
  row_count: number;
  error?: string;
  // Present only when debug_mode is active AND server ENVIRONMENT == "development":
  generated_sql?: string;
  explanation?: string;
  raw_data_table?: RawDataTable;
  execution_time_ms?: number;
}

// ── Academic summary types (new — correction.md §4.4) ────────────────────────

export interface AcademicSubjectGrade {
  subject_name: string;
  teacher_name: string;
  grade: string;
  score_pct: number;
}

export interface PersonalAcademicSummary {
  student_id: string;
  student_name: string;
  section: string;
  roll_number: number;
  attendance_rate_pct: number;
  report_card: AcademicSubjectGrade[];
  timetable_count: number;
}
