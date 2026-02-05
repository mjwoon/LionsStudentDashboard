
import { useState, useEffect } from 'react';
import { api } from '../../api';
import type { Student } from './types';

// DepartmentCurriculum 타입 import (없으면 any로 대체)
import type { DepartmentCurriculum } from '../../types';

interface StudentEntryTabProps {
  student: Student;
  initialDepartmentId?: number | null;
}

export default function StudentEntryTab({ student, initialDepartmentId }: StudentEntryTabProps) {
  const [evaluationData, setEvaluationData] = useState<any>(null);
  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<number | null>(initialDepartmentId || null);
  const [departments, setDepartments] = useState<any[]>([]);
  const [selectedCollege, setSelectedCollege] = useState<string>('');
  const [curriculum, setCurriculum] = useState<DepartmentCurriculum | null>(null);
  const [curriculumLoading, setCurriculumLoading] = useState(false);

  // 평가 가능한 학과 ID 목록
  const EVALUATION_AVAILABLE_DEPARTMENTS = [304, 303, 207, 204, 600];
  const isEvaluationAvailable = selectedDepartmentId && EVALUATION_AVAILABLE_DEPARTMENTS.includes(selectedDepartmentId);

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

  // Fetch curriculum when department changes
  useEffect(() => {
    if (!selectedDepartmentId) {
      setCurriculum(null);
      return;
    }
    const fetchCurriculum = async () => {
      try {
        setCurriculumLoading(true);
        const data = await api.departments.curriculum(selectedDepartmentId);
        setCurriculum(data.curriculum || data); // data.curriculum 구조일 수도 있음
      } catch (error) {
        setCurriculum(null);
        console.error('Failed to fetch curriculum:', error);
      } finally {
        setCurriculumLoading(false);
      }
    };
    fetchCurriculum();
  }, [selectedDepartmentId]);

  // Fetch evaluation data
  useEffect(() => {
    const isEvalAvailable = selectedDepartmentId && EVALUATION_AVAILABLE_DEPARTMENTS.includes(selectedDepartmentId);

    if (student && selectedDepartmentId && isEvalAvailable) {
      const fetchEvaluation = async () => {
        try {
          setEvaluationLoading(true);
          const data = await api.evaluation.getStudentEvaluation(
            student.student_id,
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
    } else if (selectedDepartmentId && !isEvalAvailable) {
      setEvaluationData(null);
      setEvaluationLoading(false);
    }
  }, [student, selectedDepartmentId]);

  return (
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
              className="w-full px-5 py-3 border border-black/10 rounded-lg text-xl text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84] disabled:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-400"
              value={selectedDepartmentId || ''}
              onChange={(e) => setSelectedDepartmentId(Number(e.target.value))}
              disabled={!selectedCollege}
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
        curriculum && Object.keys(curriculum).length > 0 ? (
          <div className="space-y-6">
            {Object.entries(curriculum).sort(([a], [b]) => a.localeCompare(b)).map(([year, semesters]) => (
              <div key={year} className="bg-white border border-black/10 rounded-[14px] overflow-hidden">
                {/* 학년 헤더 */}
                <div className="bg-white px-7 py-6">
                  <h3 className="text-2xl font-semibold leading-7 text-[#101828] mb-1.5">{year}학년 커리큘럼</h3>
                </div>
                {/* 테이블 */}
                <div className="overflow-x-auto">
                  {Object.entries(semesters).sort(([a], [b]) => a.localeCompare(b)).map(([semester, courses]) => (
                    <div key={semester} className="mb-6">
                      <div className="font-bold text-lg text-blue-700 mb-2">{semester}</div>
                      <table className="w-full mb-2">
                        <thead>
                          <tr className="bg-[#F9FAFB] border-t border-b border-[#E5E7EB]">
                            <th className="px-7 py-0 h-12 text-center text-lg font-bold leading-5 text-[#6A7282] w-[320px]">과목명</th>
                            <th className="px-7 py-0 h-12 text-center text-lg font-bold leading-5 text-[#6A7282] w-[120px]">학점</th>
                            <th className="px-7 py-0 h-12 text-center text-lg font-bold leading-5 text-[#6A7282] w-[160px]">구분</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(Array.isArray(courses) ? courses : []).map((course: any, idx: number) => (
                            <tr key={idx} className={`h-14 ${idx % 2 === 0 ? '' : 'bg-white'}`}>
                              <td className="px-7 py-0 text-center text-lg font-medium leading-5 text-[#101828]">{course.course_name}</td>
                              <td className="px-7 py-0 text-center text-lg font-normal leading-5 text-[#6A7282]">{course.credits}</td>
                              <td className="px-7 py-0 text-center text-lg font-normal leading-5 text-[#6A7282]">{course.course_type}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white border border-black/10 rounded-2xl p-9 text-center">
            <p className="text-xl text-[#6a7282]">평가 데이터가 없습니다.</p>
          </div>
        )
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
                          <th className="px-7 py-0 h-12 text-center text-lg font-bold leading-5 text-[#6A7282] w-[160px]">학기</th>
                          <th className="px-7 py-0 h-12 text-center text-lg font-bold leading-5 text-[#6A7282] w-[320px]">과목명</th>
                          <th className="px-7 py-0 h-12 text-center text-lg font-bold leading-5 text-[#6A7282] bg-[#F2F5F9] w-[160px]">구분</th>
                          <th className="px-7 py-0 h-12 text-center text-lg font-bold leading-5 text-[#6A7282] w-[120px]">학점</th>
                          <th className="px-7 py-0 h-12 text-left text-lg font-bold leading-5 text-[#6A7282] w-[200px]">이수현황</th>
                          <th className="px-7 py-0 h-12 text-left text-lg font-bold leading-5 text-[#6A7282] w-[200px]">비고</th>
                        </tr>
                      </thead>
                      <tbody>
                        {courses.map((course: any, idx: number) => (
                          <tr key={idx} className={`h-16 ${idx % 2 === 0 ? '' : 'bg-white'}`}>
                            <td className="px-7 py-0 text-center text-lg font-normal leading-5 text-[#6A7282]">
                              {course.semester === 1 ? '1학기' : '2학기'}
                            </td>
                            <td className="px-7 py-0 text-center">
                              <p className="text-lg font-medium leading-5 text-[#101828]">{course.course_name}</p>
                            </td>
                            <td className="px-7 py-0 text-center bg-[#F8FAFD]">
                              {(() => {
                                const displayType = course.requirement_type;
                                if (!displayType) return <span className="text-lg font-normal leading-5 text-[#6A7282]">-</span>;
                                
                                // 전공진입 (파란색)
                                if (displayType === '전공진입') {
                                  return (
                                    <span className="inline-flex items-center justify-center px-5 py-2 rounded-full text-lg font-medium leading-5 bg-[#DBEAFE] text-[#1E40AF]">
                                      {displayType}
                                    </span>
                                  );
                                }
                                // 권장과목 (노란색)
                                if (displayType === '권장과목') {
                                  return (
                                    <span className="inline-flex items-center justify-center px-5 py-2 rounded-full text-lg font-medium leading-5 bg-[#FEF9C3] text-[#8D601F]">
                                      {displayType}
                                    </span>
                                  );
                                }
                                // 기타
                                return <span className="text-lg font-normal leading-5 text-[#6A7282]">-</span>;
                              })()}
                            </td>
                            <td className="px-7 py-0 text-center text-lg font-normal leading-5 text-[#6A7282]">
                              {course.credits}
                            </td>
                            <td className="px-7 py-0 text-left">
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
                            <td className="px-7 py-0 text-left text-lg font-normal leading-5 text-[#6A7282]">
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
    </div>
  );
}
