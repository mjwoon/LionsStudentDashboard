import { useState, useEffect } from 'react';
import { Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../api';

interface Student {
  student_id: string;
  name: string;
  email: string;
  phone?: string;
  department: {
    id: number;
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

export default function StudentDetailView() {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [perPage] = useState<number>(30);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [showDetail, setShowDetail] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'survey' | 'entry' | 'courses'>('survey');

  // Filter states
  const [trackFilter, setTrackFilter] = useState<string>('전체');
  const [prideFilter, setPrideFilter] = useState<string>('전체');
  const [classFilter, setClassFilter] = useState<string>('전체');

  // Entry tab data
  const [evaluationData, setEvaluationData] = useState<any>(null);
  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<number | null>(null);
  const [departments, setDepartments] = useState<any[]>([]);
  const [selectedCollege, setSelectedCollege] = useState<string>('');

  // 평가 가능한 학과 ID 목록
  const EVALUATION_AVAILABLE_DEPARTMENTS = [304, 303, 207, 204, 600]; // 디자인컨버전스, 데이터사이언스, 산업경영공학, 전자공학부, 광고홍보학과
  const isEvaluationAvailable = selectedDepartmentId && EVALUATION_AVAILABLE_DEPARTMENTS.includes(selectedDepartmentId);

  // Fetch students list
  useEffect(() => {
    const fetchStudents = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.students.list(currentPage, perPage, {
          search: searchQuery || undefined
        });
        setStudents(response.students);
        setTotalCount(response.count);
      } catch (error) {
        console.error('Failed to fetch students:', error);
        setError(error instanceof Error ? error.message : '학생 목록을 불러오는데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    };
    fetchStudents();
  }, [searchQuery, currentPage, perPage]);

  // Fetch departments list
  useEffect(() => {
    const fetchDepartments = async () => {
      try {
        const response = await api.departments.list();
        setDepartments(response.departments);
      } catch (error) {
        console.error('Failed to fetch departments:', error);
      }
    };
    fetchDepartments();
  }, []);

  // Fetch evaluation data when entry tab is activated
  useEffect(() => {
    // 평가 가능한 학과만 API 호출
    const isEvalAvailable = selectedDepartmentId && EVALUATION_AVAILABLE_DEPARTMENTS.includes(selectedDepartmentId);

    if (activeTab === 'entry' && selectedStudent && selectedDepartmentId && isEvalAvailable) {
      const fetchEvaluation = async () => {
        try {
          setEvaluationLoading(true);
          const data = await api.evaluation.getStudentEvaluation(
            selectedStudent.student_id,
            selectedDepartmentId
          );
          setEvaluationData(data);
        } catch (error) {
          console.error('Failed to fetch evaluation:', error);
          setEvaluationData(null);
        } finally {
          setEvaluationLoading(false);
        }
      };
      fetchEvaluation();
    } else if (activeTab === 'entry' && selectedDepartmentId && !isEvalAvailable) {
      // 평가 불가능한 학과는 데이터 초기화
      setEvaluationData(null);
      setEvaluationLoading(false);
    }
  }, [activeTab, selectedStudent, selectedDepartmentId]);

  const handleSearch = () => {
    setSearchQuery(searchInput);
    setCurrentPage(1);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const downloadCSV = () => {
    const headers = ['이름', '학번', '계열', 'Pride', '분반', '최신 희망 학과', '전공결정도', '이수현황', '수강과목 적합성'];
    const rows = students.map(s => [
      s.name,
      s.student_id,
      s.academic_info.track || '-',
      s.academic_info.pride,
      s.academic_info.class_number,
      s.latest_major_choice || '-',
      getDecisionCertaintyLabel(s.decision_certainty) || '-',
      s.completion_status || '-',
      s.course_suitability || '-'
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `students_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getDecisionCertaintyLabel = (certainty?: number): string | null => {
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

  const getDecisionCertaintyColor = (certainty?: number): string => {
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

  const getCourseProgressColor = (percentage?: string | number): string => {
    if (!percentage) return 'bg-gray-400';
    const num = typeof percentage === 'string' ? parseInt(percentage) : percentage;
    if (num >= 80) return 'bg-green-400';
    if (num >= 60) return 'bg-blue-400';
    if (num >= 40) return 'bg-yellow-400';
    return 'bg-red-400';
  };

  const totalPages = Math.ceil(totalCount / perPage);

  // 필터 옵션 추출
  const trackOptions = ['전체', ...Array.from(new Set(students.map(s => s.academic_info.track).filter(Boolean)))];
  const prideOptions = ['전체', ...Array.from(new Set(students.map(s => s.academic_info.pride).filter(Boolean))).sort((a, b) => {
    const order = ['L', 'I', 'O', 'N', 'S', 'E'];
    return order.indexOf(a) - order.indexOf(b);
  })];
  const classOptions = ['전체', ...Array.from(new Set(students.map(s => s.academic_info.class_number).filter(Boolean))).sort((a, b) => a - b)];

  // 필터링된 학생 목록
  const filteredStudents = students.filter(student => {
    const trackMatch = trackFilter === '전체' || student.academic_info.track === trackFilter;
    const prideMatch = prideFilter === '전체' || student.academic_info.pride === prideFilter;
    const classMatch = classFilter === '전체' || student.academic_info.class_number.toString() === classFilter;
    return trackMatch && prideMatch && classMatch;
  });

  // 학생 상세 정보 페이지 렌더링
  if (showDetail && selectedStudent) {
    return (
      <div className="bg-[#f5f7fa] min-h-screen py-8">
        <div className="max-w-[1920px] mx-auto px-8">
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-[32pt] font-bold text-[#101828] mb-4">{selectedStudent.name}</h1>
            </div>
            <button
              onClick={() => setShowDetail(false)}
              className="flex items-center gap-3 px-4 py-2 bg-white border border-black/10 rounded-lg hover:bg-gray-50"
            >
              <ChevronLeft className="w-5 h-5 text-[#101828]" />
              <span className="text-lg font-medium text-[#101828]">목록으로 돌아가기</span>
            </button>
          </div>

          {/* 학생 학적 정보 */}
          <div className="mb-6">
            <p className="text-xl text-[#6a7282] font-medium">
              {selectedStudent.student_id} ⋅ {selectedStudent.academic_info.class_number}반 ⋅ {selectedStudent.department.name}
            </p>
            <p className="text-lg text-[#BBBFC8]">
              학생의 학적 및 전공 선택 정보를 확인합니다.
            </p>
          </div>

          {/* 탭 네비게이션 */}
          <div className="flex items-start gap-0 mb-6 border-b border-[#e5e7eb]">
            <button
              onClick={() => setActiveTab('survey')}
              className={`px-6 py-6 text-xl font-semibold transition-all ${activeTab === 'survey'
                ? 'text-[#0e4a84] border-b-2 border-[#0e4a84]'
                : 'text-[#6a7282]'
                }`}
            >
              희망 전공 조사 결과
            </button>
            <button
              onClick={() => setActiveTab('entry')}
              className={`px-6 py-6 text-xl font-semibold transition-all ${activeTab === 'entry'
                ? 'text-[#0e4a84] border-b-2 border-[#0e4a84]'
                : 'text-[#6a7282]'
                }`}
            >
              희망 전공 진입
            </button>
            <button
              onClick={() => setActiveTab('courses')}
              className={`px-6 py-6 text-xl font-semibold transition-all ${activeTab === 'courses'
                ? 'text-[#0e4a84] border-b-2 border-[#0e4a84]'
                : 'text-[#6a7282]'
                }`}
            >
              수강 과목 리스트
            </button>
          </div>

          {/* 탭 컨텐츠 */}
          {activeTab === 'survey' && (
            <div className="space-y-6">
              {/* 3차 조사 */}
              <div className="bg-white border border-black/10 rounded-2xl p-9">
                <div className="mb-8">
                  <h3 className="text-3xl font-bold text-[#0e4a84] mb-2">3차 조사 완료</h3>
                  <p className="text-xl text-[#6a7282]">조사 시점: 2024년 2학년 1학기</p>
                </div>

                <div className="flex gap-8 items-center">
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">1지망</p>
                    <p className="text-[22pt] font-bold text-[#101828]">
                      {selectedStudent.latest_major_choice || '-'}
                    </p>
                  </div>
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">2지망</p>
                    <p className="text-[22pt] font-bold text-[#101828]">미정</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">전공 결정도</p>
                    {selectedStudent.decision_certainty && selectedStudent.decision_certainty >= 4 ? (
                      <div className="inline-block px-6 py-3 bg-blue-100 text-blue-800 rounded-full text-2xl font-bold">
                        {getDecisionCertaintyLabel(selectedStudent.decision_certainty)}
                      </div>
                    ) : (
                      <div className="inline-block px-6 py-3 bg-gray-100 text-gray-800 rounded-full text-2xl font-bold">
                        미정
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* 2차 조사 */}
              <div className="bg-white border border-black/10 rounded-2xl p-9">
                <div className="mb-8">
                  <h3 className="text-[22pt] font-bold text-[#0e4a84] mb-2">2차 조사 완료</h3>
                  <p className="text-xl text-[#6a7282]">조사 시점: 2023년 1학년 2학기</p>
                </div>

                <div className="flex gap-8 items-center">
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">1지망</p>
                    <p className="text-[22pt] font-bold text-[#101828]">-</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">2지망</p>
                    <p className="text-3xl font-bold text-[#101828]">미정</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">전공 결정도</p>
                    <div className="inline-block px-6 py-3 bg-yellow-100 text-yellow-800 rounded-full text-2xl font-bold">
                      구체 중
                    </div>
                  </div>
                </div>
              </div>

              {/* 1차 조사 */}
              <div className="bg-white border border-black/10 rounded-2xl p-9">
                <div className="mb-8">
                  <h3 className="text-[22pt] font-bold text-[#0e4a84] mb-2">1차 조사 완료</h3>
                  <p className="text-xl text-[#6a7282]">조사 시점: 2023년 1학년 1학기</p>
                </div>

                <div className="flex gap-8 items-center">
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">1지망</p>
                    <p className="text-[22pt] font-bold text-[#101828]">미정</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">2지망</p>
                    <p className="text-[22pt] font-bold text-[#101828]">미정</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">전공 결정도</p>
                    <div className="inline-block px-6 py-3 bg-gray-100 text-gray-700 rounded-full text-[22pt] font-bold">
                      미정
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'entry' && (
            <div className="space-y-6">
              {/* 분석할 학과 선택 섹션 */}
              <div className="bg-white border border-black/10 rounded-2xl p-9">
                <h3 className="text-[20pt] font-bold text-[#101828] mb-8">분석할 학과 선택</h3>
                <div className="flex gap-8">
                  <div className="flex-1">
                    <label className="block text-[14pt] text-[#6a7282] font-medium mb-3">단과대학</label>
                    <select
                      className="w-full px-5 py-3 border border-black/10 rounded-lg text-xl text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
                      value={selectedCollege}
                      onChange={(e) => {
                        setSelectedCollege(e.target.value);
                        // 단과대학 변경 시 해당 단과대학의 첫 번째 학과로 자동 선택
                        const filteredDepts = departments.filter(d => !e.target.value || d.college_name === e.target.value);
                        if (filteredDepts.length > 0) {
                          setSelectedDepartmentId(filteredDepts[0].id);
                        }
                      }}
                    >
                      <option value="">전체</option>
                      {Array.from(new Set(departments.map(d => d.college_name)))
                        .filter(college => college && !college.includes('라이언스') && !college.toLowerCase().includes('lions'))
                        .map(college => (
                          <option key={college} value={college}>{college}</option>
                        ))}
                    </select>
                  </div>
                  <div className="flex-1">
                    <label className="block text-[14pt] text-[#6a7282] font-medium mb-3">학과</label>
                    <select
                      className="w-full px-5 py-3 border border-black/10 rounded-lg text-xl text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
                      value={selectedDepartmentId || ''}
                      onChange={(e) => setSelectedDepartmentId(Number(e.target.value))}
                    >
                      <option value="">학과를 선택하세요</option>
                      {departments
                        .filter(d => !selectedCollege || d.college_name === selectedCollege)
                        .map(dept => (
                          <option key={dept.id} value={dept.id}>{dept.name}</option>
                        ))}
                    </select>
                  </div>
                </div>
              </div>

              {!isEvaluationAvailable ? (
                <div className="bg-white border border-black/10 rounded-2xl p-9 text-center">
                  <p className="text-xl text-[#6a7282]">
                    선택한 학과는 현재 평가가 지원되지 않습니다.
                  </p>
                  <p className="text-lg text-[#6a7282] mt-2">
                    평가 가능 학과: 디자인컨버전스전공, 데이터사이언스학과, 산업경영공학과, 전자공학부, 광고홍보학과
                  </p>
                </div>
              ) : evaluationLoading ? (
                <div className="bg-white border border-black/10 rounded-2xl p-9 text-center">
                  <p className="text-xl text-[#6a7282]">평가 데이터를 불러오는 중...</p>
                </div>
              ) : !evaluationData ? (
                <div className="bg-white border border-black/10 rounded-2xl p-9 text-center">
                  <p className="text-xl text-[#6a7282]">평가 데이터가 없습니다.</p>
                </div>
              ) : (
                <>
                  {/* 안내 배너 */}
                  <div className={`rounded-2xl p-6 mb-6 ${evaluationData.overall_score >= 80
                    ? 'bg-gradient-to-r from-blue-500 to-blue-600'
                    : evaluationData.overall_score >= 60
                      ? 'bg-gradient-to-r from-green-500 to-green-600'
                      : 'bg-gradient-to-r from-yellow-500 to-yellow-600'
                    }`}>
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                        <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <p className="text-xl font-semibold text-white">
                        {evaluationData.summary_message ||
                          (evaluationData.overall_score >= 80 ? '우수: 전공진입 준비가 잘 되어 있습니다!' :
                            evaluationData.overall_score >= 60 ? '양호: 전공진입 필수 과목을 이수하고 있습니다.' :
                              '주의: 추가 노력이 필요합니다. 필수 과목 이수를 권장합니다.')}
                      </p>
                    </div>
                  </div>

                  {/* 주의사항 배너 */}
                  <div className="bg-[#FEF9C3] rounded-[14px] px-9 py-5 mb-6">
                    <div className="flex items-center gap-2.5">
                      <svg className="w-6 h-6 flex-shrink-0" fill="none" stroke="#95430E" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.33} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <p className="text-xl text-[#95430E] font-semibold leading-6">
                        과목 구분은 현재 소속인 라이언스 칼리지 기준으로 구분된 정보이며, 향후 전공 진입에 따라 바뀔 수 있음을 유의하십시오.
                      </p>
                    </div>
                  </div>

                  {/* 전공이수체계도 - 학년별 테이블 */}
                  {evaluationData.curriculum_details && Object.keys(evaluationData.curriculum_details).length > 0 && (
                    <div className="space-y-6">
                      {Object.entries(evaluationData.curriculum_details as Record<string, any[]>).map(([year, courses]) => (
                        <div key={year} className="bg-white border border-black/10 rounded-[14px] overflow-hidden">
                          {/* 학년 헤더 */}
                          <div className="bg-white px-7 py-6">
                            <h3 className="text-2xl font-semibold leading-7 text-[#101828] mb-1.5">{year}학년 교육과정</h3>
                          </div>

                          {/* 테이블 */}
                          <div className="overflow-x-auto">
                            <table className="w-full">
                              <thead>
                                <tr className="bg-[#F9FAFB] border-t border-b border-[#E5E7EB]">
                                  <th className="px-7 py-0 h-12 text-left text-lg font-bold leading-5 text-[#6A7282] w-[160px]">학기</th>
                                  <th className="px-7 py-0 h-12 text-left text-lg font-bold leading-5 text-[#6A7282] w-[320px]">과목명</th>
                                  <th className="px-7 py-0 h-12 text-left text-lg font-bold leading-5 text-[#6A7282] w-[160px]">구분</th>
                                  <th className="px-7 py-0 h-12 text-left text-lg font-bold leading-5 text-[#6A7282] w-[120px]">학점</th>
                                  <th className="px-7 py-0 h-12 text-left text-lg font-bold leading-5 text-[#6A7282] w-[200px]">이수현황</th>
                                  <th className="px-7 py-0 h-12 text-left text-lg font-bold leading-5 text-[#6A7282] w-[200px]">비고</th>
                                </tr>
                              </thead>
                              <tbody>
                                {courses.map((course: any, idx: number) => (
                                  <tr key={idx} className={`h-16 ${idx % 2 === 0 ? '' : 'bg-white'}`}>
                                    <td className="px-7 py-0 text-lg font-normal leading-5 text-[#6A7282]">
                                      {course.semester === 1 ? '1학기' : '2학기'}
                                    </td>
                                    <td className="px-7 py-0">
                                      <p className="text-lg font-medium leading-5 text-[#101828]">{course.course_name}</p>
                                    </td>
                                    <td className="px-7 py-0">
                                      <span className={`inline-flex items-center justify-center px-5 py-2 rounded-full text-lg font-medium leading-5 ${(course.requirement_type || course.evaluation_type || course.course_type) === '전공진입' || (course.requirement_type || course.evaluation_type || course.course_type) === '필수'
                                        ? 'bg-[#DBEAFE] text-[#1E40AF]'
                                        : (course.requirement_type || course.evaluation_type || course.course_type) === '권장과목' ||
                                          (course.requirement_type || course.evaluation_type || course.course_type) === '필수과목'
                                          ? 'bg-[#FEF9C3] text-[#8D601F]'
                                          : '-'
                                        }`}>
                                        {course.requirement_type || course.evaluation_type}
                                      </span>
                                    </td>
                                    <td className="px-7 py-0 text-lg font-normal leading-5 text-[#6A7282]">
                                      {course.credits}
                                    </td>
                                    <td className="px-7 py-0">
                                      <div className="flex items-center gap-2">
                                        {course.enrolled && course.grade ? (
                                          <>
                                            <svg className="w-5 h-5" fill="none" stroke="#26BD89" viewBox="0 0 24 24">
                                              <circle cx="12" cy="12" r="10" strokeWidth={2.33} />
                                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.33} d="M9 12l2 2 4-4" />
                                            </svg>
                                            <span className="text-lg font-normal leading-5 text-[#26BD89]">수강완료</span>
                                          </>
                                        ) : (
                                          <>
                                            <svg className="w-5 h-5" fill="none" stroke="#F04462" viewBox="0 0 24 24">
                                              <circle cx="12" cy="12" r="10" strokeWidth={2.33} />
                                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.33} d="M15 9l-6 6m0-6l6 6" />
                                            </svg>
                                            <span className="text-lg font-normal leading-5 text-[#F04462]">미이수</span>
                                          </>
                                        )}
                                      </div>
                                    </td>
                                    <td className="px-7 py-0 text-lg font-normal leading-5 text-[#6A7282]">
                                      {course.enrolled && course.grade ? '!' : '-'}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              {/* 캐시 정보 */}
              {evaluationData && evaluationData.cached && evaluationData.evaluated_at && isEvaluationAvailable && (
                <div className="bg-gray-50 border-l-4 border-gray-400 rounded-lg p-6 mt-6">
                  <div className="flex items-start gap-3">
                    <svg className="w-6 h-6 text-gray-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-base text-gray-700">
                      캐시된 평가 결과 (평가 시점: {new Date(evaluationData.evaluated_at).toLocaleString('ko-KR')})
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'courses' && (
            <div className="space-y-6">
              {/* 학적 통계 카드들 */}
              <div className="grid grid-cols-3 gap-6">
                <div className="bg-white border border-black/10 rounded-2xl p-9">
                  <p className="text-xl text-[#6a7282] font-medium mb-3">총 취득학점</p>
                  <p className="text-[22pt] font-bold text-[#101828]">32학점</p>
                </div>
                <div className="bg-white border border-black/10 rounded-2xl p-9">
                  <p className="text-xl text-[#6a7282] font-medium mb-3">평균 학점</p>
                  <p className="text-[22pt] font-bold text-[#101828] mb-2">2.09 / 4.5</p>
                  <p className="text-xl text-[#6a7282]">총 13과목 이수</p>
                </div>
                <div className="bg-white border border-black/10 rounded-2xl p-9">
                  <p className="text-xl text-[#6a7282] font-medium mb-3">희망 전공</p>
                  <p className="text-[22pt] font-bold text-[#101828]">{selectedStudent.latest_major_choice || '-'}</p>
                </div>
              </div>

              {/* 수강 과목 목록 테이블 */}
              <div className="bg-white border border-black/10 rounded-2xl overflow-hidden">
                <div className="p-9 border-b border-black/10 flex items-center justify-between">
                  <div>
                    <h4 className="text-[22pt] font-bold text-[#101828] mb-2">수강 과목 목록</h4>
                    <p className="text-xl text-[#6a7282]">전체 과목 13개</p>
                  </div>
                  <div className="bg-white border border-black/10 rounded-lg px-4 py-3 flex items-center gap-3">
                    <span className="text-lg text-[#101828] font-medium">이수구분: 전체</span>
                    <svg className="w-4 h-4 text-[#101828]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-[#f9fafb] border-b border-[#e5e7eb] border-t">
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">년도</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">학기</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">과목코드</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">과목명</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">학점</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">성적</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">이수구분</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'A0', category: '전공필수' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'B+', category: '전공선택' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'C0', category: '교양필수' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'D+', category: '기초교양' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'P', category: '전공필수' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'F', category: '전공필수' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'A0', category: '전공필수' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'B+', category: '전공선택' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'C0', category: '교양필수' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'D+', category: '기초교양' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'P', category: '전공필수' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'F', category: '전공필수' },
                        { year: '2026', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: '3', grade: 'A0', category: '전공필수' }
                      ].map((course, idx) => (
                        <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-[#fafbfc]'}>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.year}</td>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.semester}</td>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.code}</td>
                          <td className="px-9 py-5 text-lg font-medium text-[#101828]">{course.name}</td>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.credits}</td>
                          <td className="px-9 py-5 text-lg">
                            <div className="border-[1.4px] rounded-lg px-3 py-2 inline-flex items-center justify-center w-16"
                              style={{
                                borderColor: course.grade === 'A0' ? '#3b82f6' :
                                  course.grade === 'B+' ? '#10b981' :
                                    course.grade === 'C0' ? '#f59e0b' :
                                      course.grade === 'D+' ? '#f97316' :
                                        course.grade === 'P' ? '#6b7280' :
                                          '#ef4444',
                                color: course.grade === 'A0' ? '#3b82f6' :
                                  course.grade === 'B+' ? '#10b981' :
                                    course.grade === 'C0' ? '#f59e0b' :
                                      course.grade === 'D+' ? '#f97316' :
                                        course.grade === 'P' ? '#6b7280' :
                                          '#ef4444'
                              }}>
                              <span className="text-lg font-semibold">{course.grade}</span>
                            </div>
                          </td>
                          <td className="px-9 py-5 text-lg">
                            <div className="px-6 py-2 rounded-full inline-flex items-center justify-center"
                              style={{
                                backgroundColor: course.category === '전공필수' ? '#dbeafe' :
                                  course.category === '전공선택' ? '#dcfce7' :
                                    course.category === '교양필수' ? '#ffedd4' :
                                      '#f3e8ff'
                              }}>
                              <span className="text-lg font-bold" style={{
                                color: course.category === '전공필수' ? '#1e40af' :
                                  course.category === '전공선택' ? '#016630' :
                                    course.category === '교양필수' ? '#9f2d00' :
                                      '#6e11b0'
                              }}>
                                {course.category}
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#f5f7fa] min-h-screen py-8">
      <div className="max-w-[1920px] mx-auto px-8">
        {/* Header Section */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-4xl font-bold text-[#101828] mb-4">학생 관리</h1>
            <p className="text-xl text-[#6a7282]">학생 검색 및 관리를 할 수 있습니다.</p>
          </div>
          <button
            onClick={downloadCSV}
            className="flex items-center gap-2 px-4 py-2 bg-[#0e4a84] text-white rounded-lg hover:bg-[#0a3a6b] transition"
          >
            <Download className="w-6 h-6" />
            학과별 조사시점별 데이터 다운로드
          </button>
        </div>

        {/* Student Table Card */}
        <div className="bg-white border border-black/10 rounded-2xl overflow-hidden">
          {/* Table Header with Filters */}
          <div className="bg-white p-9 border-b border-black/10">
            <div className="flex items-center justify-between">
              <h2 className="text-3xl font-bold text-[#101828]">LIONS칼리지 전체 학생 목록</h2>
              <div className="flex gap-4">
                {/* Search Input */}
                <div className="relative w-70">
                  <input
                    type="text"
                    placeholder="이름으로 검색 ..."
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="w-full px-5 py-4 border border-black/10 rounded-lg text-lg text-[#6a7282] placeholder-[#6a7282] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
                  />
                </div>

                {/* Filter Dropdowns */}
                <select
                  value={trackFilter}
                  onChange={(e) => setTrackFilter(e.target.value)}
                  className="px-5 py-4 border border-black/10 rounded-lg text-lg text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
                >
                  {trackOptions.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>

                <select
                  value={prideFilter}
                  onChange={(e) => setPrideFilter(e.target.value)}
                  className="px-5 py-4 border border-black/10 rounded-lg text-lg text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
                >
                  <option value="전체">Pride</option>
                  {prideOptions.filter(o => o !== '전체').map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>

                <select
                  value={classFilter}
                  onChange={(e) => setClassFilter(e.target.value)}
                  className="px-5 py-4 border border-black/10 rounded-lg text-lg text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
                >
                  <option value="전체">분반</option>
                  {classOptions.filter(o => o !== '전체').map(option => (
                    <option key={option} value={option.toString()}>{option}반</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Table */}
          {loading && (
            <div className="px-9 py-12 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#0e4a84]"></div>
              <p className="mt-2 text-[#6a7282]">학생 목록을 불러오는 중...</p>
            </div>
          )}

          {error && (
            <div className="px-9 py-4 bg-red-50 border-l-4 border-red-500">
              <p className="text-red-700">{error}</p>
            </div>
          )}

          {!loading && !error && students.length === 0 && (
            <div className="px-9 py-12 text-center text-[#6a7282]">
              {searchQuery ? '검색 결과가 없습니다.' : '학생이 없습니다.'}
            </div>
          )}

          {!loading && !error && students.length > 0 && filteredStudents.length === 0 && (
            <div className="px-9 py-12 text-center text-[#6a7282]">
              필터 조건에 맞는 학생이 없습니다.
            </div>
          )}

          {!loading && !error && students.length > 0 && filteredStudents.length > 0 && (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  {/* Table Header */}
                  <thead>
                    <tr className="bg-[#f9fafb] border-b border-[#e5e7eb] border-t">
                      <th className="px-9 py-4 text-left h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-36">이름</th>
                      <th className="px-9 py-4 text-left h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">학번</th>
                      <th className="px-9 py-4 text-left h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-44">계열</th>
                      <th className="px-9 py-4 text-center h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">Pride</th>
                      <th className="px-9 py-4 text-left h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">분반</th>
                      <th className="px-9 py-4 text-center h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-72 bg-[rgba(67,132,195,0.04)]">최신 희망 학과</th>
                      <th className="px-9 py-4 text-center h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-60 bg-[rgba(67,132,195,0.04)]">전공결정도</th>
                      <th className="px-9 py-4 text-center h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-56 bg-[rgba(67,132,195,0.04)]">이수현황</th>
                      <th className="px-9 py-4 text-center h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap flex-1">수강과목 적합성</th>
                    </tr>
                  </thead>
                  {/* Table Body */}
                  <tbody>
                    {students.map((student, idx) => (
                      <tr
                        key={student.student_id}
                        onClick={() => {
                          setSelectedStudent(student);
                          setSelectedDepartmentId(student.department.id);
                          setShowDetail(true);
                        }}
                        className={`${idx % 2 === 0 ? 'bg-white' : 'bg-[#fafbfc]'} cursor-pointer hover:bg-[#e8f0f7] transition-colors`}
                      >
                        <td className="px-9 py-5 text-lg font-bold text-[#0e4a84] whitespace-nowrap">
                          {student.name}
                        </td>
                        <td className="px-9 py-5 text-lg text-[#6a7282] whitespace-nowrap">
                          {student.student_id}
                        </td>
                        <td className="px-9 py-5 text-lg text-[#6a7282] whitespace-nowrap">
                          {student.academic_info.track || '-'}
                        </td>
                        <td className="px-9 py-5 text-center">
                          <div className="flex items-center justify-center">
                            <div className="border-2 border-[#0e4a84] rounded-full w-10 h-10 flex items-center justify-center">
                              <span className="text-lg font-bold text-[#0e4a84]">
                                {student.academic_info.pride}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="px-9 py-5 text-lg text-[#6a7282] whitespace-nowrap">
                          {student.academic_info.class_number}반
                        </td>
                        <td className="px-9 py-5 text-center bg-[rgba(67,132,195,0.04)]">
                          <span className="text-lg font-bold text-[#0e4a84] whitespace-nowrap">
                            {student.latest_major_choice || '-'}
                          </span>
                        </td>
                        <td className="px-9 py-5 text-center bg-[rgba(67,132,195,0.04)]">
                          {student.decision_certainty ? (
                            <span className={`px-6 py-2 rounded-full text-lg font-bold inline-block ${getDecisionCertaintyColor(student.decision_certainty)}`}>
                              {getDecisionCertaintyLabel(student.decision_certainty)}
                            </span>
                          ) : (
                            <span className="text-[#6a7282]">-</span>
                          )}
                        </td>
                        <td className="px-9 py-5 text-center bg-[rgba(67,132,195,0.04)]">
                          {student.completion_status ? (
                            <span className={`px-6 py-2 rounded-full text-lg font-bold inline-block bg-green-100 text-green-800`}>
                              {student.completion_status}
                            </span>
                          ) : (
                            <span className="text-[#6a7282]">-</span>
                          )}
                        </td>
                        <td className="px-9 py-5">
                          <div className="flex flex-col gap-2">
                            <span className="text-lg text-[#101828]">0%</span>
                            <div className="w-full h-1 bg-[#e5e7eb] rounded-full overflow-hidden">
                              <div
                                className={`h-full ${getCourseProgressColor(student.course_suitability)}`}
                                style={{ width: `${Math.random() * 100}%` }}
                              />
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="bg-[#f9fafb] border-t border-[#e5e7eb] px-9 py-6 flex items-center justify-between">
                <span className="text-lg text-[#6a7282]">총 {filteredStudents.length}명의 학생 {filteredStudents.length !== totalCount && `(전체: ${totalCount}명)`}</span>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="p-3 rounded-lg border border-black/10 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>

                  <div className="flex items-center gap-2">
                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter(page => {
                        if (totalPages <= 10) return true;
                        if (page === 1 || page === totalPages) return true;
                        if (Math.abs(page - currentPage) <= 1) return true;
                        return false;
                      })
                      .map((page, idx, arr) => (
                        <div key={page} className="flex items-center gap-2">
                          {idx > 0 && arr[idx - 1] !== page - 1 && (
                            <span className="text-[#6a7282]">...</span>
                          )}
                          <button
                            onClick={() => setCurrentPage(page)}
                            className={`w-12 h-12 rounded-lg text-lg font-bold ${currentPage === page
                              ? 'bg-[#0e4a84] text-white'
                              : 'bg-white border border-black/10 text-[#101828] hover:bg-gray-50'
                              }`}
                          >
                            {page}
                          </button>
                        </div>
                      ))}
                  </div>

                  <button
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    className="p-3 rounded-lg border border-black/10 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="text-center text-[#6c6c6c] text-base mt-8">
          <p>©2026 한양대학교 ERICA 학생 관리 시스템. All rights reserved.</p>
        </div>
      </div>
    </div>
  );
}
