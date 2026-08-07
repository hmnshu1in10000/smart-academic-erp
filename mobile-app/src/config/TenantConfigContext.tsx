import React, { createContext, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { MobileTenantConfig } from '../types';
import { API_BASE_URL } from '../api/client';
import axios from 'axios';

interface TenantContextType {
  tenantConfig: MobileTenantConfig | null;
  loading: boolean;
  refetchConfig: () => Promise<void>;
}

const TenantConfigContext = createContext<TenantContextType>({
  tenantConfig: null,
  loading: true,
  refetchConfig: async () => {},
});

const DEFAULT_CONFIG: MobileTenantConfig = {
  tenant_id: 'greenwood-high-001',
  school_name: 'Greenwood High',
  tagline: 'Excellence in Education',
  theme: {
    primaryColor: '#0F4C81',
    secondaryColor: '#D97706',
    accentColor: '#2563EB',
  },
};

export const TenantConfigProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [tenantConfig, setTenantConfig] = useState<MobileTenantConfig | null>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      // First try loading cached config from AsyncStorage for instant offline boot
      const cached = await AsyncStorage.getItem('cached_tenant_config');
      if (cached) {
        setTenantConfig(JSON.parse(cached));
      }

      // Fetch fresh tenant config from API endpoint
      const response = await axios.get(
        `${API_BASE_URL}/core/tenant-config?tenant_id=greenwood-high-001`,
        { timeout: 5000 }
      );

      if (response.data) {
        const remoteConfig: MobileTenantConfig = {
          tenant_id: response.data.tenant_id,
          school_name: response.data.school_name,
          tagline: response.data.tagline,
          theme: {
            primaryColor: response.data.theme?.primary || '#0F4C81',
            secondaryColor: response.data.theme?.secondary || '#D97706',
            accentColor: response.data.theme?.accent || '#2563EB',
            logoUri: response.data.theme?.logo_url,
          },
        };

        setTenantConfig(remoteConfig);
        await AsyncStorage.setItem('cached_tenant_config', JSON.stringify(remoteConfig));
      }
    } catch (err) {
      console.warn('Network offline or backend unavailable; using cached tenant config:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  return (
    <TenantConfigContext.Provider
      value={{
        tenantConfig,
        loading,
        refetchConfig: fetchConfig,
      }}
    >
      {children}
    </TenantConfigContext.Provider>
  );
};

export const useMobileTenant = () => useContext(TenantConfigContext);
