import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getLoans } from '../api/loans';

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  disbursed: 'bg-blue-100 text-blue-800',
  closed: 'bg-gray-100 text-gray-600',
};

export default function Dashboard() {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [search, setSearch] = useState('');

  async function load(overrideSearch) {
    setLoading(true);
    try {
      const params = {};
      if (filter) params.status = filter;
      const term = overrideSearch !== undefined ? overrideSearch : search.trim();
      if (term) params.identifier = term;
      const res = await getLoans(params);
      setLoans(res.data);
    } catch {
      setLoans([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filter]);

  function handleSearch(e) {
    e.preventDefault();
    load();
  }

  function handleClearSearch() {
    setSearch('');
    load('');
  }

  const counts = loans.reduce((acc, l) => {
    acc[l.status] = (acc[l.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Loan Applications</h1>

      {/* Summary chips */}
      <div className="flex gap-3 mb-6 flex-wrap">
        {['pending', 'approved', 'disbursed', 'rejected', 'closed'].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(filter === s ? '' : s)}
            className={`px-4 py-2 rounded-full text-sm font-medium border transition ${
              filter === s ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-400'
            }`}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)} {counts[s] !== undefined ? `(${counts[s]})` : ''}
          </button>
        ))}
        {filter && (
          <button onClick={() => setFilter('')} className="text-sm text-gray-400 hover:text-gray-600 underline">
            Clear filter
          </button>
        )}
      </div>

      {/* Search by email/phone */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <input
          className="border rounded-lg px-3 py-2 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          placeholder="Search by email or phone…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700">
          Search
        </button>
        {search && (
          <button
            type="button"
            onClick={handleClearSearch}
            className="text-sm text-gray-400 hover:text-gray-600 underline"
          >
            Clear
          </button>
        )}
      </form>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading…</div>
      ) : loans.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No loans found.</div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Applicant</th>
                <th className="px-4 py-3 text-left">Amount</th>
                <th className="px-4 py-3 text-left">Tenure</th>
                <th className="px-4 py-3 text-left">Purpose</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Applied</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loans.map((loan) => (
                <tr key={loan.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">
                    {loan.user_email || '—'}<br />
                    <span className="text-xs text-gray-400">{loan.user_phone || ''}</span>
                  </td>
                  <td className="px-4 py-3">₹{loan.amount?.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3">{loan.tenure_months}m</td>
                  <td className="px-4 py-3 text-gray-500">{loan.purpose}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[loan.status] || 'bg-gray-100 text-gray-600'}`}>
                      {loan.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(loan.created_at).toLocaleDateString('en-IN')}
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/loans/${loan.id}`} className="text-indigo-600 hover:underline font-medium">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
