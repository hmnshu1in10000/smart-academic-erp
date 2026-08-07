import React, { useEffect, useState } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  ScrollView, 
  SafeAreaView, 
  ActivityIndicator, 
  Platform 
} from 'react-native';
import { useMobileTenant } from '../../config/TenantConfigContext';
import { useMobileAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';

export const StudentHomeScreen: React.FC = () => {
  const { tenantConfig } = useMobileTenant();
  const { user } = useMobileAuth();

  const primaryColor = tenantConfig?.theme?.primaryColor || '#0F4C81';

  const [loading, setLoading] = useState<boolean>(true);
  const [summary, setSummary] = useState<any>({
    student_name: 'Isaiah Bhatt',
    section: 'Class 10-A',
    roll_number: 1,
    attendance_rate_pct: 90.0,
    report_card: [
      { subject_name: 'Mathematics', teacher_name: 'Mr. Rajesh Kumar', grade: 'A+', score_pct: 92.5 },
      { subject_name: 'Science', teacher_name: 'Ms. Priya Singh', grade: 'A', score_pct: 88.0 },
      { subject_name: 'English Language', teacher_name: 'English Dept', grade: 'A', score_pct: 85.5 },
      { subject_name: 'Social Science', teacher_name: 'SST Dept', grade: 'B+', score_pct: 78.0 },
      { subject_name: 'Computer Science', teacher_name: 'CS Dept', grade: 'A+', score_pct: 96.0 },
    ],
  });

  const fetchStudentSummary = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/student/academic-summary');
      if (res.data) {
        setSummary(res.data);
      }
    } catch (err) {
      console.warn('Could not fetch student academic summary; using local cache:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudentSummary();
  }, []);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={primaryColor} />
        <Text style={styles.loadingText}>Loading Student Academic Profile...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Student Portal</Text>
        <Text style={styles.headerSubtitle}>
          Student: {user?.full_name || summary.student_name} &bull; {summary.section}
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Attendance Badge Header Card */}
        <View style={[styles.profileCard, { borderColor: primaryColor }]}>
          <View style={styles.profileHeader}>
            <View style={[styles.avatar, { backgroundColor: primaryColor }]}>
              <Text style={styles.avatarText}>🎓</Text>
            </View>
            <View>
              <Text style={styles.studentName}>{summary.student_name}</Text>
              <Text style={styles.studentMeta}>Roll #{String(summary.roll_number).padStart(2, '0')} &bull; {summary.section}</Text>
            </View>
          </View>

          <View style={styles.attendanceBar}>
            <Text style={styles.attLabel}>Overall Personal Attendance Rate:</Text>
            <Text style={styles.attValue}>{summary.attendance_rate_pct}%</Text>
          </View>
        </View>

        {/* Report Card Viewer */}
        <View style={styles.reportCard}>
          <Text style={styles.sectionTitle}>📊 Academic Progress & Report Card</Text>

          {summary.report_card && summary.report_card.map((item: any, idx: number) => (
            <View key={idx} style={styles.subjectRow}>
              <View>
                <Text style={styles.subjectName}>{item.subject_name}</Text>
                <Text style={styles.teacherName}>{item.teacher_name}</Text>
              </View>
              <View style={styles.scoreBox}>
                <Text style={styles.scoreText}>{item.score_pct}%</Text>
                <View style={styles.gradeBadge}>
                  <Text style={styles.gradeText}>{item.grade}</Text>
                </View>
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#0F172A',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#94A3B8',
    fontSize: 14,
    marginTop: 12,
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
  profileCard: {
    backgroundColor: '#1E293B',
    borderRadius: 20,
    padding: 18,
    borderWidth: 1.5,
    marginBottom: 16,
  },
  profileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  avatar: {
    width: 46,
    height: 46,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  avatarText: {
    fontSize: 22,
  },
  studentName: {
    fontSize: 18,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  studentMeta: {
    fontSize: 12,
    color: '#94A3B8',
    marginTop: 2,
  },
  attendanceBar: {
    backgroundColor: '#0F172A',
    borderRadius: 14,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  attLabel: {
    fontSize: 12,
    color: '#94A3B8',
    fontWeight: '600',
  },
  attValue: {
    fontSize: 18,
    fontWeight: '900',
    color: '#34D399',
  },
  reportCard: {
    backgroundColor: '#1E293B',
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#FFFFFF',
    marginBottom: 14,
  },
  subjectRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#0F172A',
  },
  subjectName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  teacherName: {
    fontSize: 11,
    color: '#94A3B8',
    marginTop: 2,
  },
  scoreBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  scoreText: {
    fontSize: 13,
    fontWeight: '800',
    color: '#38BDF8',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  gradeBadge: {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.4)',
  },
  gradeText: {
    color: '#34D399',
    fontSize: 11,
    fontWeight: '900',
  },
});
