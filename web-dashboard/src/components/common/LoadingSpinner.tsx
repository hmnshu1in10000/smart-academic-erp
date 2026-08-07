import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner: React.FC<{ message?: string }> = ({ message = 'Loading data...' }) => (
  <div className="flex flex-col items-center justify-center py-12 space-y-3 text-slate-400">
    <Loader2 className="w-8 h-8 text-[var(--color-primary)] animate-spin" />
    <p className="text-sm font-medium">{message}</p>
  </div>
);
