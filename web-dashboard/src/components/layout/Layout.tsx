import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface LayoutProps {
  defaultTab?: string;
  children: (activeTab: string, setActiveTab: (tab: string) => void) => React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ defaultTab = 'dashboard', children }) => {
  const [activeTab, setActiveTab] = useState<string>(defaultTab);

  useEffect(() => {
    if (defaultTab) {
      setActiveTab(defaultTab);
    }
  }, [defaultTab]);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header activeTab={activeTab} setActiveTab={setActiveTab} />
        
        {/* Scrollable Content Body */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {children(activeTab, setActiveTab)}
        </main>
      </div>
    </div>
  );
};
