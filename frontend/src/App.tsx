import { useNavigate, useLocation, Routes, Route } from 'react-router-dom';
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
    if (path.startsWith('/student')) return 'student';
    if (path === '/admin') return 'admin';
    return 'dashboard';
  };
  
  const activeView = getActiveView();

  return (
    <div className="flex flex-col min-h-screen min-w-[1200px] bg-[#f5f7fa]">
      {/* Header Navigation */}
      <header className="bg-linear-to-r from-[#0e4a84] to-[#0a3a6b] border-b border-[#e5e7eb] h-16 md:h-20 lg:h-22">
        <div className="flex items-center justify-between px-2 sm:px-4 md:px-8 lg:px-16 xl:px-24 2xl:px-30 h-full max-w-[1920px] mx-auto">
          <div className="flex items-center gap-2 md:gap-3">
            <div className="flex items-center gap-2 md:gap-3 pr-2 md:pr-4 border-r border-[#fafafa] h-4 md:h-6">
              <img src={LOGO_URL} alt="Logo" className="w-8 h-8 md:w-10 md:h-10 lg:w-12 lg:h-12 object-contain" />
              <img src={SYMBOL_URL} alt="Symbol" className="h-5 md:h-6 lg:h-8 object-contain hidden sm:block" />
            </div>
            <div className="flex items-center gap-2 md:gap-3">
              <div className="text-[#fafafa] text-base md:text-xl lg:text-2xl font-semibold hidden sm:block">학생 관리 시스템</div>
              <div className="text-[#fafafa] text-sm font-semibold sm:hidden">학생관리</div>
            </div>
          </div>
          <nav className="flex gap-1 md:gap-2 lg:gap-4">
            <button
              onClick={() => navigate('/')}
              className={`flex items-center gap-1 md:gap-2 px-2 md:px-3 lg:px-4 py-1.5 md:py-2 rounded-lg transition-colors cursor-pointer ${
                activeView === 'dashboard'
                  ? 'bg-white/15'
                  : 'hover:bg-white/10'
              }`}
            >
              <span className="text-xs md:text-sm lg:text-[13pt] font-medium text-white">전체 현황</span>
            </button>
            <button
              onClick={() => navigate('/student')}
              className={`flex items-center gap-1 md:gap-2 px-2 md:px-3 lg:px-4 py-1.5 md:py-2 rounded-lg transition-colors cursor-pointer ${
                activeView === 'student'
                  ? 'bg-white/15'
                  : 'hover:bg-white/10'
              }`}
            >
              <span className="text-xs md:text-sm lg:text-[13pt] font-medium text-white">학생 관리</span>
            </button>
            <button
              onClick={() => navigate('/admin')}
              className={`flex items-center gap-1 md:gap-2 px-2 md:px-3 lg:px-4 py-1.5 md:py-2 rounded-lg transition-colors cursor-pointer ${
                activeView === 'admin'
                  ? 'bg-white/15'
                  : 'hover:bg-white/10'
              }`}
            >
              <span className="text-xs md:text-sm lg:text-[13pt] font-medium text-white">관리자</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-2 sm:px-4 md:px-8 lg:px-16 xl:px-24 2xl:px-30 py-1">
        <Routes>
          <Route path="/" element={<DashboardView />} />
          <Route path="/student" element={<StudentDetailView />} />
          <Route path="/student/:studentId" element={<StudentDetailView />} />
          <Route path="/admin" element={<AdminView />} />
        </Routes>
      </main>
    </div>
  );
}