import React from 'react';
import { StyleSheet, Text, View, ScrollView, SafeAreaView, TouchableOpacity } from 'react-native';
import { NotificationItem } from '../../types';

export const NotificationsScreen: React.FC = () => {
  const notifications: NotificationItem[] = [
    {
      id: 'notif_001',
      title: 'Term 1 Exam Invigilation Duty',
      message: 'You are assigned as chief invigilator for Room R10A on Monday 9:00 AM.',
      timestamp: '10 mins ago',
      type: 'URGENT',
      read: false,
    },
    {
      id: 'notif_002',
      title: 'Principal Staff Meeting Notice',
      message: 'Monthly academic performance review meeting scheduled in Conference Hall at 3:30 PM.',
      timestamp: '2 hours ago',
      type: 'ALERT',
      read: false,
    },
    {
      id: 'notif_003',
      title: 'Fee Collection Update',
      message: '80% of Term 1 fee invoices paid for Class 10-A students.',
      timestamp: '1 day ago',
      type: 'INFO',
      read: true,
    },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Teacher Inbox Notifications</Text>
        <Text style={styles.headerSubtitle}>Official staff circulars & urgent duty notices</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {notifications.map((item) => (
          <TouchableOpacity
            key={item.id}
            style={[
              styles.card,
              !item.read && styles.unreadCard,
            ]}
          >
            <View style={styles.cardHeader}>
              <View style={styles.typeBadge}>
                <Text style={styles.typeBadgeText}>{item.type}</Text>
              </View>
              <Text style={styles.timeText}>{item.timestamp}</Text>
            </View>

            <Text style={styles.title}>{item.title}</Text>
            <Text style={styles.message}>{item.message}</Text>
          </TouchableOpacity>
        ))}
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
  card: {
    backgroundColor: '#1E293B',
    borderRadius: 18,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  unreadCard: {
    borderColor: '#3B82F6',
    borderWidth: 1.5,
    backgroundColor: '#1E293B',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  typeBadge: {
    backgroundColor: 'rgba(245, 158, 11, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  typeBadgeText: {
    color: '#F59E0B',
    fontSize: 10,
    fontWeight: '900',
  },
  timeText: {
    color: '#64748B',
    fontSize: 11,
  },
  title: {
    fontSize: 15,
    fontWeight: '800',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  message: {
    fontSize: 13,
    color: '#94A3B8',
    lineHeight: 18,
  },
});
