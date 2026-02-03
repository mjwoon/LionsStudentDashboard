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
    const headers = ['이름', '학번', '학과계열', 'Pride', '분반', '최신 희망 학과', '전공결정도', '이수현황', '수강과목 적합성'];
    const rows = students.map(s => [
      s.name,
      s.student_id,
      s.department.name,
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

  // 학생 상세 정보 페이지 렌더링
  if (showDetail && selectedStudent) {
    return (
      <div className="bg-[#f5f7fa] min-h-screen py-8">
        <div className="max-w-7xl mx-auto px-8">
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-5xl font-bold text-[#101828] mb-4">{selectedStudent.name}</h1>
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
              {selectedStudent.student_id} ⋅ {selectedStudent.academic_info.class_number}학년 ⋅ {selectedStudent.department.name}
            </p>
            <p className="text-lg text-[#6a7282]">
              학생의 학적 및 전공 선택 정보를 확인합니다.
            </p>
          </div>

          {/* 탭 네비게이션 */}
          <div className="flex items-start gap-0 mb-6 border-b border-[#e5e7eb]">
            <button
              onClick={() => setActiveTab('survey')}
              className={`px-6 py-6 text-xl font-semibold transition-all ${
                activeTab === 'survey'
                  ? 'text-[#0e4a84] border-b-2 border-[#0e4a84]'
                  : 'text-[#6a7282]'
              }`}
            >
              희망 전공 조사 결과
            </button>
            <button
              onClick={() => setActiveTab('entry')}
              className={`px-6 py-6 text-xl font-semibold transition-all ${
                activeTab === 'entry'
                  ? 'text-[#0e4a84] border-b-2 border-[#0e4a84]'
                  : 'text-[#6a7282]'
              }`}
            >
              희망 전공 진입
            </button>
            <button
              onClick={() => setActiveTab('courses')}
              className={`px-6 py-6 text-xl font-semibold transition-all ${
                activeTab === 'courses'
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
                  <h3 className="text-4xl font-bold text-[#0e4a84] mb-2">3차 조사 완료</h3>
                  <p className="text-xl text-[#6a7282]">조사 시점: 2024년 2학년 1학기</p>
                </div>

                <div className="flex gap-8 items-center">
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">1지망</p>
                    <p className="text-3xl font-bold text-[#101828]">
                      {selectedStudent.latest_major_choice || '-'}
                    </p>
                  </div>
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">2지망</p>
                    <p className="text-3xl font-bold text-[#101828]">미정</p>
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
                  <h3 className="text-4xl font-bold text-[#0e4a84] mb-2">2차 조사 완료</h3>
                  <p className="text-xl text-[#6a7282]">조사 시점: 2023년 1학년 2학기</p>
                </div>

                <div className="flex gap-8 items-center">
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">1지망</p>
                    <p className="text-3xl font-bold text-[#101828]">-</p>
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
                  <h3 className="text-4xl font-bold text-[#0e4a84] mb-2">1차 조사 완료</h3>
                  <p className="text-xl text-[#6a7282]">조사 시점: 2023년 1학년 1학기</p>
                </div>

                <div className="flex gap-8 items-center">
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">1지망</p>
                    <p className="text-3xl font-bold text-[#101828]">미정</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">2지망</p>
                    <p className="text-3xl font-bold text-[#101828]">미정</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-2xl text-[#6a7282] font-medium mb-2">전공 결정도</p>
                    <div className="inline-block px-6 py-3 bg-gray-100 text-gray-700 rounded-full text-2xl font-bold">
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
                <h3 className="text-3xl font-bold text-[#101828] mb-8">분석할 학과 선택</h3>
                <div className="flex gap-8">
                  <div className="flex-1">
                    <label className="block text-2xl text-[#6a7282] font-medium mb-3">단과대학</label>
                    <select className="w-full px-5 py-3 border border-black/10 rounded-lg text-xl text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]">
                      <option>공과대학</option>
                    </select>
                  </div>
                  <div className="flex-1">
                    <label className="block text-2xl text-[#6a7282] font-medium mb-3">학과</label>
                    <select className="w-full px-5 py-3 border border-black/10 rounded-lg text-xl text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]">
                      <option>{selectedStudent.department.name}</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* 진입 관련 카드들 */}
              <div className="grid grid-cols-3 gap-6">
                <div className="bg-white border border-black/10 rounded-2xl p-9">
                  <p className="text-xl text-[#6a7282] font-medium mb-3">전공 진입 필수</p>
                  <p className="text-4xl font-bold text-[#101828] mb-3">100%</p>
                  <p className="text-xl text-[#6a7282] mb-6">3 / 3 과목</p>
                  <div className="w-full bg-[#e5e7eb] rounded-full h-1.5 overflow-hidden">
                    <div className="bg-blue-500 h-full w-full" />
                  </div>
                </div>

                <div className="bg-white border border-black/10 rounded-2xl p-9">
                  <p className="text-xl text-[#6a7282] font-medium mb-3">권장 과목</p>
                  <p className="text-4xl font-bold text-[#101828] mb-3">10%</p>
                  <p className="text-xl text-[#6a7282] mb-6">1 / 10 과목</p>
                  <div className="w-full bg-[#e5e7eb] rounded-full h-1.5 overflow-hidden">
                    <div className="bg-red-500 h-full w-[10%]" />
                  </div>
                </div>

                <div className="bg-white border border-black/10 rounded-2xl p-9">
                  <p className="text-xl text-[#6a7282] font-medium mb-3">전체 적합도</p>
                  <p className="text-4xl font-bold text-[#101828] mb-3">75%</p>
                  <p className="text-xl text-[#6a7282] mb-6">종합 진입 준비도</p>
                  <div className="w-full bg-[#e5e7eb] rounded-full h-1.5 overflow-hidden">
                    <div className="bg-green-500 h-full w-[75%]" />
                  </div>
                </div>
              </div>

              {/* 안내 메시지 */}
              <div className="space-y-4">
                <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-6">
                  <p className="text-xl text-blue-900 font-semibold">
                    양호: 전공진입 필수 과목을 충실히 이수하고 있습니다.
                  </p>
                </div>
                <div className="bg-yellow-50 border-l-4 border-yellow-400 rounded-lg p-6">
                  <p className="text-xl text-yellow-900 font-semibold">
                    과목 구분은 현재 소속인 라이언스 칼리지 기준으로 구분된 정보이며, 향후 전공 진입에 따라 바뀔 수 있음을 유의하십시오.
                  </p>
                </div>
              </div>

              {/* 1학년 교육과정 테이블 */}
              <div className="bg-white border border-black/10 rounded-2xl overflow-hidden">
                <div className="p-9 border-b border-black/10">
                  <h4 className="text-3xl font-bold text-[#101828] mb-2">1학년 교육과정</h4>
                  <p className="text-xl text-[#6a7282]">{selectedStudent.department.name} 1학년 과정</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-[#f9fafb] border-b border-[#e5e7eb] border-t">
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">학기</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] flex-1">과목명</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">구분</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">학점</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-48">이수현황</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">비고</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { semester: '1학기', name: '프로그래밍 기초', type: '전공진입', credits: '3', status: '유사과목 이수', remark: '동등과목 인정' },
                        { semester: '1학기', name: '미적분학1', type: '전공진입', credits: '3', status: '수강완료', remark: '-' },
                        { semester: '2학기', name: '컴퓨터구조', type: '권장과목', credits: '3', status: '미이수', remark: '-' },
                        { semester: '2학기', name: '미적분학2', type: '전공진입', credits: '3', status: '수강완료', remark: '-' }
                      ].map((course, idx) => (
                        <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-[#fafbfc]'}>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.semester}</td>
                          <td className="px-9 py-5 text-lg font-medium text-[#101828]">{course.name}</td>
                          <td className="px-9 py-5 text-lg">
                            <span className={`px-4 py-2 rounded-full text-lg font-medium inline-block ${
                              course.type === '전공진입' ? 'bg-blue-100 text-blue-800' :
                              course.type === '권장과목' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {course.type}
                            </span>
                          </td>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.credits}</td>
                          <td className="px-9 py-5 text-lg font-medium">
                            <span className={`${
                              course.status === '수강완료' ? 'text-green-600' :
                              course.status === '유사과목 이수' ? 'text-amber-600' :
                              'text-red-600'
                            }`}>
                              {course.status}
                            </span>
                          </td>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.remark}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 2학년 교육과정 테이블 */}
              <div className="bg-white border border-black/10 rounded-2xl overflow-hidden">
                <div className="p-9 border-b border-black/10">
                  <h4 className="text-3xl font-bold text-[#101828] mb-2">2학년 교육과정</h4>
                  <p className="text-xl text-[#6a7282]">{selectedStudent.department.name} 2학년 과정</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-[#f9fafb] border-b border-[#e5e7eb] border-t">
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">학기</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] flex-1">과목명</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">구분</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">학점</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-48">이수현황</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">비고</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { semester: '1학기', name: '프로그래밍 기초', type: '전공진입', credits: '3', status: '유사과목 이수', remark: '동등과목 인정' },
                        { semester: '1학기', name: '미적분학1', type: '전공진입', credits: '3', status: '수강완료', remark: '-' },
                        { semester: '2학기', name: '컴퓨터구조', type: '권장과목', credits: '3', status: '미이수', remark: '-' },
                        { semester: '2학기', name: '미적분학2', type: '전공진입', credits: '3', status: '향후 개설', remark: '-' }
                      ].map((course, idx) => (
                        <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-[#fafbfc]'}>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.semester}</td>
                          <td className="px-9 py-5 text-lg font-medium text-[#101828]">{course.name}</td>
                          <td className="px-9 py-5 text-lg">
                            <span className={`px-4 py-2 rounded-full text-lg font-medium inline-block ${
                              course.type === '전공진입' ? 'bg-blue-100 text-blue-800' :
                              course.type === '권장과목' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {course.type}
                            </span>
                          </td>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.credits}</td>
                          <td className="px-9 py-5 text-lg font-medium">
                            <span className={`${
                              course.status === '수강완료' ? 'text-green-600' :
                              course.status === '유사과목 이수' ? 'text-amber-600' :
                              course.status === '향후 개설' ? 'text-gray-600' :
                              'text-red-600'
                            }`}>
                              {course.status}
                            </span>
                          </td>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.remark}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 3학년 교육과정 테이블 */}
              <div className="bg-white border border-black/10 rounded-2xl overflow-hidden">
                <div className="p-9 border-b border-black/10">
                  <h4 className="text-3xl font-bold text-[#101828] mb-2">3학년 교육과정</h4>
                  <p className="text-xl text-[#6a7282]">{selectedStudent.department.name} 3학년 과정</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-[#f9fafb] border-b border-[#e5e7eb] border-t">
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">학기</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] flex-1">과목명</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">구분</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-32">학점</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-48">이수현황</th>
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">비고</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { semester: '1학기', name: '프로그래밍 기초', type: '전공진입', credits: '3', status: '유사과목 이수', remark: '동등과목 인정' },
                        { semester: '1학기', name: '미적분학1', type: '전공진입', credits: '3', status: '수강완료', remark: '-' },
                        { semester: '2학기', name: '컴퓨터구조', type: '권장과목', credits: '3', status: '미이수', remark: '-' },
                        { semester: '2학기', name: '미적분학2', type: '전공진입', credits: '3', status: '향후 개설', remark: '-' }
                      ].map((course, idx) => (
                        <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-[#fafbfc]'}>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.semester}</td>
                          <td className="px-9 py-5 text-lg font-medium text-[#101828]">{course.name}</td>
                          <td className="px-9 py-5 text-lg">
                            <span className={`px-4 py-2 rounded-full text-lg font-medium inline-block ${
                              course.type === '전공진입' ? 'bg-blue-100 text-blue-800' :
                              course.type === '권장과목' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {course.type}
                            </span>
                          </td>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.credits}</td>
                          <td className="px-9 py-5 text-lg font-medium">
                            <span className={`${
                              course.status === '수강완료' ? 'text-green-600' :
                              course.status === '유사과목 이수' ? 'text-amber-600' :
                              course.status === '향후 개설' ? 'text-gray-600' :
                              'text-red-600'
                            }`}>
                              {course.status}
                            </span>
                          </td>
                          <td className="px-9 py-5 text-lg text-[#6a7282]">{course.remark}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'courses' && (
            <div className="space-y-6">
              {/* 학적 통계 카드들 */}
              <div className="grid grid-cols-3 gap-6">
                <div className="bg-white border border-black/10 rounded-2xl p-9">
                  <p className="text-xl text-[#6a7282] font-medium mb-3">총 취득학점</p>
                  <p className="text-4xl font-bold text-[#101828]">32학점</p>
                </div>
                <div className="bg-white border border-black/10 rounded-2xl p-9">
                  <p className="text-xl text-[#6a7282] font-medium mb-3">평균 학점</p>
                  <p className="text-4xl font-bold text-[#101828] mb-2">2.09 / 4.5</p>
                  <p className="text-xl text-[#6a7282]">총 13과목 이수</p>
                </div>
                <div className="bg-white border border-black/10 rounded-2xl p-9">
                  <p className="text-xl text-[#6a7282] font-medium mb-3">희망 전공</p>
                  <p className="text-4xl font-bold text-[#101828]">{selectedStudent.latest_major_choice || '-'}</p>
                </div>
              </div>

              {/* 수강 과목 목록 테이블 */}
              <div className="bg-white border border-black/10 rounded-2xl overflow-hidden">
                <div className="p-9 border-b border-black/10 flex items-center justify-between">
                  <div>
                    <h4 className="text-3xl font-bold text-[#101828] mb-2">수강 과목 목록</h4>
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
                        <th className="px-9 py-4 text-left font-bold text-lg text-[#6a7282] flex-1">과목명</th>
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
                              <span className="text-lg font-medium" style={{
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
      <div className="max-w-7xl mx-auto px-8">
        {/* Header Section */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-4xl font-bold text-[#101828] mb-2">학생 관리</h1>
            <p className="text-xl text-[#6a7282]">학생 검색 및 관리를 할 수 있습니다.</p>
          </div>
          <button
            onClick={downloadCSV}
            className="flex items-center gap-4 px-3 py-2 bg-[#0e4a84] text-white rounded-lg hover:bg-[#0a3a6b] transition-colors font-medium text-lg"
          >
            <Download className="w-6 h-6" />
            학과별 조사시점별 데이터 다운로드
          </button>
        </div>

        {/* Student Table Card */}
        <div className="bg-white border border-black/10 rounded-2xl overflow-hidden">
          {/* Table Header with Filters */}
          <div className="bg-white p-9 border-b border-black/10">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-[#101828]">학과별 희망 학생 비율</h2>
              <div className="flex gap-4">
                {/* Search Input */}
                <div className="relative w-72">
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
                <select className="px-5 py-4 border border-black/10 rounded-lg text-lg text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]">
                  <option>전체</option>
                </select>
                
                <select className="px-5 py-4 border border-black/10 rounded-lg text-lg text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]">
                  <option>Pride</option>
                </select>
                
                <select className="px-5 py-4 border border-black/10 rounded-lg text-lg text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]">
                  <option>분반</option>
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

          {!loading && !error && students.length > 0 && (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  {/* Table Header */}
                  <thead>
                    <tr className="bg-[#f9fafb] border-b border-[#e5e7eb] border-t">
                      <th className="px-9 py-4 text-left h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-44">이름</th>
                      <th className="px-9 py-4 text-left h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-56">학번</th>
                      <th className="px-9 py-4 text-left h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-44">학과</th>
                      <th className="px-9 py-4 text-center h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">Pride</th>
                      <th className="px-9 py-4 text-left h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-40">분반</th>
                      <th className="px-9 py-4 text-center h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap flex-1 bg-[rgba(67,132,195,0.04)]">최신 희망 학과</th>
                      <th className="px-9 py-4 text-center h-16 font-bold text-lg text-[#6a7282] whitespace-nowrap w-56 bg-[rgba(67,132,195,0.04)]">전공결정도</th>
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
                          {student.department.name}
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
                <span className="text-lg text-[#6a7282]">총 {totalCount}명의 학생</span>
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
                            className={`w-12 h-12 rounded-lg text-lg font-bold ${
                              currentPage === page
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
