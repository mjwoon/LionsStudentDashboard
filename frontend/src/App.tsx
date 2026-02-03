import { useState } from 'react';
import DashboardView from './components/DashboardView';
import StudentDetailView from './components/StudentDetailView';
import AdminView from './components/AdminView';

const LOGO_URL = 'http://localhost:3845/assets/c974f2e7e9b303389f9f28541314404c25977105.svg';

export default function App() {
  const [activeView, setActiveView] = useState<'dashboard' | 'student' | 'admin'>('dashboard');

  return (
    <div className="flex flex-col min-h-screen bg-[#f5f7fa]">
      {/* Header Navigation */}
      <header className="bg-linear-to-r from-[#0e4a84] to-[#0a3a6b] border-b border-[#e5e7eb] h-24">
        <div className="flex items-center justify-between px-8 h-full">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12">
              <img src={LOGO_URL} alt="Logo" className="w-full h-full object-contain" />
            </div>
            <div>
              <div className="text-white text-2xl font-bold">학생 관리 시스템</div>
              <div className="text-white text-sm opacity-50">HANYANG ERICA</div>
            </div>
          </div>
          <nav className="flex gap-2">
            <button
              onClick={() => setActiveView('dashboard')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeView === 'dashboard'
                  ? 'bg-white/15'
                  : 'hover:bg-white/10'
              }`}
            >
              <span className="text-sm font-medium text-white">전체 현황</span>
            </button>
            <button
              onClick={() => setActiveView('student')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeView === 'student'
                  ? 'bg-white/15'
                  : 'hover:bg-white/10'
              }`}
            >
              <span className="text-sm font-medium text-white">학생 관리</span>
            </button>
            <button
              onClick={() => setActiveView('admin')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeView === 'admin'
                  ? 'bg-white/15'
                  : 'hover:bg-white/10'
              }`}
            >
              <span className="text-sm font-medium text-white">관리자</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {activeView === 'dashboard' && <DashboardView />}
        {activeView === 'student' && <StudentDetailView />}
        {activeView === 'admin' && <AdminView />}
      </main>
    </div>
  );
}