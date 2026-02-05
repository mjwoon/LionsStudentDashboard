import { useState, useEffect } from 'react';
import { Upload, Activity, BarChart, Lock, LogOut } from 'lucide-react';
import DataUploadTab from './DataUploadTab';
import DiagnosisManagementTab from './DiagnosisManagementTab';
import SystemStatsTab from './SystemStatsTab';

type TabType = 'upload' | 'diagnosis' | 'stats';

const ADMIN_PASSWORD = 'lions'; // 실제 환경에서는 환경변수로 관리

export default function AdminView() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<TabType>('upload');

  // 세션 스토리지에서 인증 상태 확인
  useEffect(() => {
    const authStatus = sessionStorage.getItem('admin_authenticated');
    if (authStatus === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (password === ADMIN_PASSWORD) {
      setIsAuthenticated(true);
      sessionStorage.setItem('admin_authenticated', 'true');
      setError('');
      setPassword('');
    } else {
      setError('암호가 올바르지 않습니다');
      setPassword('');
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    sessionStorage.removeItem('admin_authenticated');
    setActiveTab('upload');
  };

  // 인증되지 않은 경우 로그인 화면 표시
  if (!isAuthenticated) {
    return (
      <div className="bg-linear-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8 w-full max-w-sm md:max-w-md">
          <div className="text-center mb-6 md:mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 md:w-16 md:h-16 bg-blue-100 rounded-full mb-3 md:mb-4">
              <Lock className="h-6 w-6 md:h-8 md:w-8 text-blue-600" />
            </div>
            <h1 className="text-xl md:text-2xl font-bold text-gray-900 mb-1 md:mb-2">관리자 인증</h1>
            <p className="text-sm md:text-base text-gray-600">관리자 암호를 입력해주세요</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="password" className="block text-xs md:text-sm font-medium text-gray-700 mb-1 md:mb-2">
                암호
              </label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 md:px-4 py-2 md:py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm md:text-base"
                placeholder="암호를 입력하세요"
                autoFocus
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-2 md:p-3">
                <p className="text-xs md:text-sm text-red-800">{error}</p>
              </div>
            )}

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-2 md:py-3 rounded-lg hover:bg-blue-700 transition-colors font-semibold text-sm md:text-base"
            >
              로그인
            </button>
          </form>

          <div className="mt-4 md:mt-6 pt-4 md:pt-6 border-t border-gray-200">
            <p className="text-[10px] md:text-xs text-gray-500 text-center">
              관리자 권한이 필요합니다
            </p>
          </div>
        </div>
      </div>
    );
  }

  // 인증된 경우 관리자 화면 표시

  const tabs = [
    { id: 'upload' as TabType, label: '데이터 업로드', icon: Upload },
    { id: 'diagnosis' as TabType, label: '진단 관리', icon: Activity },
    { id: 'stats' as TabType, label: '시스템 현황', icon: BarChart },
  ];

  return (
    <div className="p-4 md:p-6 lg:p-8 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* 헤더 */}
        <div className="mb-6 md:mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-1 md:mb-2">관리자</h1>
            <p className="text-sm md:text-base text-gray-600">
              데이터 업로드, 진단 관리 및 시스템 현황을 확인할 수 있습니다
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 md:px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors self-start"
          >
            <LogOut className="h-4 w-4" />
            <span>로그아웃</span>
          </button>
        </div>

        {/* 탭 네비게이션 */}
        <div className="bg-white rounded-lg shadow mb-4 md:mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px overflow-x-auto">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-1.5 md:gap-2 px-3 md:px-4 lg:px-6 py-3 md:py-4 border-b-2 font-medium text-xs md:text-sm transition-colors whitespace-nowrap ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <Icon className="h-4 w-4 md:h-5 md:w-5" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        {/* 탭 컨텐츠 */}
        <div>
          {activeTab === 'upload' && <DataUploadTab />}
          {activeTab === 'diagnosis' && <DiagnosisManagementTab />}
          {activeTab === 'stats' && <SystemStatsTab />}
        </div>
      </div>
    </div>
  );
}
