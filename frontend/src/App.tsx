import { useNavigate, useLocation } from 'react-router-dom';
import DashboardView from './components/DashboardView';
import StudentDetailView from './components/StudentDetailView';
import AdminView from './components/AdminView';

const LOGO_URL = '/HYU_logo.svg';
const SYMBOL_URL = '/HYU_logotype_ERICA_white_kor.png';

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  
  const getActiveView = () => {
    const path = location.pathname;
    if (path === '/student') return 'student';
    if (path === '/admin') return 'admin';
    return 'dashboard';
  };
  
  const activeView = getActiveView();

  return (
    <div className="flex flex-col min-h-screen bg-[#f5f7fa]">
      {/* Header Navigation */}
      <header className="bg-linear-to-r from-[#0e4a84] to-[#0a3a6b] border-b border-[#e5e7eb] h-22">
        <div className="flex items-center justify-between pl-18 pr-22 h-full">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-3 pr-4 border-r border-[#898c8e]">
              <img src={LOGO_URL} alt="Logo" className="w-12 h-12 object-contain" />
              <img src={SYMBOL_URL} alt="Symbol" className="h-8 object-contain" />
            </div>
            <div className="flex items-center gap-3">
              <div className="text-[#fafafa] text-2xl font-semibold">학생 관리 시스템</div>
            </div>
          </div>
          <nav className="flex gap-4">
            <button
              onClick={() => navigate('/')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors cursor-pointer ${
                activeView === 'dashboard'
                  ? 'bg-white/15'
                  : 'hover:bg-white/10'
              }`}
            >
              <span className="text-[13pt] font-medium text-white">전체 현황</span>
            </button>
            <button
              onClick={() => navigate('/student')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors cursor-pointer ${
                activeView === 'student'
                  ? 'bg-white/15'
                  : 'hover:bg-white/10'
              }`}
            >
              <span className="text-[13pt] font-medium text-white">학생 관리</span>
            </button>
            <button
              onClick={() => navigate('/admin')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors cursor-pointer ${
                activeView === 'admin'
                  ? 'bg-white/15'
                  : 'hover:bg-white/10'
              }`}
            >
              <span className="text-[13pt] font-medium text-white">관리자</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-30 py-1">
        <div style={{ display: activeView === 'dashboard' ? 'block' : 'none' }}>
          <DashboardView />
        </div>
        <div style={{ display: activeView === 'student' ? 'block' : 'none' }}>
          <StudentDetailView />
        </div>
        <div style={{ display: activeView === 'admin' ? 'block' : 'none' }}>
          <AdminView />
        </div>
      </main>
    </div>
  );
}