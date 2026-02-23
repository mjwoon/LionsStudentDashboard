import { useEffect, useState } from 'react';

interface SessionWarningModalProps {
  expiresAt: number;
  onExtend: () => void;
  onLogout: () => void;
}

export default function SessionWarningModal({ expiresAt, onExtend, onLogout }: SessionWarningModalProps) {
  const [remaining, setRemaining] = useState(() => Math.max(0, expiresAt - Date.now()));

  useEffect(() => {
    const tick = () => setRemaining(Math.max(0, expiresAt - Date.now()));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [expiresAt]);

  const minutes = Math.floor(remaining / 60_000);
  const seconds = Math.floor((remaining % 60_000) / 1000);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

      {/* Modal card */}
      <div className="relative bg-white rounded-2xl shadow-2xl p-8 w-full max-w-[420px] mx-4 flex flex-col items-center gap-6">
        {/* Warning icon */}
        <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center shrink-0">
          <svg width="34" height="30" viewBox="0 0 34 30" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M14.536 2C15.6906 0 18.3094 0 19.464 2L32.8564 25.5C34.011 27.5 32.7016 30 30.3923 30H3.6077C1.2984 30 -0.0110047 27.5 1.14359 25.5L14.536 2Z" fill="#FEF3C7" stroke="#F59E0B" strokeWidth="1.5" />
            <path d="M17 11V17" stroke="#F59E0B" strokeWidth="2" strokeLinecap="round" />
            <circle cx="17" cy="22.5" r="1.25" fill="#F59E0B" />
          </svg>
        </div>

        {/* Text */}
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-[22px] font-bold text-[#1a1a1a]">세션 만료 경고</h2>
          <p className="text-[15px] text-black/60 leading-relaxed">
            비활동으로 인해 잠시 후 자동 로그아웃됩니다.<br />
            계속 사용하시려면 아래 버튼을 눌러주세요.
          </p>
        </div>

        {/* Countdown */}
        <div className="flex flex-col items-center gap-1">
          <span className="text-[13px] text-black/40 font-medium tracking-wide uppercase">남은 시간</span>
          <span
            className={`text-[48px] font-bold leading-none tabular-nums transition-colors ${remaining <= 60_000 ? 'text-red-500' : 'text-[#0e4a84]'}`}
          >
            {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
          </span>
        </div>

        {/* Buttons */}
        <div className="flex flex-col gap-3 w-full">
          <button
            onClick={onExtend}
            className="h-[52px] w-full rounded-lg text-white text-[17px] font-semibold cursor-pointer shadow-[0px_0px_12px_0px_rgba(12,66,120,0.4)] hover:opacity-90 transition-opacity"
            style={{ background: 'linear-gradient(90deg, #0E4A84 0%, #0A3A6B 100%)' }}
          >
            계속 사용하기
          </button>
          <button
            onClick={onLogout}
            className="h-[52px] w-full rounded-lg text-[#6b7280] text-[17px] font-medium cursor-pointer border border-black/10 hover:bg-gray-50 transition-colors"
          >
            로그아웃
          </button>
        </div>
      </div>
    </div>
  );
}
