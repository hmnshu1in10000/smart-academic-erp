import React, { createContext, useContext, useEffect, useState } from 'react';
import axios from 'axios';
import type { TenantConfig } from '../types';

interface TenantContextType {
  config: TenantConfig | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

const TenantContext = createContext<TenantContextType>({
  config: null,
  loading: true,
  error: null,
  refetch: () => {},
});

const DEFAULT_TENANT_ID = 'greenwood-high-001';

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<TenantConfig | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTenantConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get<TenantConfig>(
        `http://localhost:8000/api/v1/core/tenant-config?tenant_id=${DEFAULT_TENANT_ID}`
      );
      const data = response.data;
      setConfig(data);
      
      // Inject CSS Custom Variables into document root
      if (data.theme) {
        const root = document.documentElement;
        root.style.setProperty('--color-primary', data.theme.primary || '#0F4C81');
        root.style.setProperty('--color-secondary', data.theme.secondary || '#D97706');
        root.style.setProperty('--color-accent', data.theme.accent || '#2563EB');
        root.style.setProperty('--color-success', data.theme.success || '#16A34A');
        root.style.setProperty('--color-warning', data.theme.warning || '#D97706');
        root.style.setProperty('--color-error', data.theme.error || '#DC2626');
        
        if (data.theme.font_family_heading) {
          root.style.setProperty('--font-family-heading', data.theme.font_family_heading);
        }
        if (data.theme.font_family_body) {
          root.style.setProperty('--font-family-body', data.theme.font_family_body);
        }
      }

      // Update document title
      if (data.school_name) {
        document.title = `${data.school_name} — Smart Academic ERP`;
      }
    } catch (err: any) {
      console.error('Failed to fetch tenant configuration:', err);
      setError('Could not load tenant visual theme. Using default styles.');
      // Apply default Greenwood High Navy/Gold theme fallback
      const root = document.documentElement;
      root.style.setProperty('--color-primary', '#0F4C81');
      root.style.setProperty('--color-secondary', '#D97706');
      root.style.setProperty('--color-accent', '#2563EB');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTenantConfig();
  }, []);

  return (
    <TenantContext.Provider value={{ config, loading, error, refetch: fetchTenantConfig }}>
      {children}
    </TenantContext.Provider>
  );
};

export const useTenant = () => useContext(TenantContext);
