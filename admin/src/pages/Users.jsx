import { useEffect, useState } from 'react';
import api from '../api/client';

const ROLE_LABELS = { admin: 'Admin', superuser: 'Support' };
const ROLE_COLORS = {
  admin: 'bg-purple-100 text-purple-800',
  superuser: 'bg-blue-100 text-blue-700',
};

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ email: '', phone: '', password: '', role: 'superuser' });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [resetTarget, setResetTarget] = useState(null); // { id, email }
  const [newPassword, setNewPassword] = useState('');
  const [resetError, setResetError] = useState('');
  const [resetting, setResetting] = useState(false);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const r = await api.get('/admin/users');
      setUsers(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function createUser(e) {
    e.preventDefault();
    setSubmitting(true);
    setFormError('');
    try {
      await api.post('/admin/users', form);
      setShowForm(false);
      setFormError('');
      setForm({ email: '', phone: '', password: '', role: 'superuser' });
      await load();
    } catch (e) {
      const d = e.response?.data?.detail;
      setFormError(Array.isArray(d) ? d.map(x => x.msg).join(', ') : (d || 'Failed to create user'));
    } finally {
      setSubmitting(false);
    }
  }

  async function changeRole(userId, newRole) {
    try {
      await api.patch(`/admin/users/${userId}/role`, { role: newRole });
      load();
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to update role');
    }
  }

  async function resetPassword(e) {
    e.preventDefault();
    setResetting(true);
    setResetError('');
    try {
      await api.patch(`/admin/users/${resetTarget.id}/password`, { new_password: newPassword });
      setResetTarget(null);
      setNewPassword('');
    } catch (e) {
      const d = e.response?.data?.detail;
      setResetError(Array.isArray(d) ? d.map(x => x.msg).join(', ') : (d || 'Failed to reset password'));
    } finally {
      setResetting(false);
    }
  }

  async function deleteUser(userId, email) {
    if (!window.confirm(`Remove ${email}? This cannot be undone.`)) return;
    try {
      await api.delete(`/admin/users/${userId}`);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to delete user');
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Staff Users</h2>
          <p className="text-gray-500 text-sm mt-1">Manage admin and customer support accounts</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
        >
          + Add User
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold mb-4">Create Staff User</h3>
            <form onSubmit={createUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none"
                  placeholder="support@company.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input
                  type="text"
                  required
                  value={form.phone}
                  onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none"
                  placeholder="+919876543210"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none"
                >
                  <option value="superuser">Support (superuser)</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              {formError && <p className="text-red-600 text-sm">{formError}</p>}
              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setFormError(''); }}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submitting ? 'Creating…' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400">Loading…</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-5 py-3 font-medium text-gray-600">Email</th>
                <th className="text-left px-5 py-3 font-medium text-gray-600">Phone</th>
                <th className="text-left px-5 py-3 font-medium text-gray-600">Role</th>
                <th className="text-right px-5 py-3 font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center py-12 text-gray-400">No staff users found</td>
                </tr>
              )}
              {users.map(u => (
                <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50 transition">
                  <td className="px-5 py-3 font-medium text-gray-800">{u.email}</td>
                  <td className="px-5 py-3 text-gray-500">{u.phone}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${ROLE_COLORS[u.role] || 'bg-gray-100 text-gray-700'}`}>
                      {ROLE_LABELS[u.role] || u.role}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <div className="flex items-center gap-2 justify-end">
                      {u.role === 'superuser' ? (
                        <button
                          onClick={() => changeRole(u.id, 'admin')}
                          className="text-xs px-3 py-1 border rounded-lg text-gray-600 hover:border-indigo-400 hover:text-indigo-700 transition"
                        >
                          Promote to Admin
                        </button>
                      ) : (
                        <button
                          onClick={() => changeRole(u.id, 'superuser')}
                          className="text-xs px-3 py-1 border rounded-lg text-gray-600 hover:border-blue-400 hover:text-blue-700 transition"
                        >
                          Demote to Support
                        </button>
                      )}
                      <button
                        onClick={() => { setResetTarget({ id: u.id, email: u.email }); setNewPassword(''); setResetError(''); }}
                        className="text-xs px-3 py-1 border border-gray-200 rounded-lg text-gray-500 hover:border-indigo-300 hover:text-indigo-600 transition"
                      >
                        Reset Password
                      </button>
                      <button
                        onClick={() => deleteUser(u.id, u.email)}
                        className="text-xs px-3 py-1 border border-red-200 rounded-lg text-red-500 hover:bg-red-50 transition"
                      >
                        Remove
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {resetTarget && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h3 className="text-lg font-semibold mb-1">Reset Password</h3>
            <p className="text-sm text-gray-500 mb-4">{resetTarget.email}</p>
            <form onSubmit={resetPassword} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none"
                  placeholder="Min. 8 characters"
                  autoFocus
                />
              </div>
              {resetError && <p className="text-red-600 text-sm">{resetError}</p>}
              <div className="flex gap-3 justify-end pt-1">
                <button
                  type="button"
                  onClick={() => { setResetTarget(null); setResetError(''); }}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resetting}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                >
                  {resetting ? 'Saving…' : 'Set Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
        <p className="text-sm text-blue-800 font-medium">Role permissions</p>
        <ul className="text-xs text-blue-700 mt-2 space-y-1">
          <li><span className="font-semibold">Admin</span> — full access: approve/reject loans, disburse, override KYC, manage pricing, manage users</li>
          <li><span className="font-semibold">Support</span> — read-only: view loans, repayment schedules, disbursements, notifications, KYC profiles</li>
        </ul>
      </div>
    </div>
  );
}
