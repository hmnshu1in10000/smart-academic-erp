import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useMobileAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';
import { NotificationItem } from '../../types';

interface ApiNotificationResponse {
  id: string;
  user_email: string;
  title: string;
  message: string;
  category: string;
  notification_type: string;
  is_read: boolean;
  read: boolean;
  created_at: string;
}

export const NotificationsScreen: React.FC = () => {
  const { user } = useMobileAuth();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const roleLabel = user?.role ? user.role.toUpperCase() : 'USER';

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await apiClient.get<ApiNotificationResponse[]>('/notifications/inbox');
      if (res.data && Array.isArray(res.data)) {
        const mapped: NotificationItem[] = res.data.map((item) => {
          let timeFormatted = 'Recently';
          try {
            const d = new Date(item.created_at);
            if (!isNaN(d.getTime())) {
              timeFormatted = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
          } catch {
            timeFormatted = 'Recently';
          }

          const rawCategory = (item.category || item.notification_type || 'INFO').toUpperCase();
          const category: 'ALERT' | 'INFO' | 'URGENT' =
            rawCategory.includes('URGENT') ? 'URGENT' :
            rawCategory.includes('ALERT') || rawCategory.includes('FEE') || rawCategory.includes('ATTENDANCE') ? 'ALERT' :
            'INFO';

          return {
            id: item.id,
            title: item.title,
            message: item.message,
            timestamp: timeFormatted,
            type: category,
            read: item.is_read || item.read,
          };
        });
        setNotifications(mapped);
      }
    } catch (err) {
      console.warn('Failed to load notifications from API:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchNotifications();
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient.post('/notifications/mark-all-read');
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch (err) {
      console.warn('Failed to mark notifications as read:', err);
    }
  };

  const getBadgeStyle = (type: 'ALERT' | 'INFO' | 'URGENT') => {
    if (type === 'URGENT') {
      return { bg: 'rgba(239, 68, 68, 0.2)', text: '#EF4444', border: '#EF4444' };
    }
    if (type === 'ALERT') {
      return { bg: 'rgba(245, 158, 11, 0.2)', text: '#F59E0B', border: '#F59E0B' };
    }
    return { bg: 'rgba(59, 130, 246, 0.2)', text: '#3B82F6', border: '#3B82F6' };
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <Text style={styles.headerTitle}>{roleLabel} Inbox</Text>
          {unreadCount > 0 && (
            <TouchableOpacity onPress={handleMarkAllRead} style={styles.markReadBtn}>
              <Text style={styles.markReadText}>Mark Read</Text>
            </TouchableOpacity>
          )}
        </View>
        <Text style={styles.headerSubtitle}>
          Role-scoped notices & alerts for {user?.full_name || 'Academic Portal'}
        </Text>
      </View>

      {loading && !refreshing ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#3B82F6" />
          <Text style={styles.loadingText}>Fetching your notifications...</Text>
        </View>
      ) : notifications.length === 0 ? (
        <View style={styles.centerContainer}>
          <Text style={styles.emptyTitle}>All Caught Up! 🎉</Text>
          <Text style={styles.emptySubtitle}>No pending notifications for your account.</Text>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#3B82F6" />}
        >
          {notifications.map((item) => {
            const badge = getBadgeStyle(item.type);
            return (
              <TouchableOpacity
                key={item.id}
                style={[
                  styles.card,
                  !item.read && styles.unreadCard,
                ]}
                activeOpacity={0.8}
              >
                <View style={styles.cardHeader}>
                  <View style={[styles.typeBadge, { backgroundColor: badge.bg }]}>
                    <Text style={[styles.typeBadgeText, { color: badge.text }]}>{item.type}</Text>
                  </View>
                  <Text style={styles.timeText}>{item.timestamp}</Text>
                </View>

                <Text style={styles.title}>{item.title}</Text>
                <Text style={styles.message}>{item.message}</Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}
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
  headerTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '900',
    color: '#FFFFFF',
    letterSpacing: -0.3,
  },
  markReadBtn: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(59, 130, 246, 0.3)',
  },
  markReadText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#60A5FA',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#94A3B8',
    marginTop: 4,
  },
  scrollContent: {
    padding: 16,
  },
  centerContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  loadingText: {
    color: '#94A3B8',
    fontSize: 13,
    marginTop: 12,
    fontWeight: '600',
  },
  emptyTitle: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '800',
    marginBottom: 6,
  },
  emptySubtitle: {
    color: '#64748B',
    fontSize: 13,
    textAlign: 'center',
  },
  card: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
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
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  typeBadgeText: {
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0.5,
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
    lineHeight: 20,
  },
  message: {
    fontSize: 13,
    color: '#94A3B8',
    lineHeight: 18,
  },
});

