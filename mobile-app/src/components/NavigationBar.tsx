import React from 'react';
import { StyleSheet, Text, View, TouchableOpacity, SafeAreaView } from 'react-native';
import { useMobileAuth } from '../context/AuthContext';
import { useMobileTenant } from '../config/TenantConfigContext';

interface NavigationBarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

export const NavigationBar: React.FC<NavigationBarProps> = ({ currentTab, onSelectTab }) => {
  const { logout } = useMobileAuth();
  const { tenantConfig } = useMobileTenant();

  const primaryColor = tenantConfig?.theme?.primaryColor || '#0F4C81';

  const tabs = [
    { id: 'schedule', label: 'Schedule', icon: '📅' },
    { id: 'attendance', label: 'Attendance', icon: '📝' },
    { id: 'notifications', label: 'Inbox', icon: '🔔' },
  ];

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {tabs.map((t) => {
          const isActive = currentTab === t.id;

          return (
            <TouchableOpacity
              key={t.id}
              style={[styles.tabButton, isActive && { borderTopColor: primaryColor, borderTopWidth: 2 }]}
              onPress={() => onSelectTab(t.id)}
            >
              <Text style={styles.icon}>{t.icon}</Text>
              <Text style={[styles.label, isActive && { color: primaryColor, fontWeight: '900' }]}>
                {t.label}
              </Text>
            </TouchableOpacity>
          );
        })}

        <TouchableOpacity style={styles.tabButton} onPress={logout}>
          <Text style={styles.icon}>🚪</Text>
          <Text style={styles.label}>Logout</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: '#1E293B',
  },
  container: {
    flexDirection: 'row',
    height: 60,
    backgroundColor: '#1E293B',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
  },
  tabButton: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  icon: {
    fontSize: 18,
  },
  label: {
    fontSize: 10,
    color: '#94A3B8',
    marginTop: 2,
    fontWeight: '600',
  },
});
