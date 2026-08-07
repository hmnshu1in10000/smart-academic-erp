import React from 'react';
import { StyleSheet, Text, View, ScrollView, SafeAreaView, TouchableOpacity, Platform } from 'react-native';
import { useMobileTenant } from '../../config/TenantConfigContext';
import { useMobileAuth } from '../../context/AuthContext';
import { TimetablePeriod } from '../../types';

export const DailyScheduleScreen: React.FC<{ onNavigateToMark: (section: string) => void }> = ({
  onNavigateToMark,
}) => {
  const { tenantConfig } = useMobileTenant();
  const { user } = useMobileAuth();

  const primaryColor = tenantConfig?.theme?.primaryColor || '#0F4C81';

  const schedule: TimetablePeriod[] = [
    { period: 1, day: 'MON', subject: 'Mathematics', section: 'Class 10-A', start_time: '08:00', end_time: '08:45', room: 'R10A' },
    { period: 2, day: 'MON', subject: 'Science', section: 'Class 10-B', start_time: '08:45', end_time: '09:30', room: 'R10B' },
    { period: 3, day: 'MON', subject: 'Computer Science', section: 'Class 10-A', start_time: '09:30', end_time: '10:15', room: 'Lab-1' },
    { period: 4, day: 'MON', subject: 'Mathematics', section: 'Class 10-B', start_time: '10:30', end_time: '11:15', room: 'R10B' },
    { period: 5, day: 'MON', subject: 'Physical Education', section: 'Class 10-A', start_time: '11:15', end_time: '12:00', room: 'Ground' },
  ];

  const currentActivePeriod = 1; // Simulated current period

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Daily Class Schedule</Text>
        <Text style={styles.headerSubtitle}>
          Teacher: {user?.full_name || 'Mr. Rajesh Kumar'} &bull; Today: Monday
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.banner}>
          <Text style={styles.bannerTitle}>⚡ Current Period Active</Text>
          <Text style={styles.bannerSubtitle}>
            Period 1: Mathematics in Class 10-A (Room R10A)
          </Text>
          <TouchableOpacity
            style={[styles.bannerButton, { backgroundColor: '#F59E0B' }]}
            onPress={() => onNavigateToMark('10-A')}
          >
            <Text style={styles.bannerButtonText}>Mark Attendance Now →</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.sectionTitle}>Full Daily Period Schedule</Text>

        {schedule.map((item) => {
          const isActive = item.period === currentActivePeriod;

          return (
            <View
              key={item.period}
              style={[
                styles.periodCard,
                isActive && { borderColor: primaryColor, borderWidth: 2 },
              ]}
            >
              <View style={styles.periodRow}>
                <View style={styles.periodBadgeContainer}>
                  <View style={[styles.periodBadge, isActive ? { backgroundColor: primaryColor } : { backgroundColor: '#334155' }]}>
                    <Text style={styles.periodBadgeText}>P{item.period}</Text>
                  </View>
                  <Text style={styles.timeText}>
                    {item.start_time} - {item.end_time}
                  </Text>
                </View>

                {isActive && (
                  <View style={styles.nowBadge}>
                    <Text style={styles.nowBadgeText}>LIVE NOW</Text>
                  </View>
                )}
              </View>

              <Text style={styles.subjectText}>{item.subject}</Text>
              
              <View style={styles.metaRow}>
                <Text style={styles.metaText}>Class: {item.section}</Text>
                <Text style={styles.metaText}>Room: {item.room}</Text>
              </View>

              <TouchableOpacity
                style={styles.markButton}
                onPress={() => onNavigateToMark(item.section.includes('10-A') ? '10-A' : '10-B')}
              >
                <Text style={styles.markButtonText}>Take Class Attendance</Text>
              </TouchableOpacity>
            </View>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  header: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '900',
    color: '#FFFFFF',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#94A3B8',
    marginTop: 2,
  },
  scrollContent: {
    padding: 16,
  },
  banner: {
    backgroundColor: '#1E293B',
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 20,
  },
  bannerTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#F59E0B',
  },
  bannerSubtitle: {
    fontSize: 13,
    color: '#FFFFFF',
    fontWeight: '600',
    marginTop: 4,
  },
  bannerButton: {
    marginTop: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  bannerButtonText: {
    color: '#0F172A',
    fontWeight: '800',
    fontSize: 12,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#CBD5E1',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  periodCard: {
    backgroundColor: '#1E293B',
    borderRadius: 18,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  periodRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  periodBadgeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  periodBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    marginRight: 8,
  },
  periodBadgeText: {
    color: '#FFFFFF',
    fontWeight: '800',
    fontSize: 12,
  },
  timeText: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '600',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  nowBadge: {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.4)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  nowBadgeText: {
    color: '#34D399',
    fontSize: 10,
    fontWeight: '900',
  },
  subjectText: {
    fontSize: 17,
    fontWeight: '800',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  metaText: {
    color: '#94A3B8',
    fontSize: 12,
  },
  markButton: {
    backgroundColor: '#0F172A',
    borderRadius: 10,
    paddingVertical: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#334155',
  },
  markButtonText: {
    color: '#38BDF8',
    fontSize: 12,
    fontWeight: '700',
  },
});
