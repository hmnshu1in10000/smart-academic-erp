import React from 'react';
import { ThemeProvider } from './config/ThemeProvider';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Layout } from './components/layout/Layout';
import { LoginPage } from './features/auth/LoginPage';
import { OverviewDashboard } from './features/dashboard/OverviewDashboard';
import { StudentRoster } from './features/student-academic/StudentRoster';
import { AttendanceAnalytics } from './features/attendance/AttendanceAnalytics';
import { FeeDashboard } from './features/fee-management/FeeDashboard';
import { ChatQueryBox } from './features/ai-analytics/ChatQueryBox';

import { ROLE_NAV_CONFIG, DEFAULT_TAB_BY_ROLE, normalizeRole } from './config/roleNavigation';
import { TeacherScheduleScreen } from './features/teacher/TeacherScheduleScreen';
import { TeacherAttendanceScreen } from './features/teacher/TeacherAttendanceScreen';
import { AcademicGradesScreen } from './features/academic/AcademicGradesScreen';
import { PersonalAttendanceScreen } from './features/attendance/PersonalAttendanceScreen';
import { PersonalFeeScreen } from './features/fee-management/PersonalFeeScreen';

const MainContent: React.FC = () => {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const role = normalizeRole(user?.role);
  const allowedTabIds = new Set(ROLE_NAV_CONFIG[role].map((i) => i.id));
  const defaultTab = DEFAULT_TAB_BY_ROLE[role] || 'dashboard';

  return (
    <Layout defaultTab={defaultTab}>
      {(activeTab, setActiveTab) => {
        // Hard guard: never render a tab this role isn't entitled to.
        const tab = allowedTabIds.has(activeTab) ? activeTab : defaultTab;

        switch (tab) {
          case 'dashboard':
            return <OverviewDashboard setActiveTab={setActiveTab} />;
          case 'students':
            return <StudentRoster />;
          case 'attendance':
            return <AttendanceAnalytics />;
          case 'fees':
            return <FeeDashboard />;
          case 'ai-analytics':
            return <ChatQueryBox />;

          case 'teacher-schedule':
            return <TeacherScheduleScreen />;
          case 'teacher-attendance':
            return <TeacherAttendanceScreen />;

          case 'student-academics':
          case 'parent-academics':
            return <AcademicGradesScreen viewerRole={role} />;

          case 'student-attendance':
          case 'parent-attendance':
            return <PersonalAttendanceScreen viewerRole={role} />;

          case 'student-fees':
          case 'parent-fees':
            return <PersonalFeeScreen viewerRole={role} />;

          default:
            return <AcademicGradesScreen viewerRole={role} />;
        }
      }}
    </Layout>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <MainContent />
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
