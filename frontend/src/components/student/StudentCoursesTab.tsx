import { useState, useEffect } from 'react';
import { api } from '../../api';
import type { Student } from '../../types';
import type { CourseEnrollment } from '../../types';

interface StudentCoursesTabProps {
  student: Student;
}

export default function StudentCoursesTab({ student }: StudentCoursesTabProps) {
  const [courses, setCourses] = useState<CourseEnrollment[]>([]);
  const [totalCredits, setTotalCredits] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>('전체');

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoading(true);
        const data = await api.students.courses(student.student_id);
        setCourses(data.course_history);
        setTotalCredits(data.total_credits);
      } catch (error) {
        console.error('Failed to fetch courses:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchCourses();
  }, [student.student_id]);

  // 이수구분 목록 추출
  const completionTypes = ['전체', ...Array.from(new Set(courses.map(c => c.completion_type).filter(Boolean)))];

  // 필터 적용
  const filteredCourses = filterType === '전체'
    ? courses
    : courses.filter(c => c.completion_type === filterType);

  // GPA 계산 (P/F 제외)
  const gradedCourses = courses.filter(c => c.grade && c.grade !== 'P' && c.grade !== 'F' && c.numeric_grade != null && c.numeric_grade > 0);
  const totalGradePoints = gradedCourses.reduce((sum, c) => sum + (c.numeric_grade || 0) * c.credits, 0);
  const totalGradedCredits = gradedCourses.reduce((sum, c) => sum + c.credits, 0);
  const gpa = totalGradedCredits > 0 ? totalGradePoints / totalGradedCredits : 0;

  const getGradeColor = (grade?: string) => {
    if (!grade) return '#6b7280';
    if (grade.startsWith('A')) return '#3b82f6';
    if (grade.startsWith('B')) return '#10b981';
    if (grade.startsWith('C')) return '#f59e0b';
    if (grade.startsWith('D')) return '#f97316';
    if (grade === 'P') return '#6b7280';
    return '#ef4444';
  };

  const getCategoryStyle = (category?: string) => {
    switch (category) {
      case '전공필수':
      case '전공핵심':
        return { bg: '#dbeafe', color: '#1e40af' };
      case '전공선택':
      case '전공심화':
        return { bg: '#dcfce7', color: '#016630' };
      case '교양필수':
        return { bg: '#ffedd4', color: '#9f2d00' };
      case '전공기초':
        return { bg: '#fef9c3', color: '#8d601f' };
      default:
        return { bg: '#f3e8ff', color: '#6e11b0' };
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="bg-white border border-black/10 rounded-2xl p-9 text-center">
          <p className="text-xl text-[#6a7282]">수강 이력을 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 학적 통계 카드들 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-black/10 rounded-2xl p-6">
          <p className="text-[9pt] text-[#6a7282] font-medium mb-2">총 취득학점</p>
          <p className="text-[15pt] font-bold text-[#101828]">{totalCredits}학점</p>
        </div>
        <div className="bg-white border border-black/10 rounded-2xl p-6">
          <p className="text-[9pt] text-[#6a7282] font-medium mb-2">평균 학점</p>
          <p className="text-[15pt] font-bold text-[#101828] mb-1">{gpa.toFixed(2)} / 4.5</p>
        </div>
        <div className="bg-white border border-black/10 rounded-2xl p-6">
          <p className="text-[9pt] text-[#6a7282] font-medium mb-2">희망 전공</p>
          <p className="text-[15pt] font-bold text-[#101828]">{student.latest_major_choice || '-'}</p>
        </div>
      </div>
      {/* 수강 과목 목록 테이블 */}
      <div className="bg-white border border-black/10 rounded-2xl overflow-hidden">
        <div className="px-6 py-5 border-b border-black/10 flex items-center justify-between">
          <div>
            <h4 className="text-[15pt] font-bold text-[#101828] mb-1">수강 과목 목록</h4>
            <p className="text-sm text-[#6a7282]">전체 과목 {filteredCourses.length}개</p>
          </div>
          <div className="relative">
            <select
              className="bg-white border border-black/10 rounded-lg px-3 py-2 text-sm text-[#101828] font-medium appearance-none pr-8 focus:outline-none focus:ring-2 focus:ring-[#0e4a84]"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
            >
              {completionTypes.map(type => (
                <option key={type} value={type}>{type === '전체' ? '이수구분: 전체' : type}</option>
              ))}
            </select>
            <svg className="w-3.5 h-3.5 text-[#101828] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#f9fafb] border-b border-[#e5e7eb] border-t">
                <th className="px-6 py-2.5 text-center font-bold text-[13px] text-[#6a7282] whitespace-nowrap w-20">년도</th>
                <th className="px-6 py-2.5 text-center font-bold text-[13px] text-[#6a7282] whitespace-nowrap w-20">학기</th>
                <th className="px-6 py-2.5 text-center font-bold text-[13px] text-[#6a7282] whitespace-nowrap w-20">과목코드</th>
                <th className="px-6 py-2.5 text-center font-bold text-[13px] text-[#6a7282] whitespace-nowrap w-32">과목명</th>
                <th className="px-6 py-2.5 text-center font-bold text-[13px] text-[#6a7282] whitespace-nowrap w-14">학점</th>
                <th className="px-6 py-2.5 text-center font-bold text-[13px] text-[#6a7282] whitespace-nowrap w-14 bg-[#F2F5F9]">성적</th>
                <th className="px-6 py-2.5 text-center font-bold text-[13px] text-[#6a7282] whitespace-nowrap w-28 bg-[#F2F5F9]">이수구분</th>
              </tr>
            </thead>
            <tbody>
              {filteredCourses.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-[13px] text-[#6a7282]">
                    수강 이력이 없습니다.
                  </td>
                </tr>
              ) : (
                filteredCourses.map((course, idx) => {
                  const catStyle = getCategoryStyle(course.completion_type);
                  return (
                    <tr key={`${course.course_id}-${course.year}-${course.semester}-${idx}`} className={idx % 2 === 0 ? 'bg-white' : 'bg-[#fafbfc]'}>
                      <td className="px-6 py-3 text-center text-[13px] text-[#6a7282]">{course.year}</td>
                      <td className="px-6 py-3 text-center text-[13px] text-[#6a7282]">{course.semester}학기</td>
                      <td className="px-6 py-3 text-center text-[13px] text-[#6a7282]">{course.course_code}</td>
                      <td className="px-6 py-3 text-center text-[13px] font-medium text-[#101828]">{course.course_name}</td>
                      <td className="px-6 py-3 text-center text-[13px] text-[#6a7282]">{course.credits}</td>
                      <td className="px-6 py-3 text-center text-[13px] bg-[#F8FAFD]">
                        {course.grade ? (
                          <div className="rounded-lg px-2 py-1 inline-flex items-center justify-center w-12"
                            style={{
                              borderColor: getGradeColor(course.grade),
                              color: getGradeColor(course.grade),
                            }}>
                            <span className="text-[13px] font-semibold">{course.grade}</span>
                          </div>
                        ) : (
                          <span className="text-[13px] font-semibold" style={{ color: '#898F99' }}>수강중</span>
                        )}
                      </td>
                      <td className="px-6 py-3 text-center text-[13px] bg-[#F8FAFD]">
                        <div className="px-4 py-1 rounded-full inline-flex items-center justify-center"
                          style={{ backgroundColor: catStyle.bg }}>
                          <span className="text-[13px] font-bold" style={{ color: catStyle.color }}>
                            {course.completion_type || '-'}
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
