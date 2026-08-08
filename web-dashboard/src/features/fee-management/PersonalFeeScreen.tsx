import React, { useState, useEffect } from 'react';
import { 
  CreditCard, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  ArrowRight, 
  Receipt, 
  ShieldCheck,
  ExternalLink
} from 'lucide-react';
import { apiClient } from '../../api/client';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import type { FeeInvoice } from '../../types';

interface StudentFeeLedger {
  student_id: string;
  student_name: string;
  section: string;
  total_billed: number;
  total_paid: number;
  outstanding: number;
  invoices: FeeInvoice[];
}

interface PersonalFeeScreenProps {
  viewerRole: 'student' | 'parent' | string;
}

export const PersonalFeeScreen: React.FC<PersonalFeeScreenProps> = ({ viewerRole }) => {
  const [ledger, setLedger] = useState<StudentFeeLedger | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedInvoice, setSelectedInvoice] = useState<FeeInvoice | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<string>('UPI');
  const [paying, setPaying] = useState<boolean>(false);
  const [receiptResult, setReceiptResult] = useState<any | null>(null);

  const fetchLedger = async () => {
    setLoading(true);
    try {
      const endpoint = viewerRole === 'parent' ? '/fees/my-child' : '/fees/me';
      const res = await apiClient.get(endpoint);
      setLedger(res.data);
    } catch (err) {
      console.error('Error fetching fee ledger:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedger();
  }, [viewerRole]);

  const handlePay = async () => {
    if (!selectedInvoice) return;
    setPaying(true);
    setReceiptResult(null);
    try {
      const res = await apiClient.post('/fees/pay-invoice', {
        invoice_id: selectedInvoice.id,
        payment_method: paymentMethod,
      });
      setReceiptResult(res.data);
      // Refresh ledger
      await fetchLedger();
    } catch (err) {
      console.error('Payment error:', err);
      alert('Payment processing failed. Please try again.');
    } finally {
      setPaying(false);
    }
  };

  if (loading) {
    return <LoadingSpinner text="Loading fee account statement..." />;
  }

  if (!ledger) {
    return (
      <div className="glass-panel p-8 rounded-2xl text-center text-slate-400 text-sm">
        No fee statement found for this profile.
      </div>
    );
  }

  const hasOverdue = (ledger.invoices || []).some((i) => i.status === 'OVERDUE');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <CreditCard className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">
              {viewerRole === 'parent' ? "Child's Fee Account & Payments" : "My Student Fee Account"}
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Student: <strong className="text-white">{ledger.student_name}</strong> • Section: <span className="text-amber-400 font-semibold">{ledger.section}</span>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right">
            <div className="text-[10px] uppercase font-bold text-slate-400">Total Outstanding</div>
            <div className={`text-2xl font-black ${ledger.outstanding > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
              ₹{ledger.outstanding.toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Overdue Warning */}
      {hasOverdue && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center space-x-3 shadow-lg shadow-amber-500/5">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <div>
            <strong className="font-bold">Overdue Invoices Pending:</strong> You have one or more overdue invoices. Please settle outstanding dues via Razorpay Sandbox to avoid late charges.
          </div>
        </div>
      )}

      {/* Ledger Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 font-semibold">Total Billed</span>
          <div className="text-2xl font-bold text-white">₹{ledger.total_billed.toLocaleString()}</div>
        </div>
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 font-semibold">Total Paid</span>
          <div className="text-2xl font-bold text-emerald-400">₹{ledger.total_paid.toLocaleString()}</div>
        </div>
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 font-semibold">Outstanding Dues</span>
          <div className="text-2xl font-bold text-amber-400">₹{ledger.outstanding.toLocaleString()}</div>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="font-bold text-sm text-white">Fee Invoices & Receipts</h3>
          <span className="text-xs text-slate-400">{(ledger.invoices || []).length} Invoices</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Fee Head</th>
                <th className="py-3 px-4">Term</th>
                <th className="py-3 px-4 text-right">Amount Due</th>
                <th className="py-3 px-4 text-right">Amount Paid</th>
                <th className="py-3 px-4">Due Date</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {(ledger.invoices || []).map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-900/40 transition">
                  <td className="py-3.5 px-4 font-bold text-white">{inv.fee_head}</td>
                  <td className="py-3.5 px-4 text-slate-400">{inv.term_label || 'Annual Term'}</td>
                  <td className="py-3.5 px-4 text-right font-mono text-slate-200">₹{inv.amount_due}</td>
                  <td className="py-3.5 px-4 text-right font-mono text-emerald-400">₹{inv.amount_paid}</td>
                  <td className="py-3.5 px-4 font-mono text-slate-400">{inv.due_date}</td>
                  <td className="py-3.5 px-4 text-center">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-black ${
                      inv.status === 'PAID'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : inv.status === 'OVERDUE'
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    {inv.status !== 'PAID' ? (
                      <button
                        onClick={() => {
                          setSelectedInvoice(inv);
                          setReceiptResult(null);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] shadow-sm shadow-indigo-600/30 transition"
                      >
                        Pay Now
                      </button>
                    ) : (
                      <span className="text-[11px] text-slate-500 font-mono">
                        {inv.transaction_ref ? inv.transaction_ref.slice(0, 14) : 'PAID'}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Razorpay Sandbox Payment Modal */}
      {selectedInvoice && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md p-6 rounded-3xl border border-slate-800 shadow-2xl space-y-4">
            <div className="flex items-center space-x-2 text-indigo-400">
              <ShieldCheck className="w-5 h-5" />
              <h3 className="font-bold text-base text-white">Razorpay Test Sandbox Payment</h3>
            </div>
            <p className="text-xs text-slate-400">
              Paying: <strong className="text-white">{selectedInvoice.fee_head}</strong> • Amount:{' '}
              <strong className="text-emerald-400 font-mono">₹{selectedInvoice.outstanding || selectedInvoice.amount_due}</strong>
            </p>

            {receiptResult ? (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 space-y-2 text-xs">
                <div className="flex items-center space-x-1.5 font-bold text-emerald-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Payment Successful!</span>
                </div>
                <p>Transaction Ref: <strong className="font-mono text-white">{receiptResult.razorpay_payment_id}</strong></p>
                <div className="pt-2">
                  <button
                    onClick={() => {
                      setSelectedInvoice(null);
                      setReceiptResult(null);
                    }}
                    className="w-full py-2 rounded-xl bg-emerald-600 text-white font-bold text-xs"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <label className="text-xs text-slate-300 font-semibold">Select Payment Method:</label>
                  <div className="grid grid-cols-3 gap-2">
                    {['UPI', 'CARD', 'NETBANKING'].map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setPaymentMethod(m)}
                        className={`py-2 rounded-xl text-xs font-bold border transition ${
                          paymentMethod === m
                            ? 'bg-indigo-600 text-white border-indigo-500'
                            : 'bg-slate-900 text-slate-400 border-slate-800'
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end space-x-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedInvoice(null)}
                    className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 hover:text-white text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handlePay}
                    disabled={paying}
                    className="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:opacity-95 text-white text-xs font-bold shadow-lg shadow-emerald-600/30 disabled:opacity-50"
                  >
                    {paying ? 'Processing...' : `Pay ₹${selectedInvoice.outstanding || selectedInvoice.amount_due}`}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
