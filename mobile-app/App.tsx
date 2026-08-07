import React, { useState } from 'react';
import { StyleSheet, View, StatusBar } from 'react-native';
import { TenantConfigProvider } from './src/config/TenantConfigContext';
import { AuthProvider, useMobileAuth } from './src/context/AuthContext';
import { LoginScreen } from './src/features/auth/LoginScreen';
import { DailyScheduleScreen } from './src/features/timetable/DailyScheduleScreen';
import { MarkAttendanceScreen } from './src/features/attendance/MarkAttendanceScreen';
import { NotificationsScreen } from './src/features/notifications/NotificationsScreen';
import { ParentHomeScreen } from './src/features/parent/ParentHomeScreen';
import { StudentHomeScreen } from './src/features/student/StudentHomeScreen';
import { NavigationBar } from './src/components/NavigationBar';

const MainAppContent: React.FC = () => {
  const { user, isAuthenticated } = useMobileAuth();
  const [currentTab, setCurrentTab] = useState<string>('schedule');
  const [selectedSection, setSelectedSection] = useState<string>('10-A');

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  // Parent Role Routing
  if (user?.role === 'parent') {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#0F172A" />
        <View style={styles.content}>
          {currentTab === 'notifications' ? <NotificationsScreen /> : <ParentHomeScreen />}
        </View>
        <NavigationBar currentTab={currentTab} onSelectTab={setCurrentTab} />
      </View>
    );
  }

  // Student Role Routing
  if (user?.role === 'student') {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#0F172A" />
        <View style={styles.content}>
          {currentTab === 'notifications' ? <NotificationsScreen /> : <StudentHomeScreen />}
        </View>
        <NavigationBar currentTab={currentTab} onSelectTab={setCurrentTab} />
      </View>
    );
  }

  // Default Teacher / Admin Routing
  const handleNavigateToMark = (sec: string) => {
    setSelectedSection(sec);
    setCurrentTab('attendance');
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0F172A" />

      <View style={styles.content}>
        {currentTab === 'schedule' && (
          <DailyScheduleScreen onNavigateToMark={handleNavigateToMark} />
        )}

        {currentTab === 'attendance' && (
          <MarkAttendanceScreen selectedSection={selectedSection} />
        )}

        {currentTab === 'notifications' && (
          <NotificationsScreen />
        )}
      </View>

      <NavigationBar currentTab={currentTab} onSelectTab={setCurrentTab} />
    </View>
  );
};

export default function App() {
  return (
    <TenantConfigProvider>
      <AuthProvider>
        <MainAppContent />
      </AuthProvider>
    </TenantConfigProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  content: {
    flex: 1,
  },
});
