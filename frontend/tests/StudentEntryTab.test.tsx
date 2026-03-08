import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import StudentEntryTab from '../src/components/student/StudentEntryTab';
import { BrowserRouter } from 'react-router-dom';
import { api } from '../src/api';

// api 모듈 전체를 모킹합니다.
vi.mock('../src/api', () => ({
  api: {
    departments: {
      list: vi.fn(),
    },
    evaluation: {
      getStudentEvaluation: vi.fn(),
    },
    courses: {
      fullCurriculum: vi.fn(),
    }
  }
}));

// 컴포넌트에 넘겨줄 가짜 데이터
const mockStudent = {
  student_id: 20260001,
  name: '홍길동',
  department_id: 101,
  email: 'hong@example.com',
  phone: '010-0000-0000'
};

const mockDepartmentsResponse = {
  departments: [
    { id: 101, code: 'CSE', name: '컴퓨터학부', college_id: 1, min_credits: 130 }
  ]
};

describe('StudentEntryTab Component Test', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.departments.list as any).mockResolvedValue(mockDepartmentsResponse);
    (api.courses.fullCurriculum as any).mockResolvedValue({});
  });

  it('Should render the AI status banner with "우수" colors', async () => {
    // '우수' 상태에 해당하는 evaluationResult 모의 데이터
    const mockEvalResult = {
      overall_score: 95,
      grade: 'A',
      entry_requirement_score: 100,
      recommended_exact_rate: 100,
      curriculum_exact_rate: 100,
      ai_summary: '우수 : 훌륭한 성적을 유지 중입니다.',
      detailed_results: []
    };

    // getStudentEvaluation이 호출되면 모의 데이터를 반환하도록 설정
    (api.evaluation.getStudentEvaluation as any).mockResolvedValue(mockEvalResult);

    render(
      <BrowserRouter>
        <StudentEntryTab 
          student={mockStudent as any} 
          selectedDepartmentId="101"
        />
      </BrowserRouter>
    );

    // AI Banner 텍스트가 나타날 때까지 대기
    await waitFor(() => {
      expect(screen.getByText('AI 튜터 종합 평가')).toBeInTheDocument();
    });
    
    // '[우수]' 라는 텍스트가 렌더링되었는지 확인
    expect(screen.getByText(/우수/i)).toBeInTheDocument();

    // '우수' 상태일 때 렌더링되어야 하는 Tailwind 클래스 (text-blue-800)
    // 뱃지 자체에 있는 텍스트를 찾았으므로 클래스가 맞는지 체크
    const badgeElement = screen.getByText('우수');
    expect(badgeElement).toHaveClass('text-blue-800');
    expect(badgeElement).toHaveClass('bg-blue-100');
  });

  it('Should render the AI status banner with "주의" colors', async () => {
    const mockEvalResult = {
      overall_score: 65,
      grade: 'D',
      entry_requirement_score: 50,
      recommended_exact_rate: 20,
      curriculum_exact_rate: 30,
      ai_summary: '주의 : 필수 과목 이수를 신경써주세요.',
      detailed_results: []
    };

    (api.evaluation.getStudentEvaluation as any).mockResolvedValue(mockEvalResult);

    render(
      <BrowserRouter>
        <StudentEntryTab 
          student={mockStudent as any} 
          selectedDepartmentId="101"
        />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('AI 튜터 종합 평가')).toBeInTheDocument();
    });

    const badgeElement = screen.getByText('주의');
    expect(badgeElement).toHaveClass('text-amber-800');
    expect(badgeElement).toHaveClass('bg-amber-100');
  });
});
