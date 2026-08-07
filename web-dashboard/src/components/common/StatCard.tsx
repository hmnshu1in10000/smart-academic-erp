import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: string;
  trendType?: 'positive' | 'negative' | 'neutral';
  color?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendType = 'positive',
  color = 'var(--color-primary)',
}) => {
  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800/80 shadow-lg relative overflow-hidden group hover:border-slate-700/80 transition duration-300">
      {/* Background Accent Glow */}
      <div 
        className="absolute -right-6 -bottom-6 w-24 h-24 rounded-full opacity-10 blur-2xl group-hover:opacity-20 transition duration-500"
        style={{ backgroundColor: color }}
      ></div>

      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {title}
          </p>
          <h3 className="text-2xl font-black text-white mt-1.5 tracking-tight">
            {value}
          </h3>
          {subtitle && (
            <p className="text-xs text-slate-400 mt-1">
              {subtitle}
            </p>
          )}
        </div>
        <div 
          className="p-3 rounded-xl flex items-center justify-center shadow-inner"
          style={{ 
            backgroundColor: `${color}1A`, 
            color: color,
            border: `1px solid ${color}33`
          }}
        >
          <Icon className="w-5 h-5" />
        </div>
      </div>

      {trend && (
        <div className="mt-3 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
          <span 
            className={`font-semibold ${
              trendType === 'positive' ? 'text-emerald-400' :
              trendType === 'negative' ? 'text-rose-400' : 'text-slate-400'
            }`}
          >
            {trend}
          </span>
          <span className="text-[10px] text-slate-400 uppercase font-medium">vs last month</span>
        </div>
      )}
    </div>
  );
};
