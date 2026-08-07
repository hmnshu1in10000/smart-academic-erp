import React, { useEffect, useState } from 'react';
import { CreditCard, CheckCircle2 } from 'lucide-react';
import { apiClient } from '../../api/client';
import type { FeeInvoice, FeeSummary } from '../../types';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

export const FeeDashboard: React.FC = () => {
  const [summary, setSummary] = useState<FeeSummary | null>(null);
  const [invoices, setInvoices] = useState<FeeInvoice[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  const fetchFeeData = async () => {
    setLoading(true);
    try {
      let invUrl = '/fees/invoices?page=1&page_size=20';
      if (statusFilter) {
        invUrl += `&status=${statusFilter}`;
      }

      const [sumRes, invRes] = await Promise.all([
        apiClient.get<FeeSummary>('/fees/summary'),
        apiClient.get(invUrl),
      ]);

      setSummary(sumRes.data);
      setInvoices(invRes.data.items);
    } catch (err) {
      console.error('Failed to load fee management data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeeData();
  }, [statusFilter]);

  if (loading) {
    return <LoadingSpinner message="Loading fee collection statistics..." />;
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PAID':
        return <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold">PAID</span>;
      case 'OVERDUE':
        return <span className="px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-bold">OVERDUE</span>;
      case 'PARTIAL':
        return <span className="px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-bold">PARTIAL</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 text-[10px] font-bold">PENDING</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Collection KPI Header */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Billed</div>
          <div className="text-2xl font-black text-white mt-1">₹{summary?.total_billed.toLocaleString()}</div>
          <div className="text-[11px] text-slate-400 mt-1">Academic Session 2024-25</div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Total Collected</div>
          <div className="text-2xl font-black text-white mt-1">₹{summary?.total_collected.toLocaleString()}</div>
          <div className="text-[11px] text-emerald-400 font-medium mt-1">
            {summary?.collection_rate_pct}% Collection Rate
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-xs font-semibold uppercase tracking-wider text-rose-400">Total Outstanding</div>
          <div className="text-2xl font-black text-white mt-1">₹{summary?.total_outstanding.toLocaleString()}</div>
          <div className="text-[11px] text-rose-400 font-medium mt-1">
            {summary?.overdue_count} Overdue Invoices
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-amber-400">On-Time Payers</div>
            <div className="text-2xl font-black text-white mt-1">{summary?.paid_count} Students</div>
            <div className="text-[11px] text-slate-400 mt-1">UPI & Online Gateway</div>
          </div>
          <CheckCircle2 className="w-8 h-8 text-emerald-400 opacity-80" />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="glass-panel rounded-2xl border border-slate-800/80 overflow-hidden">
        {/* Table Filter Controls */}
        <div className="px-6 py-4 border-b border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <h3 className="font-bold text-sm text-white flex items-center space-x-2">
            <CreditCard className="w-4 h-4 text-amber-400" />
            <span>Student Fee Invoice Ledger</span>
          </h3>

          <div className="flex items-center space-x-1.5 bg-slate-900/80 p-1 border border-slate-800 rounded-xl">
            {[
              { id: '', label: 'All Invoices' },
              { id: 'PAID', label: 'Paid' },
              { id: 'OVERDUE', label: 'Overdue' },
              { id: 'PARTIAL', label: 'Partial' },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setStatusFilter(item.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  statusFilter === item.id
                    ? 'bg-amber-500 text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Invoice Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="px-6 py-3">Student Name</th>
                <th className="px-6 py-3">Class</th>
                <th className="px-6 py-3">Fee Head</th>
                <th className="px-6 py-3">Term</th>
                <th className="px-6 py-3">Amount Due</th>
                <th className="px-6 py-3">Amount Paid</th>
                <th className="px-6 py-3">Due Date</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3 text-right">Payment Method</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-800/40 transition">
                  <td className="px-6 py-3.5 font-semibold text-white">
                    {inv.student_name}
                  </td>
                  <td className="px-6 py-3.5">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-indigo-300 text-[11px]">
                      {inv.section}
                    </span>
                  </td>
                  <td className="px-6 py-3.5 text-slate-300">
                    {inv.fee_head}
                  </td>
                  <td className="px-6 py-3.5 text-slate-400">
                    {inv.term_label}
                  </td>
                  <td className="px-6 py-3.5 font-mono font-bold text-white">
                    ₹{inv.amount_due.toLocaleString()}
                  </td>
                  <td className="px-6 py-3.5 font-mono font-semibold text-emerald-400">
                    ₹{inv.amount_paid.toLocaleString()}
                  </td>
                  <td className="px-6 py-3.5 font-mono text-[11px] text-slate-400">
                    {inv.due_date}
                  </td>
                  <td className="px-6 py-3.5">
                    {getStatusBadge(inv.status)}
                  </td>
                  <td className="px-6 py-3.5 text-right font-mono text-[11px] text-slate-400">
                    {inv.payment_method || 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
