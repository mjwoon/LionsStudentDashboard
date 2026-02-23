import { useState, useEffect } from 'react';
import { api } from '../../api';
import type { Student, Department, EvaluationResult, CurriculumCourse } from '../../types';

import DepartmentSelector from './DepartmentSelector';
import CurriculumTable from './CurriculumTable';

interface StudentEntryTabProps {
  student: Student;
  selectedDepartmentId: string | null;
}

export default function StudentEntryTab({ student, selectedDepartmentId: initialSelectedDepartmentId }: StudentEntryTabProps) {
  const [evaluationData, setEvaluationData] = useState<EvaluationResult | null>(null);
  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<string | null>(initialSelectedDepartmentId || null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedCollege, setSelectedCollege] = useState<string>('');
  const [curriculum, setCurriculum] = useState<Record<string, Record<string, CurriculumCourse[]>> | null>(null);
  const [curriculumLoading, setCurriculumLoading] = useState(false);
  const isEvaluationAvailable = true;

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

  useEffect(() => {
    if (!selectedDepartmentId) {
      setCurriculum(null);
      return;
    }
    const fetchCurriculum = async () => {
      try {
        setCurriculumLoading(true);
        const data = await api.courses.fullCurriculum(selectedDepartmentId);
        setCurriculum(data.curriculum || data);
      } catch (error) {
        setCurriculum(null);
        console.error('Failed to fetch curriculum:', error);
      } finally {
        setCurriculumLoading(false);
      }
    };
    fetchCurriculum();
  }, [selectedDepartmentId]);

  useEffect(() => {
    if (student && selectedDepartmentId && isEvaluationAvailable) {
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
    } else if (selectedDepartmentId && !isEvaluationAvailable) {
      setEvaluationData(null);
      setEvaluationLoading(false);
    }
  }, [student, selectedDepartmentId, isEvaluationAvailable]);

  // Derived Summary States for Cards
  // entry_requirement (단수) 구조에서 읽기
  const entryReqData = (evaluationData as any)?.analysis_json?.entry_requirement;
  const reqTotal = entryReqData?.total_courses ?? 0;
  const reqCompleted = entryReqData?.completed_courses ?? 0;
  const entryRequirementScore = (evaluationData as any)?.entry_requirement_score ?? entryReqData?.score ?? 0;
  const reqPercent = reqTotal > 0 ? Math.round((reqCompleted / reqTotal) * 100) : Math.round(entryRequirementScore);

  // recommended_courses 구조에서 읽기 (total_courses, similar_completed, similar_rate)
  const recData = evaluationData?.analysis_json?.recommended_courses as any;
  const recTotal = recData?.total_courses ?? recData?.total ?? 0;
  const recCompleted = recData?.similar_completed ?? recData?.completed ?? 0;
  const recPercent = recData?.similar_rate ?? recData?.completion_rate ?? (evaluationData as any)?.recommended_similar_rate ?? 0;

  const overallScore = evaluationData?.overall_score || 0;

  // 1) Main Content Renderer: Returns only the necessary content state (loading, error, or curriculum tables)
  const renderContent = () => {
    if (!selectedDepartmentId) return null;

    if (isEvaluationAvailable && evaluationLoading) {
      return (
        <div className="bg-white border border-black/10 rounded-[14px] p-[36px] items-center text-center">
          <p className="text-[22px] text-[#6a7282]">평가 데이터를 불러오는 중...</p>
        </div>
      );
    }

    if (isEvaluationAvailable && evaluationData) {
      return (
        <>
          {/* 안내 배너 목록 */}
          <div className="flex flex-col gap-[12px] w-full">
            {/* 메인 평가 배너 */}
              {evaluationData.ai_summary && (
              <div className="bg-gradient-to-r from-[#f0f9ff] to-[#e0f2fe] rounded-[14px] px-[36px] py-[20px] border border-blue-100">
                <div className="flex items-start gap-[10px]">
                  <div className="rounded-full shrink-0">
                    <svg className="w-[24px] h-[24px] shrink-0 text-[#0284c7]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-[18px] font-bold text-[#0369a1] mb-2 flex items-center gap-2">
                      AI 튜터 종합 평가
                    </h3>
                    <div className="text-[16px] leading-relaxed text-[#334155] whitespace-pre-wrap">
                      {evaluationData.ai_summary}
                    </div>
                  </div>
                </div>
              </div>
            )}
    

            {/* 주의사항 배너 */}
            <div className="bg-[#FEF9C3] rounded-[14px] px-[36px] py-[20px]">
              <div className="flex items-center gap-[10px]">
                <svg className="w-[24px] h-[24px] shrink-0" fill="none" stroke="#95430E" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.33} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <p className="text-[18px] text-[#95430E] font-semibold leading-normal">
                  과목 구분은 현재 소속인 라이언스 칼리지 기준으로 구분된 정보이며, 향후 전공 진입에 따라 바뀔 수 있음을 유의하십시오.
                </p>
              </div>
            </div>
          
          </div>

          {/* 전공이수체계도 - 학년별 테이블 */}
          <CurriculumTable
            curriculumData={(() => {
              const details = evaluationData.curriculum_details as Record<string, any[]> | undefined;
              if (!details) return {};
              const formatted: Record<string, Record<string, CurriculumCourse[]>> = {};
              Object.entries(details).forEach(([year, courses]) => {
                const yearStr = `${year}학년`;
                formatted[yearStr] = {};
                courses.forEach(course => {
                  const semStr = course.semester ? `${course.semester}학기` : '구분없음';
                  if (!formatted[yearStr][semStr]) formatted[yearStr][semStr] = [];
                  formatted[yearStr][semStr].push(course as CurriculumCourse);
                });
              });
              return formatted;
            })()}
          />
        </>
      );
    }

    if (curriculumLoading) {
      return (
        <div className="bg-white border border-black/10 rounded-[14px] p-[36px] items-center text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#0e4a84] mb-3"></div>
          <p className="text-[22px] text-[#6a7282]">교육과정 데이터를 불러오는 중...</p>
        </div>
      );
    }

    const hasCurriculum = curriculum && Object.keys(curriculum).length > 0;

    if (hasCurriculum) {
      return (
        <div className="space-y-[24px]">
          {!isEvaluationAvailable && (
            <div className="bg-[#FEF9C3] rounded-[14px] px-[36px] py-[20px]">
              <div className="flex items-center gap-[10px]">
                <svg className="w-[24px] h-[24px] shrink-0" fill="none" stroke="#95430E" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.33} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-[20px] text-[#95430E] font-semibold leading-normal">
                  선택한 학과는 현재 평가가 지원되지 않으나, 등록된 교육과정을 확인할 수 있습니다.
                </p>
              </div>
            </div>
          )}
          <CurriculumTable curriculumData={curriculum} />
        </div>
      );
    }

    return (
      <div className="bg-white border border-black/10 rounded-[14px] p-[36px] items-center text-center">
        <p className="text-[22px] text-[#6a7282]">
          {!isEvaluationAvailable
            ? "선택한 학과는 현재 평가가 지원되지 않으며 등록된 교육과정이 없습니다."
            : "등록된 교육과정 데이터가 없습니다."}
        </p>
      </div>
    );
  };

  return (
    <div className="space-y-[24px]">
      {/* 2) Top Selector and Score Cards */}
      {isEvaluationAvailable && evaluationData ? (
        <div className="flex gap-[30px] items-stretch justify-center w-full">
          {/* 분석할 학과 선택 */}
          <div className="bg-white border border-black/10 rounded-[14px] p-9 flex flex-col gap-3 justify-center shrink-0 w-auto">
            <div className="text-[22px] font-bold text-[#101828]">분석할 학과 선택</div>
            <DepartmentSelector
              departments={departments}
              selectedCollege={selectedCollege}
              selectedDepartmentId={selectedDepartmentId}
              onCollegeChange={setSelectedCollege}
              onDepartmentChange={setSelectedDepartmentId}
            />
          </div>

          {/* 전공 진입 필수 */}
          <div className="bg-white border border-black/10 rounded-[14px] p-[37px] flex-1 flex flex-col gap-[12px] justify-center">
            <p className="text-[20px] text-[#6a7282]">전공 진입 필수</p>
            <p className="text-[28px] font-bold text-[#101828]">{reqPercent}%</p>
            <p className="text-[18px] text-[#6a7282]">{reqCompleted} / {reqTotal} 과목</p>
            <div className="bg-[#e5e7eb] h-1.5 rounded-full w-full overflow-hidden mt-1 relative">
              <div className="bg-[#3b82f6] h-full rounded-full absolute left-0 top-0" style={{ width: `${Math.min(100, reqPercent)}%` }} />
            </div>
          </div>

          {/* 권장 과목 */}
          <div className="bg-white border border-black/10 rounded-[14px] p-[37px] flex-1 flex flex-col gap-[12px] justify-center">
            <p className="text-[20px] text-[#6a7282]">권장 과목</p>
            <p className="text-[28px] font-bold text-[#101828]">{recPercent}%</p>
            <p className="text-[18px] text-[#6a7282]">{recCompleted} / {recTotal} 과목</p>
            <div className="bg-[#e5e7eb] h-1.5 rounded-full w-full overflow-hidden mt-1 relative">
              <div className="bg-[#ef4444] h-full rounded-full absolute left-0 top-0" style={{ width: `${Math.min(100, recPercent)}%` }} />
            </div>
          </div>

          {/* 전체 적합도 */}
          <div className="bg-white border border-black/10 rounded-[14px] p-[37px] flex-1 flex flex-col gap-[12px] justify-center">
            <p className="text-[20px] text-[#6a7282]">전체 적합도</p>
            <p className="text-[28px] font-bold text-[#101828]">{overallScore}%</p>
            <p className="text-[18px] text-[#6a7282]">종합 진입 준비도</p>
            <div className="bg-[#e5e7eb] h-1.5 rounded-full w-full overflow-hidden mt-1 relative">
              <div className="bg-[#10b981] h-full rounded-full absolute left-0 top-0" style={{ width: `${Math.min(100, overallScore)}%` }} />
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white border border-black/10 rounded-[14px] p-[36px] flex flex-col gap-[12px] justify-center shrink-0 w-auto">
          <div className="text-[22px] font-bold text-[#101828]">분석할 학과 선택</div>
          <DepartmentSelector
            departments={departments}
            selectedCollege={selectedCollege}
            selectedDepartmentId={selectedDepartmentId}
            onCollegeChange={setSelectedCollege}
            onDepartmentChange={setSelectedDepartmentId}
          />
        </div>
      )}

      {/* 3) Main Table / Status Renderer */}
      {renderContent()}
    </div>
  );
}
