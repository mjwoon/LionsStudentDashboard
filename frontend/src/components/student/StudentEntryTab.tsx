import { useState, useEffect } from 'react';
import { api } from '../../api';
import type { Student, Department, EvaluationResult, CurriculumCourse } from '../../types';

import DepartmentSelector from './DepartmentSelector';
import CurriculumTable from './CurriculumTable';

// 상태값 파싱 헬퍼: AI 총평 문자열에서 상태값과 의견을 분리
const STATUS_STYLES: Record<string, { bg: string; border: string; titleColor: string; textColor: string }> = {
  '양호': { bg: 'from-[#ecfdf5] to-[#d1fae5]', border: 'border-emerald-200', titleColor: 'text-[#065f46]', textColor: 'text-[#064e3b]' },
  '우수': { bg: 'from-[#f0f9ff] to-[#e0f2fe]', border: 'border-blue-100',    titleColor: 'text-[#0369a1]', textColor: 'text-[#334155]' },
  '주의': { bg: 'from-[#fffbeb] to-[#fef3c7]', border: 'border-amber-200',   titleColor: 'text-[#92400e]', textColor: 'text-[#78350f]' },
  '위험': { bg: 'from-[#fef2f2] to-[#fee2e2]', border: 'border-red-200',     titleColor: 'text-[#991b1b]', textColor: 'text-[#7f1d1d]' },
};

const STATUS_BADGE_COLORS: Record<string, string> = {
  '양호': 'bg-emerald-100 text-emerald-800',
  '우수': 'bg-blue-100 text-blue-800',
  '주의': 'bg-amber-100 text-amber-800',
  '위험': 'bg-red-100 text-red-800',
};

function parseAiStatus(summary: string) {
  const defaultStyle = STATUS_STYLES['양호'];
  if (summary.includes(' : ')) {
    const [label, ...rest] = summary.split(' : ');
    const trimmed = label.trim();
    if (trimmed in STATUS_STYLES) {
      return { label: trimmed, opinion: rest.join(' : '), style: STATUS_STYLES[trimmed] };
    }
  }
  return { label: '양호', opinion: summary, style: defaultStyle };
}

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
  // 평가 가능 여부는 응답이 알려준다(진입요건·권장과목·1학년 교육과정 중 하나라도
  // 등록돼 있는지). 근거가 0개인 학과는 어떤 학생에게나 같은 값이라 점수를 내지 않는다.
  // 조회 자체는 항상 시도해야 이 플래그를 알 수 있으므로 fetch 게이트로는 쓰지 않는다.

  useEffect(() => {
    const fetchDepartments = async () => {
      try {
        // 진입 대상 전공만 — 학생의 소속 계열은 분석 대상이 아니다.
        const response = await api.departments.list(true);
        setDepartments(response.departments);

        // 학생 목록에서 넘어올 때 학생 '본인의 소속 계열'이 초기 선택으로 실려 온다
        // (StudentListView가 student.department.id를 넘긴다). 자연계열·인문사회계열은
        // 학과가 아니라 진입 대상이 될 수 없으므로, 대상 목록에 없는 초기값은 버린다.
        // 그대로 두면 선택 상자는 비어 있는데 점수 카드만 채워지는 상태가 된다.
        setSelectedDepartmentId((current) =>
          current && !response.departments.some((d) => String(d.id) === String(current))
            ? null
            : current
        );
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
    if (!student || !selectedDepartmentId) {
      // 선택이 없으면 점수 카드도 비운다. 앞선 조회 결과를 그대로 두면
      // '학과를 선택하세요'인데 점수만 떠 있는 상태가 된다.
      setEvaluationData(null);
      setEvaluationLoading(false);
      return;
    }

    // 학과를 바꾸는 동안 이전 학과의 점수가 남아 보이지 않도록 즉시 비운다.
    let cancelled = false;
    setEvaluationData(null);
    setEvaluationLoading(true);

    const fetchEvaluation = async () => {
      try {
        const data = await api.evaluation.getStudentEvaluation(
          student.student_id,
          selectedDepartmentId
        );
        if (!cancelled) setEvaluationData(data);
      } catch (error) {
        console.error('Failed to fetch evaluation:', error);
        if (!cancelled) setEvaluationData(null);
      } finally {
        if (!cancelled) setEvaluationLoading(false);
      }
    };
    fetchEvaluation();

    // 빠르게 학과를 바꾸면 먼저 건 요청이 나중에 도착해 엉뚱한 학과 점수를 덮어쓸 수 있다.
    return () => {
      cancelled = true;
    };
  }, [student, selectedDepartmentId]);

  // Derived Summary States for Cards
  // entry_requirement (단수) 구조에서 읽기
  const entryReqData = (evaluationData as any)?.analysis_json?.entry_requirement;
  const reqTotal = entryReqData?.total_courses ?? 0;
  const reqCompleted = entryReqData?.completed_courses ?? 0;
  const entryRequirementScore = (evaluationData as any)?.entry_requirement_score ?? entryReqData?.score ?? 0;
  // 진입요건 %는 등급을 결정하는 규칙 점수(entry_requirement_score)를 그대로 사용한다.
  // reqCompleted/reqTotal은 백엔드가 최고 그룹의 qualifying/required로 채우므로 "X/Y 과목"이 %와 일치.
  const reqPercent = Math.round(entryRequirementScore);
  // 요건이 등록되지 않은 학과는 점수가 공허참 100%다 — 만점처럼 보이면 안 되므로 카드에서 분리한다.
  const reqHasData = entryReqData?.has_requirement ?? reqTotal > 0;
  // 진입요건은 학칙이 정하는 관문이다. open(충족) / blocked(미충족) / unknown(미등록).
  const entryGate: 'open' | 'pending' | 'blocked' | 'unknown' =
    (evaluationData as any)?.entry_gate ?? entryReqData?.gate ?? 'unknown';

  // recommended_courses 구조에서 읽기 (total_courses, similar_completed, similar_rate)
  const recData = evaluationData?.analysis_json?.recommended_courses as any;
  const recTotal = recData?.total_courses ?? recData?.total ?? 0;
  const recCompleted = recData?.similar_completed ?? recData?.completed ?? 0;
  const recPercent = recData?.similar_rate ?? recData?.completion_rate ?? (evaluationData as any)?.recommended_similar_rate ?? 0;
  const recHasData = recData?.has_data ?? recTotal > 0;

  // 근거가 0개인 학과는 overall_score가 null로 온다 — 0점이라는 판정이 아니다.
  const isEvaluationAvailable =
    (evaluationData as any)?.is_evaluable ??
    (evaluationData as any)?.analysis_json?.overall?.is_evaluable ??
    true;
  const overallScore = evaluationData?.overall_score ?? 0;
  // 종합 점수가 실제로 몇 개 항목을 반영했는지 — 학과끼리 비교할 때 기준이 다름을 알린다.
  const scoredCount =
    ((evaluationData as any)?.analysis_json?.overall?.scored_components?.length ?? 3) as number;

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
      // AI 상태값 파싱
      const aiStatus = evaluationData.ai_summary ? parseAiStatus(evaluationData.ai_summary) : null;

      return (
        <>
          {/* 안내 배너 목록 */}
          <div className="flex flex-col gap-[12px] w-full">
            {/* 메인 평가 배너 - 상태값에 따라 색상 분기 */}
              {aiStatus && (
              <div className={`bg-gradient-to-r ${aiStatus.style.bg} rounded-[14px] px-[36px] py-[20px] border ${aiStatus.style.border}`}>
                <div className="flex items-start gap-[10px]">
                  <div className="rounded-full shrink-0">
                    <svg className={`w-[24px] h-[24px] shrink-0 ${aiStatus.style.titleColor}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className={`text-[18px] font-bold ${aiStatus.style.titleColor} mb-2 flex items-center gap-2`}>
                      AI 튜터 종합 평가
                      <span className={`text-[13px] font-semibold px-2.5 py-0.5 rounded-full ${STATUS_BADGE_COLORS[aiStatus.label]}`}>
                        {aiStatus.label}
                      </span>
                    </h3>
                    <div className={`text-[16px] leading-relaxed ${aiStatus.style.textColor} whitespace-pre-wrap`}>
                      {aiStatus.opinion}
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
                  이 학과는 진입요건·권장과목이 등록되지 않아 적합도를 계산할 수 없습니다. 등록된 교육과정은 아래에서 확인할 수 있습니다.
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
            ? "이 학과는 진입요건·권장과목·교육과정이 모두 등록되지 않아 적합도를 계산할 수 없습니다."
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
            <p className="text-[28px] font-bold text-[#101828]">{reqHasData ? `${reqPercent}%` : "—"}</p>
            <p className="text-[18px] text-[#6a7282]">
              {reqHasData ? `${reqCompleted} / ${reqTotal} 과목` : "등록된 진입요건 없음"}
            </p>
            <div className="bg-[#e5e7eb] h-1.5 rounded-full w-full overflow-hidden mt-1 relative">
              <div className="bg-[#3b82f6] h-full rounded-full absolute left-0 top-0" style={{ width: `${reqHasData ? Math.min(100, reqPercent) : 0}%` }} />
            </div>
          </div>

          {/* 권장 과목 */}
          <div className="bg-white border border-black/10 rounded-[14px] p-[37px] flex-1 flex flex-col gap-[12px] justify-center">
            <p className="text-[20px] text-[#6a7282]">권장 과목</p>
            <p className="text-[28px] font-bold text-[#101828]">{recHasData ? `${recPercent}%` : "—"}</p>
            <p className="text-[18px] text-[#6a7282]">
              {recHasData ? `${recCompleted} / ${recTotal} 과목` : "등록된 권장과목 없음"}
            </p>
            <div className="bg-[#e5e7eb] h-1.5 rounded-full w-full overflow-hidden mt-1 relative">
              <div className="bg-[#ef4444] h-full rounded-full absolute left-0 top-0" style={{ width: `${recHasData ? Math.min(100, recPercent) : 0}%` }} />
            </div>
          </div>

          {/* 전체 적합도 */}
          <div className="bg-white border border-black/10 rounded-[14px] p-[37px] flex-1 flex flex-col gap-[12px] justify-center">
            <p className="text-[20px] text-[#6a7282]">전체 적합도</p>
            {/* 관문 상태가 헤드라인이다 — 요건 미충족이면 준비도가 높아도 진입할 수 없다. */}
            {entryGate === 'blocked' && (
              <p className="text-[18px] font-semibold text-[#b42318]">진입요건 미충족</p>
            )}
            {/* 아직 안 들은 것은 차단이 아니다 — 1학년에게는 정상 상태다. */}
            {entryGate === 'pending' && (
              <p className="text-[18px] font-semibold text-[#b54708]">진입요건 과목 미이수</p>
            )}
            {entryGate === 'open' && (
              <p className="text-[18px] font-semibold text-[#067647]">진입요건 충족</p>
            )}
            <p className="text-[28px] font-bold text-[#101828]">{overallScore}%</p>
            <p className="text-[18px] text-[#6a7282]">
              {scoredCount >= 3
                ? "종합 진입 준비도"
                : `종합 진입 준비도 · ${scoredCount}개 항목 기준`}
            </p>
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
