import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api } from '../src/api';

/**
 * fetchAPI에는 타임아웃이 없었다. AbortController도 signal도 없어서 백엔드가
 * 느리거나 멈추면 화면이 무기한 대기했다.
 *
 * 상대 등급 도입으로 단일 학과 조회 한 번이 평가 대상 학과 전체(38개)를 훑게 되면서
 * 이 경로가 눈에 띄게 무거워졌다. 로컬 Postgres 실측은 캐시가 빈 첫 조회 0.79초지만,
 * 운영은 원격 DB에 Render 무료 플랜이라 훨씬 느릴 수 있다. 멈춘 요청이 영원히
 * 스피너로 남는 상태만은 막아야 한다.
 */
describe('fetchAPI 타임아웃', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('요청에 AbortSignal을 실어 보낸다', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });

    await api.evaluation.getStudentEvaluation(20260001, '303');

    const [, init] = (global.fetch as any).mock.calls[0];
    expect(init.signal).toBeInstanceOf(AbortSignal);
  });

  it('응답이 오지 않으면 중단하고 사람이 읽을 수 있는 오류를 던진다', async () => {
    // 영원히 멈춰 있는 요청: abort 신호가 와야만 reject 된다.
    global.fetch = vi.fn().mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => {
            const err = new Error('aborted');
            err.name = 'AbortError';
            reject(err);
          });
        })
    );

    const pending = api.evaluation.getStudentEvaluation(20260001, '303');
    const assertion = expect(pending).rejects.toThrow(/시간|응답|초과/);

    await vi.advanceTimersByTimeAsync(120_000);
    await assertion;
  });

  it('제때 응답하면 타임아웃이 걸리지 않는다', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: 1 }) });

    await expect(
      api.evaluation.getStudentEvaluation(20260001, '303')
    ).resolves.toEqual({ ok: 1 });
  });
});
