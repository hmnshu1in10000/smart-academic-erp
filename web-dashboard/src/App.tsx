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

const MainContent: React.FC = () => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <Layout>
      {(activeTab, setActiveTab) => {
        switch (activeTab) {
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
          default:
            return <OverviewDashboard setActiveTab={setActiveTab} />;
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
