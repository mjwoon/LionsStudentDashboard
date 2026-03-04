import { useState, useEffect } from 'react';
import { LogOut, Trash2 } from 'lucide-react';
import { api } from '../api';
import DataUploadTab from './DataUploadTab';
import DiagnosisManagementTab from './DiagnosisManagementTab';
import SystemStatsTab from './SystemStatsTab';

type TabType = 'upload' | 'diagnosis' | 'stats';

const ADMIN_PASSWORD = 'admin@2048';

export default function AdminView() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('upload');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteResult, setDeleteResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    if (sessionStorage.getItem('admin_authenticated') === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = () => {
    if (password === ADMIN_PASSWORD) {
      setIsAuthenticated(true);
      sessionStorage.setItem('admin_authenticated', 'true');
      setError(false);
      setPassword('');
    } else {
      setError(true);
      setPassword('');
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    sessionStorage.removeItem('admin_authenticated');
    setActiveTab('upload');
  };

  const handleDeleteAll = async () => {
    setDeleting(true);
    try {
      const result = await api.admin.deleteAllData();
      setDeleteResult(result);
    } catch {
      setDeleteResult({ success: false, message: '삭제 중 오류가 발생했습니다.' });
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[80vh]">
        <div className="bg-white rounded-3xl shadow-[0px_4px_20px_0px_rgba(0,0,0,0.1)] p-12 w-full max-w-[500px] inline-flex flex-col items-center gap-10">

          {/* Lock icon */}
          <div className="w-[112px] h-[112px] rounded-full bg-[#EBF4FF] flex items-center justify-center shrink-0">
            <svg width="52" height="52" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M19 11H5C3.89543 11 3 11.8954 3 13V20C3 21.1046 3.89543 22 5 22H19C20.1046 22 21 21.1046 21 20V13C21 11.8954 20.1046 11 19 11Z" stroke="#1e3a5f" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M7 11V7C7 5.67392 7.52678 4.40215 8.46447 3.46447C9.40215 2.52678 10.6739 2 12 2C13.3261 2 14.5979 2.52678 15.5355 3.46447C16.4732 4.40215 17 5.67392 17 7V11" stroke="#1e3a5f" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>

          {/* Title */}
          <div className="flex flex-col items-center gap-1 text-center">
            <div className="justify-center font-bold text-3xl text-black leading-normal">관리자 인증</div>
            <div className="justify-center text-lg text-black/50 leading-normal">관리자 암호를 입력해주세요</div>
          </div>

          {/* Form */}
          <div className="self-stretch flex flex-col justify-start gap-5 w-full">
            <div className="self-stretch flex flex-col gap-3.5 ">
              <label className="text-[20px] text-[#1a1a1a]">암호</label>
              <div className={`flex items-center justify-between h-[60px] px-5 rounded-lg border bg-white ${error ? 'border-red-400' : 'border-black/10'}`}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError(false); }}
                  onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
                  placeholder="비밀번호를 입력하세요"
                  className="flex-1 min-w-0 text-[20px] text-[#1a1a1a] placeholder-[#e5e7eb] outline-none bg-transparent"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="shrink-0 ml-3 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
                  aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 보기'}
                >
                  {showPassword ? (
                    <svg width="18" height="16" viewBox="0 0 22 18" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M1 1L21 17M8.5 7.5C8.18692 7.93469 8 8.46894 8 9C8 10.6569 9.34315 12 11 12C11.5311 12 12.0653 11.813 12.5 11.5M4.5 4.5C2.33333 6 1 8 1 9C1 11 5.58824 16 11 16C13.1667 16 15.1667 15.1667 16.5 14M9 3.08C9.33 3.03 9.66 3 10 3C15.41 3 20 8 20 9C20 9.61 19.33 10.83 18.11 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : (
                    <svg width="18" height="14" viewBox="0 0 22 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M11 1C5.58824 1 1 6 1 7C1 8 5.58824 13 11 13C16.4118 13 21 8 21 7C21 6 16.4118 1 11 1Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M11 10C12.6569 10 14 8.65685 14 7C14 5.34315 12.6569 4 11 4C9.34315 4 8 5.34315 8 7C8 8.65685 9.34315 10 11 10Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </button>
              </div>
              {error && (
                <div className="flex items-center gap-1.5">
                  <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10.85 6.90587V11.3503M10.85 20.8501C5.32713 20.8501 0.849976 16.3729 0.849976 10.8501C0.849976 5.32725 5.32713 0.850098 10.85 0.850098C16.3728 0.850098 20.85 5.32725 20.85 10.8501C20.85 16.3729 16.3728 20.8501 10.85 20.8501ZM10.9053 14.6836V14.7948L10.7946 14.7943V14.6836H10.9053Z" stroke="#FF0000" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <p className="text-red-500 text-sm">암호가 올바르지 않습니다.</p>
                </div>
              )}
            </div>

            <button
              onClick={handleLogin}
              className="h-[60px] w-full rounded-lg text-white text-[20px] font-semibold cursor-pointer shadow-[0px_0px_12.3px_0px_rgba(12,66,120,0.5)] hover:opacity-90 transition-opacity"
              style={{ background: 'linear-gradient(90deg, #0E4A84 0%, #0A3A6B 100%)' }}
            >
              접속하기
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 인증된 경우 관리자 화면 표시

  return (
    <div>
      <div className="py-4 md:py-6">
        {/* 헤더 */}
        <div className="flex items-start justify-between mb-4 ">
          <div>
            <h1 className="text-2xl md:text-3xl lg:text-3xl font-bold text-[#101828]">관리자</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setShowDeleteConfirm(true); setDeleteResult(null); }}
              className="flex items-center gap-1.5 px-4 py-2 bg-white border border-red-200 text-red-600 rounded-lg hover:bg-red-50 cursor-pointer"
            >
              <Trash2 className="h-4 w-4" />
              <span className="text-[12pt] font-medium">데이터 초기화</span>
            </button>
            <button
              onClick={handleLogout}
              className="flex items-center px-4 py-2 bg-white border border-black/10 rounded-lg hover:bg-gray-50 cursor-pointer"
            >
              <LogOut className="h-4 w-4" />
              <span className="text-[12pt] font-medium text-[#101828]">로그아웃</span>
            </button>
          </div>
        </div>

        {/* 삭제 결과 알림 */}
        {deleteResult && (
          <div className={`mb-4 px-4 py-3 rounded-lg text-sm flex items-center justify-between ${deleteResult.success ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
            <span>{deleteResult.message}</span>
            <button onClick={() => setDeleteResult(null)} className="ml-4 text-current opacity-60 hover:opacity-100 cursor-pointer">✕</button>
          </div>
        )}

        {/* 삭제 확인 모달 */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md mx-4">
              <div className="flex flex-col items-center gap-4 text-center">
                <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center">
                  <Trash2 className="h-7 w-7 text-red-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-[#101828] mb-1">전체 데이터 초기화</h2>
                  <p className="text-sm text-gray-500">업로드된 모든 데이터(학생, 과목, 수강내역, 학과 등)가<br />영구적으로 삭제됩니다. 계속하시겠습니까?</p>
                </div>
                <div className="flex gap-3 w-full mt-2">
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    disabled={deleting}
                    className="flex-1 py-2.5 rounded-lg border border-black/10 text-[#101828] font-medium hover:bg-gray-50 cursor-pointer disabled:opacity-50"
                  >
                    취소
                  </button>
                  <button
                    onClick={handleDeleteAll}
                    disabled={deleting}
                    className="flex-1 py-2.5 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 cursor-pointer disabled:opacity-50"
                  >
                    {deleting ? '삭제 중...' : '삭제'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 탭 네비게이션 */}
        <div className="flex items-start gap-0 mb-6 border-b border-[#e5e7eb]">
         <button
              onClick={() => setActiveTab('upload')}
              className={`px-6 py-6 text-xl font-semibold transition-all cursor-pointer ${activeTab === 'upload'
                ? 'text-[#0e4a84] border-b-2 border-[#0e4a84] font-bold'
                : 'text-[#6a7282] font-medium'
                }`}
            >
              데이터 업로드
            </button>
            <button
              onClick={() => setActiveTab('diagnosis')}
              className={`px-6 py-6 text-xl font-semibold transition-all cursor-pointer ${activeTab === 'diagnosis'
                ? 'text-[#0e4a84] border-b-2 border-[#0e4a84] font-bold'
                : 'text-[#6a7282] font-medium'
                }`}
            >
              진단 관리
            </button>
            <button
              onClick={() => setActiveTab('stats')}
              className={`px-6 py-6 text-xl font-semibold transition-all cursor-pointer ${activeTab === 'stats'
                ? 'text-[#0e4a84] border-b-2 border-[#0e4a84] font-bold'
                : 'text-[#6a7282] font-medium'
                }`}
            >
              시스템 현황
            </button>
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
