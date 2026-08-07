import React, { useState } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  Modal, 
  TouchableOpacity, 
  TextInput, 
  Alert 
} from 'react-native';
import { StudentAttendanceItem } from '../../types';

interface ManualOverrideDialogProps {
  visible: boolean;
  student: StudentAttendanceItem | null;
  onClose: () => void;
  onConfirmOverride: (studentId: string, newStatus: 'P' | 'A' | 'L', justification: string) => void;
}

export const ManualOverrideDialog: React.FC<ManualOverrideDialogProps> = ({
  visible,
  student,
  onClose,
  onConfirmOverride,
}) => {
  if (!student) return null;

  const [selectedStatus, setSelectedStatus] = useState<'P' | 'A' | 'L'>(student.status);
  const [justification, setJustification] = useState<string>('');

  const handleSave = () => {
    if (!justification.trim()) {
      Alert.alert('Justification Required', 'Please enter a valid reason for overriding this attendance record.');
      return;
    }
    onConfirmOverride(student.id, selectedStatus, justification.trim());
    setJustification('');
    onClose();
  };

  return (
    <Modal
      animationType="fade"
      transparent={true}
      visible={visible}
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.dialog}>
          <Text style={styles.title}>Manual Attendance Override</Text>
          <Text style={styles.studentName}>
            Student: <Text style={styles.highlight}>{student.full_name}</Text>
          </Text>
          <Text style={styles.subtitle}>
            Roll #{student.roll_number} &bull; Current Status: {student.status}
          </Text>

          {/* New Status Toggle */}
          <Text style={styles.sectionLabel}>Select New Status:</Text>
          <View style={styles.statusToggleRow}>
            {[
              { id: 'P', label: 'Present', color: '#10B981' },
              { id: 'A', label: 'Absent', color: '#EF4444' },
              { id: 'L', label: 'Late', color: '#F59E0B' },
            ].map((item) => (
              <TouchableOpacity
                key={item.id}
                style={[
                  styles.statusOption,
                  selectedStatus === item.id && { backgroundColor: item.color, borderColor: item.color },
                ]}
                onPress={() => setSelectedStatus(item.id as any)}
              >
                <Text
                  style={[
                    styles.statusOptionText,
                    selectedStatus === item.id && { color: '#FFFFFF', fontWeight: '900' },
                  ]}
                >
                  {item.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Mandatory Justification Box */}
          <Text style={styles.sectionLabel}>Mandatory Reason / Justification:</Text>
          <TextInput
            style={styles.textInput}
            value={justification}
            onChangeText={setJustification}
            placeholder="e.g. Verified parent sick leave note / Principal approved..."
            placeholderTextColor="#64748B"
            multiline
            numberOfLines={3}
          />

          {/* Actions */}
          <View style={styles.actionRow}>
            <TouchableOpacity style={styles.cancelButton} onPress={onClose}>
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.confirmButton} onPress={handleSave}>
              <Text style={styles.confirmText}>Save Override</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  dialog: {
    backgroundColor: '#1E293B',
    borderRadius: 24,
    padding: 24,
    width: '100%',
    maxWidth: 400,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  title: {
    fontSize: 18,
    fontWeight: '900',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  studentName: {
    fontSize: 14,
    color: '#CBD5E1',
  },
  highlight: {
    color: '#38BDF8',
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 12,
    color: '#94A3B8',
    marginBottom: 16,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#94A3B8',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
    marginTop: 8,
  },
  statusToggleRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  statusOption: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 12,
    alignItems: 'center',
    backgroundColor: '#0F172A',
    borderWidth: 1,
    borderColor: '#334155',
  },
  statusOptionText: {
    fontSize: 12,
    color: '#94A3B8',
    fontWeight: '600',
  },
  textInput: {
    backgroundColor: '#0F172A',
    borderRadius: 12,
    padding: 12,
    color: '#FFFFFF',
    fontSize: 13,
    borderWidth: 1,
    borderColor: '#334155',
    textAlignVertical: 'top',
    height: 80,
    marginBottom: 16,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
  },
  cancelButton: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 12,
    backgroundColor: '#0F172A',
  },
  cancelText: {
    color: '#94A3B8',
    fontSize: 13,
    fontWeight: '700',
  },
  confirmButton: {
    paddingVertical: 10,
    paddingHorizontal: 18,
    borderRadius: 12,
    backgroundColor: '#2563EB',
  },
  confirmText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '800',
  },
});
