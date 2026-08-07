// Mobile App Shared TypeScript Type Definitions

export interface MobileThemeTokens {
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
  logoUri?: string;
}

export interface MobileTenantConfig {
  tenant_id: string;
  school_name: string;
  tagline: string | null;
  theme: MobileThemeTokens;
}

export interface MobileUser {
  sub: string;
  role: string;
  full_name: string;
  tenant_id: string;
}

export interface StudentAttendanceItem {
  id: string;
  roll_number: number;
  full_name: string;
  status: 'P' | 'A' | 'L';
  hasOverride?: boolean;
  overrideNotes?: string;
}

export interface AttendanceSignalPayload {
  signal_id: string;
  student_id: string;
  class_section_id: string;
  timestamp: string;
  status: 'P' | 'A' | 'L';
  confidence_score: number;
  source: string;
  notes?: string;
}

export interface OfflineQueueItem {
  id: string;
  timestamp: string;
  signals: AttendanceSignalPayload[];
  retryCount: number;
}

export interface TimetablePeriod {
  period: number;
  day: string;
  subject: string;
  section: string;
  start_time: string;
  end_time: string;
  room: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  type: 'ALERT' | 'INFO' | 'URGENT';
  read: boolean;
}
