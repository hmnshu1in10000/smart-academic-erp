import AsyncStorage from '@react-native-async-storage/async-storage';
import { OfflineQueueItem, AttendanceSignalPayload } from '../../types';
import { API_BASE_URL } from '../../api/client';
import axios from 'axios';

const QUEUE_STORAGE_KEY = 'offline_attendance_queue';

export const queueOfflineAttendance = async (signals: AttendanceSignalPayload[]): Promise<OfflineQueueItem> => {
  const existingQueueRaw = await AsyncStorage.getItem(QUEUE_STORAGE_KEY);
  const queue: OfflineQueueItem[] = existingQueueRaw ? JSON.parse(existingQueueRaw) : [];

  const newItem: OfflineQueueItem = {
    id: `queue_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
    timestamp: new Date().toISOString(),
    signals,
    retryCount: 0,
  };

  queue.push(newItem);
  await AsyncStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(queue));
  return newItem;
};

export const getOfflineQueue = async (): Promise<OfflineQueueItem[]> => {
  const raw = await AsyncStorage.getItem(QUEUE_STORAGE_KEY);
  return raw ? JSON.parse(raw) : [];
};

export const clearOfflineQueue = async (): Promise<void> => {
  await AsyncStorage.removeItem(QUEUE_STORAGE_KEY);
};

export const syncOfflineQueue = async (token: string | null): Promise<{ synced: number; failed: number }> => {
  const queue = await getOfflineQueue();
  if (queue.length === 0) {
    return { synced: 0, failed: 0 };
  }

  let synced = 0;
  let failed = 0;
  const remainingQueue: OfflineQueueItem[] = [];

  for (const item of queue) {
    try {
      // Send queued attendance signals to backend
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(
        `${API_BASE_URL}/attendance/summary`,
        { signals: item.signals },
        { headers, timeout: 5000 }
      );
      synced++;
    } catch (err) {
      console.warn(`Failed syncing queue item ${item.id}:`, err);
      failed++;
      item.retryCount += 1;
      if (item.retryCount < 5) {
        remainingQueue.push(item);
      }
    }
  }

  await AsyncStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(remainingQueue));
  return { synced, failed };
};
