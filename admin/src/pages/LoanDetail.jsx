import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getLoan, approveLoan, rejectLoan, disburseLoan,
  getRepayments, markRepaymentPaid,
} from '../api/loans';

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  disbursed: 'bg-blue-100 text-blue-800',
  paid: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
};

export default function LoanDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loan, setLoan] = useState(null);
  const [repayments, setRepayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showDisburseModal, setShowDisburseModal] = useState(false);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    try {
      const [loanRes, repRes] = await Promise.all([
        getLoan(id),
        getRepayments(id).catch(() => ({ data: [] })),
      ]);
      setLoan(loanRes.data);
      setRepayments(repRes.data);
    } catch {
      setError('Failed to load loan.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function handleApprove() {
    setActionLoading('approve');
    try {
      await approveLoan(id);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Approve failed');
    } finally {
      setActionLoading('');
    }
  }

  async function handleReject() {
    if (!rejectReason.trim()) return;
    setActionLoading('reject');
    try {
      await rejectLoan(id, rejectReason.trim());
      setShowRejectModal(false);
      setRejectReason('');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Reject failed');
    } finally {
      setActionLoading('');
    }
  }

  async function handleDisburse() {
    if (!referenceNumber.trim()) return;
    setActionLoading('disburse');
    try {
      await disburseLoan(id, referenceNumber.trim());
      setShowDisburseModal(false);
      setReferenceNumber('');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Disburse failed');
    } finally {
      setActionLoading('');
    }
  }

  async function handleMarkPaid(repaymentId) {
    setActionLoading(`pay-${repaymentId}`);
    try {
      await markRepaymentPaid(id, repaymentId);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to mark paid');
    } finally {
      setActionLoading('');
    }
  }

  if (loading) return <div className="text-center py-12 text-gray-400">Loading…</div>;
  if (!loan) return <div className="text-center py-12 text-red-400">{error || 'Loan not found.'}</div>;

  return (
    <div className="max-w-3xl">
      <button onClick={() => navigate(-1)} className="text-indigo-600 hover:underline text-sm mb-4 inline-block">
        ← Back
      </button>

      {error && <div className="bg-red-50 text-red-600 rounded-lg p-3 mb-4 text-sm">{error}</div>}

      {/* Loan info card */}
      <div className="bg-white rounded-xl shadow p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-800">Loan #{loan.id.slice(0, 8)}…</h2>
            <p className="text-sm text-gray-400 mt-1">{loan.user_email} · {loan.user_phone}</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[loan.status] || 'bg-gray-100 text-gray-600'}`}>
            {loan.status.toUpperCase()}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          {[
            ['Amount', `₹${loan.amount?.toLocaleString('en-IN')}`],
            ['Tenure', `${loan.tenure_months} months`],
            ['Purpose', loan.purpose],
            ['CIBIL Score', loan.cibil_score],
            ['Monthly Income', `₹${loan.monthly_income?.toLocaleString('en-IN')}`],
            ['Interest Rate', loan.annual_interest_rate ? `${loan.annual_interest_rate}% p.a.` : '—'],
            ['Processing Fee', loan.processing_fee ? `₹${loan.processing_fee?.toLocaleString('en-IN')}` : '—'],
            ['Applied On', new Date(loan.created_at).toLocaleDateString('en-IN')],
          ].map(([label, value]) => (
            <div key={label}>
              <span className="text-gray-400">{label}</span>
              <p className="font-medium text-gray-800">{value}</p>
            </div>
          ))}
          {loan.rejection_reason && (
            <div className="col-span-2">
              <span className="text-gray-400">Rejection Reason</span>
              <p className="font-medium text-red-600">{loan.rejection_reason}</p>
            </div>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 mb-6 flex-wrap">
        {loan.status === 'pending' && (
          <>
            <button
              onClick={handleApprove}
              disabled={!!actionLoading}
              className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {actionLoading === 'approve' ? 'Approving…' : 'Approve'}
            </button>
            <button
              onClick={() => setShowRejectModal(true)}
              disabled={!!actionLoading}
              className="bg-red-500 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-red-600 disabled:opacity-50"
            >
              Reject
            </button>
          </>
        )}
        {loan.status === 'approved' && !loan.disbursement && (
          <button
            onClick={() => setShowDisburseModal(true)}
            disabled={!!actionLoading}
            className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            Disburse Loan
          </button>
        )}
      </div>

      {/* Repayment schedule */}
      {repayments.length > 0 && (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <div className="px-6 py-4 border-b">
            <h3 className="font-semibold text-gray-800">Repayment Schedule</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">#</th>
                <th className="px-4 py-3 text-left">Due Date</th>
                <th className="px-4 py-3 text-left">EMI</th>
                <th className="px-4 py-3 text-left">Principal</th>
                <th className="px-4 py-3 text-left">Interest</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Penalty</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {repayments.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500">{r.installment_number}</td>
                  <td className="px-4 py-3">{new Date(r.due_date).toLocaleDateString('en-IN')}</td>
                  <td className="px-4 py-3 font-medium">₹{r.emi_amount?.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-gray-500">₹{r.principal?.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-gray-500">₹{r.interest?.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[r.status] || 'bg-gray-100 text-gray-600'}`}>
                      {r.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-red-600 text-sm">
                    {r.penalty_amount ? `₹${parseFloat(r.penalty_amount).toLocaleString('en-IN')}` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {(r.status === 'pending' || r.status === 'overdue') && (
                      <button
                        onClick={() => handleMarkPaid(r.id)}
                        disabled={actionLoading === `pay-${r.id}`}
                        className="text-indigo-600 hover:underline text-xs font-medium disabled:opacity-50"
                      >
                        {actionLoading === `pay-${r.id}` ? 'Saving…' : 'Mark Paid'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reject modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="font-semibold text-gray-800 mb-3">Reject Loan</h3>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm h-24 resize-none focus:outline-none focus:ring-2 focus:ring-red-400"
              placeholder="Reason for rejection…"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
            <div className="flex gap-3 mt-4 justify-end">
              <button onClick={() => setShowRejectModal(false)} className="text-sm text-gray-500 hover:text-gray-700">
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={!rejectReason.trim() || actionLoading === 'reject'}
                className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-600 disabled:opacity-50"
              >
                {actionLoading === 'reject' ? 'Rejecting…' : 'Confirm Reject'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Disburse modal */}
      {showDisburseModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="font-semibold text-gray-800 mb-4">Confirm Disbursement</h3>
            <div className="bg-gray-50 rounded-lg p-4 mb-4 text-sm space-y-2">
              <p className="text-gray-500 text-xs uppercase font-medium mb-1">Borrower's Bank Details</p>
              <div className="flex justify-between">
                <span className="text-gray-500">Account Number</span>
                <span className="font-medium">{loan.bank_account_number || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">IFSC Code</span>
                <span className="font-medium">{loan.ifsc_code || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Net Amount</span>
                <span className="font-medium text-green-700">
                  ₹{(loan.amount - loan.processing_fee)?.toLocaleString('en-IN')}
                </span>
              </div>
            </div>
            <label className="block text-sm text-gray-600 mb-1">Transaction / Reference Number</label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="e.g. UTR123456789"
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value)}
            />
            <div className="flex gap-3 mt-4 justify-end">
              <button onClick={() => setShowDisburseModal(false)} className="text-sm text-gray-500 hover:text-gray-700">
                Cancel
              </button>
              <button
                onClick={handleDisburse}
                disabled={!referenceNumber.trim() || actionLoading === 'disburse'}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {actionLoading === 'disburse' ? 'Disbursing…' : 'Confirm Disburse'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
