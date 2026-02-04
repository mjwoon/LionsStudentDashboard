import { useState, useEffect } from 'react';
import { Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../../api';
import type { Student } from './types';
import { getDecisionCertaintyLabel, getDecisionCertaintyColor, getCourseProgressColor } from './types';

interface StudentListViewProps {
  onStudentSelect: (student: Student, departmentId: number) => void;
}

export default function StudentListView({ onStudentSelect }: StudentListViewProps) {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [perPage] = useState<number>(30);

  // Filter states
  const [trackFilter, setTrackFilter] = useState<string>('전체');
  const [prideFilter, setPrideFilter] = useState<string>('전체');
  const [classFilter, setClassFilter] = useState<string>('전체');

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

  return (
    <div className="min-h-screen py-4 md:py-6">
      <div>
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
          <div className="bg-white p-6 border-b border-black/10">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-[#101828]">LIONS칼리지 전체 학생 목록</h2>
              <div className="flex gap-3">
                {/* Search Input */}
                <div className="relative w-56">
                  <input
                    type="text"
                    placeholder="이름으로 검색 ..."
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="w-full px-4 py-2.5 border border-black/10 rounded-lg text-base text-[#6a7282] placeholder-[#6a7282] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
                  />
                </div>

                {/* Filter Dropdowns */}
                <select
                  value={trackFilter}
                  onChange={(e) => setTrackFilter(e.target.value)}
                  className="px-4 py-2.5 border border-black/10 rounded-lg text-base text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
                >
                  {trackOptions.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>

                <select
                  value={prideFilter}
                  onChange={(e) => setPrideFilter(e.target.value)}
                  className="px-4 py-2.5 border border-black/10 rounded-lg text-base text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
                >
                  <option value="전체">Pride</option>
                  {prideOptions.filter(o => o !== '전체').map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>

                <select
                  value={classFilter}
                  onChange={(e) => setClassFilter(e.target.value)}
                  className="px-4 py-2.5 border border-black/10 rounded-lg text-base text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
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
                      <th className="px-5 py-2.5 text-left h-11 font-bold text-base text-[#6a7282] whitespace-nowrap w-24">이름</th>
                      <th className="px-5 py-2.5 text-left h-11 font-bold text-base text-[#6a7282] whitespace-nowrap w-28">학번</th>
                      <th className="px-5 py-2.5 text-left h-11 font-bold text-base text-[#6a7282] whitespace-nowrap w-32">계열</th>
                      <th className="px-5 py-2.5 text-center h-11 font-bold text-base text-[#6a7282] whitespace-nowrap w-20">Pride</th>
                      <th className="px-5 py-2.5 text-left h-11 font-bold text-base text-[#6a7282] whitespace-nowrap w-20">분반</th>
                      <th className="px-5 py-2.5 text-center h-11 font-bold text-base text-[#6a7282] whitespace-nowrap w-48 bg-[rgba(67,132,195,0.04)]">최신 희망 학과</th>
                      <th className="px-5 py-2.5 text-center h-11 font-bold text-base text-[#6a7282] whitespace-nowrap w-36 bg-[rgba(67,132,195,0.04)]">전공결정도</th>
                      <th className="px-5 py-2.5 text-center h-11 font-bold text-base text-[#6a7282] whitespace-nowrap w-32 bg-[rgba(67,132,195,0.04)]">이수현황</th>
                      <th className="px-5 py-2.5 text-center h-11 font-bold text-base text-[#6a7282] whitespace-nowrap flex-1">수강과목 적합성</th>
                    </tr>
                  </thead>
                  {/* Table Body */}
                  <tbody>
                    {students.map((student, idx) => (
                      <tr
                        key={student.student_id}
                        onClick={() => onStudentSelect(student, student.department.id)}
                        className={`${idx % 2 === 0 ? 'bg-white' : 'bg-[#fafbfc]'} cursor-pointer hover:bg-[#e8f0f7] transition-colors`}
                      >
                        <td className="px-5 py-3 text-base font-bold text-[#0e4a84] whitespace-nowrap">
                          {student.name}
                        </td>
                        <td className="px-5 py-3 text-base text-[#6a7282] whitespace-nowrap">
                          {student.student_id}
                        </td>
                        <td className="px-5 py-3 text-base text-[#6a7282] whitespace-nowrap">
                          {student.academic_info.track || '-'}
                        </td>
                        <td className="px-5 py-3 text-center">
                          <div className="flex items-center justify-center">
                            <div className="border-2 border-[#0e4a84] rounded-full w-8 h-8 flex items-center justify-center">
                              <span className="text-base font-bold text-[#0e4a84]">
                                {student.academic_info.pride}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-3 text-base text-[#6a7282] whitespace-nowrap">
                          {student.academic_info.class_number}반
                        </td>
                        <td className="px-5 py-3 text-center bg-[rgba(67,132,195,0.04)]">
                          <span className="text-base font-bold text-[#0e4a84] whitespace-nowrap">
                            {student.latest_major_choice || '-'}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-center bg-[rgba(67,132,195,0.04)]">
                          {student.decision_certainty ? (
                            <span className={`px-4 py-1 rounded-full text-base font-bold inline-block ${getDecisionCertaintyColor(student.decision_certainty)}`}>
                              {getDecisionCertaintyLabel(student.decision_certainty)}
                            </span>
                          ) : (
                            <span className="text-[#6a7282]">-</span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-center bg-[rgba(67,132,195,0.04)]">
                          {student.completion_status ? (
                            <span className={`px-4 py-1 rounded-full text-base font-bold inline-block bg-green-100 text-green-800`}>
                              {student.completion_status}
                            </span>
                          ) : (
                            <span className="text-[#6a7282]">-</span>
                          )}
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex flex-col gap-1">
                            <span className="text-base text-[#101828]">0%</span>
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
              <div className="bg-[#f9fafb] border-t border-[#e5e7eb] px-6 py-4 flex items-center justify-between">
                <span className="text-sm text-[#6a7282]">총 {filteredStudents.length}명의 학생 {filteredStudents.length !== totalCount && `(전체: ${totalCount}명)`}</span>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="p-2 rounded-lg border border-black/10 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>

                  <div className="flex items-center gap-1.5">
                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter(page => {
                        if (totalPages <= 10) return true;
                        if (page === 1 || page === totalPages) return true;
                        if (Math.abs(page - currentPage) <= 1) return true;
                        return false;
                      })
                      .map((page, idx, arr) => (
                        <div key={page} className="flex items-center gap-1.5">
                          {idx > 0 && arr[idx - 1] !== page - 1 && (
                            <span className="text-[#6a7282]">...</span>
                          )}
                          <button
                            onClick={() => setCurrentPage(page)}
                            className={`w-9 h-9 rounded-lg text-sm font-bold ${currentPage === page
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
                    className="p-2 rounded-lg border border-black/10 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-4 h-4" />
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
