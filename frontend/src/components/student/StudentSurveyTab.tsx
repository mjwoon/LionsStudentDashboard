import { useState, useEffect } from 'react';
import type { Student } from './types';
import { getDecisionCertaintyLabel, getDecisionCertaintyColor } from './types';
import { api } from '../../api';
import type { SurveyHistory } from '../../types';

interface StudentSurveyTabProps {
  student: Student;
}

/** 전공결정도 숫자(1-5)를 텍스트로 변환 */
function DecisionBadge({ scale }: { scale: number }) {
  const label = getDecisionCertaintyLabel(scale);
  const colorClass = getDecisionCertaintyColor(scale);
  return (
    <div className={`${colorClass} px-6 py-2.5 rounded-full inline-flex items-center justify-center self-start`}>
      <span className="text-[22px] font-semibold">{label || `${scale}점`}</span>
    </div>
  );
}

/** 설문 카드 1개 */
function SurveyCard({ survey, index }: { survey: SurveyHistory; index: number }) {
  const submittedDate = new Date(survey.submitted_at);
  const dateLabel = isNaN(submittedDate.getTime())
    ? survey.submitted_at
    : `${submittedDate.getFullYear()}년 ${submittedDate.getMonth() + 1}월 ${submittedDate.getDate()}일`;

  return (
    <div className="bg-white border border-black/10 rounded-[14px] p-9 flex-1 flex flex-col gap-9 items-start">
      <div className="flex flex-col justify-start w-full">
        <h3 className="text-[#0e4a84] text-[26px] font-bold mb-[24px]">{index}차 조사</h3>
        <p className="text-[#6a7282] text-[16px]">제출일: {dateLabel}</p>
      </div>

      <div className="flex flex-col gap-[10px] w-full">
        <p className="text-[#6a7282] text-[18px]">1지망</p>
        <p className="text-[#101828] text-[24px] font-semibold">
          {survey.first_choice.name}
        </p>
      </div>

      <div className="flex flex-col gap-[10px] w-full">
        <p className="text-[#6a7282] text-[18px]">2지망</p>
        <p className="text-[#101828] text-[24px] font-semibold">
          {survey.second_choice?.name ?? '미정'}
        </p>
      </div>

      <div className="flex flex-col gap-[10px] w-full">
        <p className="text-[#6a7282] text-[18px]">전공 결정도</p>
        <DecisionBadge scale={survey.decision_scale} />
      </div>
    </div>
  );
}

/** 빈 슬롯 (조사 미참여) */
function EmptyCard({ index }: { index: number }) {
  return (
    <div className="bg-white border border-black/10 rounded-[14px] p-9 flex-1 flex flex-col gap-9 items-start opacity-50">
      <div className="flex flex-col justify-start w-full">
        <h3 className="text-[#6a7282] text-[26px] font-bold mb-[24px]">{index}차 조사</h3>
        <p className="text-[#6a7282] text-[16px]">미참여</p>
      </div>
      <div className="flex flex-col gap-[10px] w-full">
        <p className="text-[#6a7282] text-[18px]">1지망</p>
        <p className="text-[#101828] text-[24px] font-semibold">-</p>
      </div>
      <div className="flex flex-col gap-[10px] w-full">
        <p className="text-[#6a7282] text-[18px]">2지망</p>
        <p className="text-[#101828] text-[24px] font-semibold">-</p>
      </div>
      <div className="flex flex-col gap-[10px] w-full">
        <p className="text-[#6a7282] text-[18px]">전공 결정도</p>
        <div className="bg-[#f3f4f6] px-6 py-2.5 rounded-full inline-flex items-center justify-center self-start">
          <span className="text-[#787e87] text-[20px] font-semibold">-</span>
        </div>
      </div>
    </div>
  );
}

const TOTAL_ROUNDS = 3;

export default function StudentSurveyTab({ student }: StudentSurveyTabProps) {
  const [surveys, setSurveys] = useState<SurveyHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.students.surveys(student.student_id)
      .then((res) => {
        // round 오름차순 정렬
        const sorted = [...res.history].sort((a, b) => a.round - b.round);
        setSurveys(sorted);
      })
      .catch(() => setError('설문 데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false));
  }, [student.student_id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 text-[#6a7282] text-[18px]">
        불러오는 중...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-40 text-red-500 text-[18px]">
        {error}
      </div>
    );
  }

  // round 번호 → SurveyHistory 매핑
  const surveyByRound = new Map(surveys.map((s) => [s.round, s]));

  // 최소 TOTAL_ROUNDS개, 또는 실제 max round 개수만큼 슬롯 생성
  const maxRound = surveys.length > 0 ? Math.max(...surveys.map((s) => s.round)) : TOTAL_ROUNDS;
  const slots = Array.from({ length: Math.max(maxRound, TOTAL_ROUNDS) }, (_, i) => i + 1);

  return (
    <div className="flex gap-[30px] items-stretch justify-center w-full">
      {slots.map((round) => {
        const survey = surveyByRound.get(round);
        return survey
          ? <SurveyCard key={round} survey={survey} index={round} />
          : <EmptyCard key={round} index={round} />;
      })}
    </div>
  );
}
