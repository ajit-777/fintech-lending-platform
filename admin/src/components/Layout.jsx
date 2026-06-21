import { NavLink, useNavigate } from 'react-router-dom';

export default function Layout({ children }) {
  const navigate = useNavigate();

  function logout() {
    localStorage.removeItem('admin_token');
    navigate('/login');
  }

  const navClass = ({ isActive }) =>
    `block px-4 py-2 rounded-lg text-sm font-medium transition ${
      isActive ? 'bg-indigo-700 text-white' : 'text-indigo-200 hover:bg-indigo-700 hover:text-white'
    }`;

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-56 bg-indigo-800 flex flex-col py-6 px-3">
        <div className="px-4 mb-8">
          <h1 className="text-white font-bold text-lg">Admin Portal</h1>
          <p className="text-indigo-300 text-xs mt-1">Fintech Lending</p>
        </div>
        <nav className="flex-1 space-y-1">
          <NavLink to="/" end className={navClass}>Dashboard</NavLink>
          <NavLink to="/pricing" className={navClass}>Pricing Config</NavLink>
          <NavLink to="/users" className={navClass}>Staff Users</NavLink>
        </nav>
        <button
          onClick={logout}
          className="mx-1 mt-4 px-4 py-2 rounded-lg text-sm text-indigo-300 hover:bg-indigo-700 hover:text-white text-left transition"
        >
          Sign Out
        </button>
      </aside>
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  );
}
