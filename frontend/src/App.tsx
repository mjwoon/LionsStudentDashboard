import { useState } from 'react';
import { GraduationCap, Users, BarChart3 } from 'lucide-react';
import DashboardView from './components/DashboardView';
import StudentDetailView from './components/StudentDetailView';

export default function App() {
  const [activeView, setActiveView] = useState<'dashboard' | 'student'>('dashboard');

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      {/* 상단 네비게이션 바 */}
      <header className="bg-white border-b border-gray-200">
        <div className="flex items-center justify-center px-8 py-4">
          <div className="flex items-center gap-8">
            {/* 로고 */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <GraduationCap className="h-6 w-6 text-white" />
              </div>
              <h1 className="text-gray-900">학생 관리 시스템</h1>
            </div>

            {/* 네비게이션 메뉴 */}
            <nav className="flex items-center gap-2">
            <button
              onClick={() => setActiveView('dashboard')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeView === 'dashboard'
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <BarChart3 className="h-5 w-5" />
              <span>전체 현황</span>
            </button>
            <button
              onClick={() => setActiveView('student')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeView === 'student'
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Users className="h-5 w-5" />
              <span>학생 관리</span>
            </button>
          </nav>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="flex-1">
        {activeView === 'dashboard' && <DashboardView />}
        {activeView === 'student' && <StudentDetailView />}
      </main>
    </div>
  );
}