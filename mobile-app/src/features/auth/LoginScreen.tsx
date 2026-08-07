import React, { useState } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  TextInput, 
  TouchableOpacity, 
  ActivityIndicator, 
  SafeAreaView, 
  KeyboardAvoidingView, 
  Platform 
} from 'react-native';
import { useMobileAuth } from '../../context/AuthContext';
import { useMobileTenant } from '../../config/TenantConfigContext';
import { API_BASE_URL } from '../../api/client';
import axios from 'axios';

export const LoginScreen: React.FC = () => {
  const { login } = useMobileAuth();
  const { tenantConfig } = useMobileTenant();

  const [username, setUsername] = useState('teacher01@demo.school');
  const [password, setPassword] = useState('Demo@1234!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const primaryColor = tenantConfig?.theme?.primaryColor || '#0F4C81';
  const secondaryColor = tenantConfig?.theme?.secondaryColor || '#D97706';

  const handleLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);

      const response = await axios.post(`${API_BASE_URL}/auth/login`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const data = response.data;
      await login(data.access_token, {
        sub: username,
        role: data.role,
        full_name: data.full_name,
        tenant_id: data.tenant_id,
      });
    } catch (err: any) {
      console.error('Mobile login error:', err);
      setError(err.response?.data?.detail || 'Invalid teacher credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'} 
        style={styles.inner}
      >
        {/* Brand Header */}
        <View style={styles.headerContainer}>
          <View style={[styles.logoBadge, { backgroundColor: primaryColor }]}>
            <Text style={styles.logoText}>🏫</Text>
          </View>
          <Text style={styles.schoolTitle}>
            {tenantConfig?.school_name || 'Greenwood High'}
          </Text>
          <Text style={[styles.schoolSubtitle, { color: secondaryColor }]}>
            Teacher & Staff Mobile Portal
          </Text>
        </View>

        {/* Card Form */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Teacher Sign In</Text>
          <Text style={styles.cardSubtitle}>Access timetable & mark class attendance</Text>

          {error && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Teacher Email</Text>
            <TextInput
              style={styles.input}
              value={username}
              onChangeText={setUsername}
              autoCapitalize="none"
              keyboardType="email-address"
              placeholder="teacher01@demo.school"
              placeholderTextColor="#64748B"
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Password</Text>
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              placeholder="••••••••"
              placeholderTextColor="#64748B"
            />
          </View>

          <TouchableOpacity
            style={[styles.button, { backgroundColor: primaryColor }]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.buttonText}>Sign In to Mobile Portal</Text>
            )}
          </TouchableOpacity>

          {/* Quick Demo Helper Box */}
          <View style={styles.demoBox}>
            <Text style={styles.demoTitle}>💡 Demo Teacher Credentials:</Text>
            <Text style={styles.demoText}>User: teacher01@demo.school</Text>
            <Text style={styles.demoText}>Pass: Demo@1234!</Text>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  inner: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  headerContainer: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logoBadge: {
    width: 64,
    height: 64,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  logoText: {
    fontSize: 32,
  },
  schoolTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#FFFFFF',
    textAlign: 'center',
  },
  schoolSubtitle: {
    fontSize: 13,
    fontWeight: '700',
    marginTop: 4,
  },
  card: {
    backgroundColor: '#1E293B',
    borderRadius: 24,
    padding: 24,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  cardSubtitle: {
    fontSize: 12,
    color: '#94A3B8',
    marginTop: 2,
    marginBottom: 20,
  },
  errorBox: {
    backgroundColor: 'rgba(220, 38, 38, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(220, 38, 38, 0.3)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },
  errorText: {
    color: '#FCA5A5',
    fontSize: 12,
    fontWeight: '600',
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 11,
    fontWeight: '700',
    color: '#CBD5E1',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#0F172A',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    color: '#FFFFFF',
    fontSize: 14,
  },
  button: {
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 4,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
  demoBox: {
    backgroundColor: '#0F172A',
    borderRadius: 12,
    padding: 12,
    marginTop: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  demoTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#F59E0B',
    marginBottom: 4,
  },
  demoText: {
    fontSize: 11,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    color: '#94A3B8',
  },
});
