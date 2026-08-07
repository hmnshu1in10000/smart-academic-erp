import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

// Support Android emulator (10.0.2.2) vs iOS / Expo Web / desktop (localhost)
const getHost = () => {
  if (Platform.OS === 'android') {
    return '10.0.2.2';
  }
  return 'localhost';
};

export const API_BASE_URL = `http://${getHost()}:8000/api/v1`;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  async (config) => {
    try {
      const token = await AsyncStorage.getItem('erp_mobile_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (err) {
      console.warn('Error reading token from AsyncStorage:', err);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ERR_NETWORK' || !error.response) {
      console.warn(`[Network Warning] Could not connect to backend server at ${API_BASE_URL}. Ensure 'python backend/manage.py runserver' is active on port 8000.`);
    }
    return Promise.reject(error);
  }
);
