import { describe, it, expect, vi } from 'vitest';
import { api } from '../src/api';

// fetch 모킹 설정
global.fetch = vi.fn();

describe('API Utils Test', () => {
  it('getStudentEvaluation 평가 결과 API 호출 형식 테스트', async () => {
    // 임시 테스트 코드. 실제 api 내부 로직을 테스트합니다.
    const mockResponse = {
      overall_score: 95.5,
      grade: "A"
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await api.evaluation.getStudentEvaluation(20260001, '1');
    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/evaluation/student/20260001/department/1'),
      expect.any(Object)
    );
  });
});
