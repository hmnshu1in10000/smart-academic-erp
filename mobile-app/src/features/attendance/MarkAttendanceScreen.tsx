import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  ScrollView, 
  TouchableOpacity, 
  SafeAreaView, 
  ActivityIndicator, 
  Alert,
  Platform
} from 'react-native';
import { useMobileTenant } from '../../config/TenantConfigContext';
import { useMobileAuth } from '../../context/AuthContext';
import { StudentAttendanceItem, AttendanceSignalPayload } from '../../types';
import { ManualOverrideDialog } from './ManualOverrideDialog';
import { queueOfflineAttendance, syncOfflineQueue } from './offlineQueue';

export const MarkAttendanceScreen: React.FC<{ selectedSection?: string }> = ({
  selectedSection = '10-A',
}) => {
  const { tenantConfig } = useMobileTenant();
  const { token } = useMobileAuth();

  const primaryColor = tenantConfig?.theme?.primaryColor || '#0F4C81';

  const [activeSection, setActiveSection] = useState<string>(selectedSection);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);

  // Override dialog state
  const [overrideStudent, setOverrideStudent] = useState<StudentAttendanceItem | null>(null);

  const [students, setStudents] = useState<StudentAttendanceItem[]>([
    { id: 'std_001', roll_number: 1, full_name: 'Isaiah Bhatt', status: 'P' },
    { id: 'std_002', roll_number: 2, full_name: 'Samar Gupta', status: 'P' },
    { id: 'std_003', roll_number: 3, full_name: 'Julie Baxter', status: 'A' },
    { id: 'std_004', roll_number: 4, full_name: 'Aarav Patel', status: 'P' },
    { id: 'std_005', roll_number: 5, full_name: 'Ananya Sharma', status: 'L' },
    { id: 'std_006', roll_number: 6, full_name: 'Vikram Singh', status: 'P' },
    { id: 'std_007', roll_number: 7, full_name: 'Rohan Mehta', status: 'P' },
    { id: 'std_008', roll_number: 8, full_name: 'Sneha Verma', status: 'A' },
    { id: 'std_009', roll_number: 9, full_name: 'Kavya Nair', status: 'P' },
    { id: 'std_010', roll_number: 10, full_name: 'Aditya Kumar', status: 'P' },
  ]);

  const handleToggleStatus = (studentId: string, status: 'P' | 'A' | 'L') => {
    setStudents(prev =>
      prev.map(s => (s.id === studentId ? { ...s, status } : s))
    );
  };

  const handleConfirmOverride = (studentId: string, newStatus: 'P' | 'A' | 'L', justification: string) => {
    setStudents(prev =>
      prev.map(s =>
        s.id === studentId
          ? { ...s, status: newStatus, hasOverride: true, overrideNotes: justification }
          : s
      )
    );
  };

  const handleSubmitAttendance = async () => {
    setSubmitting(true);
    setSyncStatus(null);

    const signals: AttendanceSignalPayload[] = students.map(s => ({
      signal_id: `sig_${Date.now()}_${s.id}`,
      student_id: s.id,
      class_section_id: activeSection === '10-A' ? 'sec_10a' : 'sec_10b',
      timestamp: new Date().toISOString(),
      status: s.status,
      confidence_score: 1.0,
      source: s.hasOverride ? 'TEACHER_MANUAL_OVERRIDE' : 'TEACHER_MOBILE_APP',
      notes: s.overrideNotes,
    }));

    try {
      // Queue offline item in AsyncStorage
      await queueOfflineAttendance(signals);
      
      // Attempt auto-sync with live backend API
      const syncResult = await syncOfflineQueue(token);

      if (syncResult.synced > 0) {
        setSyncStatus(`✅ Attendance submitted & synced successfully to backend! (${syncResult.synced} items)`);
        Alert.alert('Attendance Submitted', 'Class attendance successfully posted to server database.');
      } else {
        setSyncStatus('📡 Queued locally in AsyncStorage. Will sync when online.');
        Alert.alert('Saved Offline', 'Network connection unavailable. Submission queued locally and will sync when backend is reached.');
      }
    } catch (err) {
      console.warn('Attendance submission error:', err);
      setSyncStatus('📡 Queued locally in AsyncStorage (Offline Mode).');
      Alert.alert('Queued Offline', 'Attendance saved locally in offline queue.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Mark Class Attendance</Text>
        <Text style={styles.headerSubtitle}>
          Select section & toggle P / A / L for each student
        </Text>
      </View>

      {/* Section Switcher Bar */}
      <View style={styles.sectionBar}>
        {['10-A', '10-B'].map((sec) => (
          <TouchableOpacity
            key={sec}
            style={[
              styles.sectionButton,
              activeSection === sec && { backgroundColor: primaryColor },
            ]}
            onPress={() => setActiveSection(sec)}
          >
            <Text
              style={[
                styles.sectionButtonText,
                activeSection === sec && { color: '#FFFFFF', fontWeight: '900' },
              ]}
            >
              Class {sec}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {syncStatus && (
        <View style={styles.syncBanner}>
          <Text style={styles.syncBannerText}>{syncStatus}</Text>
        </View>
      )}

      {/* Student List */}
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {students.map((student) => {
          return (
            <View key={student.id} style={styles.studentCard}>
              <View style={styles.studentInfo}>
                <Text style={styles.rollText}>#{String(student.roll_number).padStart(2, '0')}</Text>
                <View>
                  <Text style={styles.studentName}>{student.full_name}</Text>
                  {student.hasOverride && (
                    <Text style={styles.overrideBadge}>
                      ✏️ Manual Override: {student.overrideNotes}
                    </Text>
                  )}
                </View>
              </View>

              {/* Status Toggles */}
              <View style={styles.toggleRow}>
                <TouchableOpacity
                  style={[styles.statusBtn, student.status === 'P' && styles.btnPresent]}
                  onPress={() => handleToggleStatus(student.id, 'P')}
                >
                  <Text style={[styles.statusBtnText, student.status === 'P' && styles.textActive]}>P</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.statusBtn, student.status === 'A' && styles.btnAbsent]}
                  onPress={() => handleToggleStatus(student.id, 'A')}
                >
                  <Text style={[styles.statusBtnText, student.status === 'A' && styles.textActive]}>A</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.statusBtn, student.status === 'L' && styles.btnLate]}
                  onPress={() => handleToggleStatus(student.id, 'L')}
                >
                  <Text style={[styles.statusBtnText, student.status === 'L' && styles.textActive]}>L</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.overrideBtn}
                  onPress={() => setOverrideStudent(student)}
                >
                  <Text style={styles.overrideBtnText}>💬</Text>
                </TouchableOpacity>
              </View>
            </View>
          );
        })}
      </ScrollView>

      {/* Submit Button */}
      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.submitButton, { backgroundColor: primaryColor }]}
          onPress={handleSubmitAttendance}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.submitButtonText}>Submit Class Attendance ({activeSection})</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Manual Override Modal */}
      <ManualOverrideDialog
        visible={!!overrideStudent}
        student={overrideStudent}
        onClose={() => setOverrideStudent(null)}
        onConfirmOverride={handleConfirmOverride}
      />
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
  sectionBar: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
    backgroundColor: '#1E293B',
  },
  sectionButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 12,
    alignItems: 'center',
    backgroundColor: '#0F172A',
  },
  sectionButtonText: {
    fontSize: 13,
    color: '#94A3B8',
    fontWeight: '700',
  },
  syncBanner: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    padding: 10,
    marginHorizontal: 16,
    marginTop: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.3)',
  },
  syncBannerText: {
    color: '#34D399',
    fontSize: 12,
    fontWeight: '700',
    textAlign: 'center',
  },
  scrollContent: {
    padding: 16,
  },
  studentCard: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  studentInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  rollText: {
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '800',
    marginRight: 10,
    width: 28,
  },
  studentName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  overrideBadge: {
    fontSize: 10,
    color: '#F59E0B',
    marginTop: 2,
    fontWeight: '600',
  },
  toggleRow: {
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
  },
  statusBtn: {
    width: 34,
    height: 34,
    borderRadius: 10,
    backgroundColor: '#0F172A',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#334155',
  },
  statusBtnText: {
    color: '#64748B',
    fontWeight: '800',
    fontSize: 13,
  },
  btnPresent: {
    backgroundColor: '#10B981',
    borderColor: '#10B981',
  },
  btnAbsent: {
    backgroundColor: '#EF4444',
    borderColor: '#EF4444',
  },
  btnLate: {
    backgroundColor: '#F59E0B',
    borderColor: '#F59E0B',
  },
  textActive: {
    color: '#FFFFFF',
  },
  overrideBtn: {
    padding: 6,
  },
  overrideBtnText: {
    fontSize: 16,
  },
  footer: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#1E293B',
    backgroundColor: '#0F172A',
  },
  submitButton: {
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
});
