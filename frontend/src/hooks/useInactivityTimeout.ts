import { useEffect, useRef, useCallback } from 'react';

const TIMEOUT_MS = 60 * 60 * 1000;       // 1시간
const WARNING_BEFORE_MS = 5 * 60 * 1000; // 5분 전 경고
const THROTTLE_MS = 30 * 1000;           // 이벤트 처리 스로틀 (30초)

const STORAGE_KEY = 'sessionExpiresAt';

interface Options {
  enabled: boolean;
  onTimeout: () => void;
  onShowWarning: (expiresAt: number) => void;
  onHideWarning: () => void;
}

export function useInactivityTimeout({ enabled, onTimeout, onShowWarning, onHideWarning }: Options) {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const warningRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastResetRef = useRef<number>(0);
  const isWarningActiveRef = useRef(false);

  // 콜백을 ref로 관리해서 stale closure 방지
  const onTimeoutRef = useRef(onTimeout);
  const onShowWarningRef = useRef(onShowWarning);
  const onHideWarningRef = useRef(onHideWarning);
  useEffect(() => { onTimeoutRef.current = onTimeout; }, [onTimeout]);
  useEffect(() => { onShowWarningRef.current = onShowWarning; }, [onShowWarning]);
  useEffect(() => { onHideWarningRef.current = onHideWarning; }, [onHideWarning]);

  const clearTimers = useCallback(() => {
    if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
    if (warningRef.current) { clearTimeout(warningRef.current); warningRef.current = null; }
  }, []);

  const startTimers = useCallback((remaining: number) => {
    clearTimers();
    isWarningActiveRef.current = false;
    const expiresAt = Date.now() + remaining;
    localStorage.setItem(STORAGE_KEY, expiresAt.toString());

    const warningIn = remaining - WARNING_BEFORE_MS;
    if (warningIn > 0) {
      warningRef.current = setTimeout(() => {
        isWarningActiveRef.current = true;
        onShowWarningRef.current(expiresAt);
      }, warningIn);
    } else {
      // 이미 경고 구간 진입
      isWarningActiveRef.current = true;
      onShowWarningRef.current(expiresAt);
    }

    timeoutRef.current = setTimeout(() => {
      localStorage.removeItem(STORAGE_KEY);
      onTimeoutRef.current();
    }, remaining);
  }, [clearTimers]);

  /** "계속 사용하기" 버튼에서 직접 호출 — 스로틀 우회 */
  const extendSession = useCallback(() => {
    lastResetRef.current = Date.now();
    onHideWarningRef.current();
    startTimers(TIMEOUT_MS);
  }, [startTimers]);

  /** DOM 이벤트에서 호출 — 경고 중이거나 스로틀 구간이면 무시 */
  const handleActivity = useCallback(() => {
    if (isWarningActiveRef.current) return; // 경고 모달 중엔 활동 무시
    const now = Date.now();
    if (now - lastResetRef.current < THROTTLE_MS) return;
    lastResetRef.current = now;
    onHideWarningRef.current();
    startTimers(TIMEOUT_MS);
  }, [startTimers]);

  useEffect(() => {
    if (!enabled) {
      clearTimers();
      localStorage.removeItem(STORAGE_KEY);
      return;
    }

    // 페이지 새로고침 시 저장된 만료 시간 복원
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const remaining = parseInt(stored, 10) - Date.now();
      if (remaining <= 0) {
        localStorage.removeItem(STORAGE_KEY);
        onTimeoutRef.current();
        return;
      }
      lastResetRef.current = Date.now();
      startTimers(remaining);
    } else {
      lastResetRef.current = Date.now();
      startTimers(TIMEOUT_MS);
    }

    const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
    events.forEach(e => window.addEventListener(e, handleActivity, { passive: true }));

    return () => {
      clearTimers();
      events.forEach(e => window.removeEventListener(e, handleActivity));
    };
  }, [enabled, startTimers, handleActivity, clearTimers]);

  return { extendSession };
}
