import { useEffect, useState } from 'react';
import { getPricing, updatePricing } from '../api/loans';

export default function Pricing() {
  const [tiers, setTiers] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  async function load() {
    const res = await getPricing();
    setTiers(res.data);
  }

  useEffect(() => { load(); }, []);

  function startEdit(tier) {
    setEditing(tier.id);
    setForm({
      annual_interest_rate: tier.annual_interest_rate,
      processing_fee_pct: tier.processing_fee_pct,
      early_closure_fee_pct: tier.early_closure_fee_pct,
      late_payment_penalty_pct: tier.late_payment_penalty_pct,
    });
    setSuccess('');
    setError('');
  }

  async function handleSave(id) {
    setSaving(true);
    setError('');
    try {
      await updatePricing(id, {
        annual_interest_rate: parseFloat(form.annual_interest_rate),
        processing_fee_pct: parseFloat(form.processing_fee_pct),
        early_closure_fee_pct: parseFloat(form.early_closure_fee_pct),
        late_payment_penalty_pct: parseFloat(form.late_payment_penalty_pct),
      });
      setEditing(null);
      setSuccess('Pricing updated successfully.');
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Risk-Based Pricing</h1>
      {success && <div className="bg-green-50 text-green-700 rounded-lg p-3 mb-4 text-sm">{success}</div>}
      {error && <div className="bg-red-50 text-red-600 rounded-lg p-3 mb-4 text-sm">{error}</div>}

      <div className="space-y-4">
        {tiers.map((tier) => (
          <div key={tier.id} className="bg-white rounded-xl shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-semibold text-gray-800">{tier.tier_label}</h3>
                <p className="text-xs text-gray-400">CIBIL {tier.cibil_min} – {tier.cibil_max}</p>
              </div>
              {editing !== tier.id ? (
                <button
                  onClick={() => startEdit(tier)}
                  className="text-indigo-600 hover:underline text-sm font-medium"
                >
                  Edit
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditing(null)}
                    className="text-gray-400 hover:text-gray-600 text-sm"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleSave(tier.id)}
                    disabled={saving}
                    className="bg-indigo-600 text-white px-3 py-1 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {saving ? 'Saving…' : 'Save'}
                  </button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              {[
                ['annual_interest_rate', 'Interest Rate (% p.a.)'],
                ['processing_fee_pct', 'Processing Fee (%)'],
                ['early_closure_fee_pct', 'Early Closure Fee (%)'],
                ['late_payment_penalty_pct', 'Late Payment Penalty (%)'],
              ].map(([field, label]) => (
                <div key={field}>
                  <span className="text-gray-400 text-xs">{label}</span>
                  {editing === tier.id ? (
                    <input
                      type="number"
                      step="0.1"
                      className="block w-full border rounded-lg px-2 py-1 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                      value={form[field]}
                      onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                    />
                  ) : (
                    <p className="font-medium text-gray-800">{tier[field]}%</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
