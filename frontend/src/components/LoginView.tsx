import { useState } from 'react';

const ADMIN_PASSWORD = 'lions1234erica';
const HYU_SEAL = '/HYU_symbol_basic_png.png';

interface LoginViewProps {
  onLogin: () => void;
}

export default function LoginView({ onLogin }: LoginViewProps) {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(false);

  const handleSubmit = () => {
    if (password === ADMIN_PASSWORD) {
      localStorage.setItem('isAuthenticated', 'true');
      onLogin();
    } else {
      setError(true);
      setPassword('');
    }
  };

  return (
    <div
      className="relative min-h-screen w-full overflow-hidden flex flex-col"
      style={{ background: 'linear-gradient(113deg, #2A67A3 0%, #052F5B 100%), #F5F7FA' }}
    >
      {/* Decorative background circles */}
      <div className="absolute top-[-191px] right-[-100px] w-[486px] h-[486px] bg-white/5 rounded-full pointer-events-none" />
      <div className="absolute top-[-265px] left-[20%] w-[352px] h-[352px] bg-white/5 rounded-full pointer-events-none" />
      <div className="absolute top-[700px] right-[15%] w-[352px] h-[352px] bg-white/5 rounded-full pointer-events-none" />
      <div className="absolute bottom-[-120px] -left-[79px] w-[595px] h-[595px] bg-white/5 rounded-full pointer-events-none" />

      {/* Centered card */}
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="bg-white rounded-3xl shadow-[0px_4px_40px_0px_rgba(0,0,0,0.25)] p-12 w-full max-w-[500px] flex flex-col items-center gap-10">
          {/* University seal */}
          <img
            src={HYU_SEAL}
            alt="한양대학교 ERICA"
            className="w-[112px] h-[112px] object-contain"
          />

          {/* Title block */}
          <div className="flex flex-col items-center gap-1 text-center">
            <h1 className="justify-center font-bold text-[32px] text-black leading-normal">학생 관리 시스템</h1>
            <p className="justify-center text-[18px] text-black/50 leading-normal">HANYANG UNIVERSITY ERICA</p>
          </div>

          {/* Form */}
          <div className="flex flex-col gap-5 w-full">
            {/* Password field */}
            <div className="flex flex-col gap-3.5">
              <label className="text-[20px] text-[#1a1a1a]">비밀번호</label>
              <div className={`flex items-center justify-between h-[60px] px-5 rounded-lg border bg-white ${error ? 'border-red-400' : 'border-black/10'}`}>
                <div className="flex items-center gap-5 flex-1 min-w-0">
                  {/* Lock icon */}
                  <svg className="shrink-0" width="18" height="20" viewBox="0 0 18 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 9V6C14 3.79086 11.7614 2 9 2C6.23858 2 4 3.79086 4 6V9M2 9H16C16.5523 9 17 9.44772 17 10V18C17 18.5523 16.5523 19 16 19H2C1.44772 19 1 18.5523 1 18V10C1 9.44772 1.44772 9 2 9Z" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setError(false); }}
                    onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                    placeholder="비밀번호를 입력하세요"
                    className="flex-1 min-w-0 text-[20px] text-[#1a1a1a] placeholder-[#e5e7eb] outline-none bg-transparent"
                  />
                </div>
                {/* Eye toggle */}
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
                  <p className="text-red-500 text-sm">비밀번호가 올바르지 않습니다.</p>
                </div>
              )}
            </div>

            {/* Submit button */}
            <button
              onClick={handleSubmit}
              className="h-[60px] w-full rounded-lg text-white text-[20px] font-semibold cursor-pointer shadow-[0px_0px_12.3px_0px_rgba(12,66,120,0.5)] transition-opacity hover:opacity-90"
              style={{ background: 'linear-gradient(90deg, #0E4A84 0%, #0A3A6B 100%)' }}
            >
              접속하기
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="h-[60px] flex items-center justify-center shrink-0">
        <p className="text-white/50 text-[16px]">©2026 한양대학교 ERICA 학생 관리 시스템. All rights reserved.</p>
      </footer>
    </div>
  );
}
