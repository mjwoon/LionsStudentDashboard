// 학생 관련 공통 타입 정의

export interface Student {
  student_id: number;
  name: string;
  email: string;
  phone?: string;
  department: {
    id: string;
    name: string;
  };
  academic_info: {
    pride: string;
    class_number: number;
    track?: string;
    advisor_name?: string;
    status: string;
  };
  latest_major_choice?: string;
  decision_certainty?: number;
  completion_status?: string;
  course_suitability?: string;
}

// 유틸리티 함수들
export const getDecisionCertaintyLabel = (certainty?: number): string | null => {
  if (!certainty) return null;
  const labels: { [key: number]: string } = {
    1: '매우 불확실',
    2: '불확실',
    3: '보통',
    4: '확실',
    5: '매우 확실'
  };
  return labels[certainty] || null;
};

export const getDecisionCertaintyColor = (certainty?: number): string => {
  if (!certainty) return 'text-gray-500';
  const colors: { [key: number]: string } = {
    1: 'bg-red-100 text-red-800',
    2: 'bg-orange-100 text-orange-800',
    3: 'bg-yellow-100 text-yellow-800',
    4: 'bg-blue-100 text-blue-800',
    5: 'bg-green-100 text-green-800'
  };
  return colors[certainty] || '';
};

export const getCourseProgressColor = (percentage?: string | number): string => {
  if (!percentage) return 'bg-gray-400';
  const num = typeof percentage === 'string' ? parseInt(percentage) : percentage;
  if (num >= 80) return 'bg-blue-400';
  if (num >= 60) return 'bg-green-400';
  if (num >= 40) return 'bg-yellow-400';
  if (num >= 20) return 'bg-orange-400';
  return 'bg-red-400';
};
