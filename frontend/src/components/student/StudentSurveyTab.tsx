import type { Student } from './types';
import { getDecisionCertaintyLabel } from './types';

interface StudentSurveyTabProps {
  student: Student;
}

export default function StudentSurveyTab({ student }: StudentSurveyTabProps) {
  return (
    <div className="space-y-4">
      {/* 3차 조사 */}
      <div className="bg-white border border-black/10 rounded-xl p-6">
        <div className="mb-4">
          <h3 className="text-xl font-bold text-[#0e4a84] mb-1">3차 조사 완료</h3>
          <p className="text-base text-[#6a7282]">조사 시점: 2024년 2학년 1학기</p>
        </div>

        <div className="flex gap-5 items-center">
          <div className="flex-1">
            <p className="text-lg text-[#6a7282] font-medium mb-1">1지망</p>
            <p className="text-[15pt] font-bold text-[#101828]">
              {student.latest_major_choice || '-'}
            </p>
          </div>
          <div className="flex-1">
            <p className="text-lg text-[#6a7282] font-medium mb-1">2지망</p>
            <p className="text-[15pt] font-bold text-[#101828]">미정</p>
          </div>
          <div className="flex-1">
            <p className="text-lg text-[#6a7282] font-medium mb-1">전공 결정도</p>
            {student.decision_certainty && student.decision_certainty >= 4 ? (
              <div className="inline-block px-4 py-1.5 bg-blue-100 text-blue-800 rounded-full text-lg font-bold">
                {getDecisionCertaintyLabel(student.decision_certainty)}
              </div>
            ) : (
              <div className="inline-block px-4 py-1.5 bg-gray-100 text-gray-800 rounded-full text-lg font-bold">
                미정
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2차 조사 */}
      <div className="bg-white border border-black/10 rounded-xl p-6">
        <div className="mb-4">
          <h3 className="text-[15pt] font-bold text-[#0e4a84] mb-1">2차 조사 완료</h3>
          <p className="text-base text-[#6a7282]">조사 시점: 2023년 1학년 2학기</p>
        </div>

        <div className="flex gap-5 items-center">
          <div className="flex-1">
            <p className="text-lg text-[#6a7282] font-medium mb-1">1지망</p>
            <p className="text-[15pt] font-bold text-[#101828]">-</p>
          </div>
          <div className="flex-1">
            <p className="text-lg text-[#6a7282] font-medium mb-1">2지망</p>
            <p className="text-xl font-bold text-[#101828]">미정</p>
          </div>
          <div className="flex-1">
            <p className="text-lg text-[#6a7282] font-medium mb-1">전공 결정도</p>
            <div className="inline-block px-4 py-1.5 bg-yellow-100 text-yellow-800 rounded-full text-lg font-bold">
              구체 중
            </div>
          </div>
        </div>
      </div>

      {/* 1차 조사 */}
      <div className="bg-white border border-black/10 rounded-xl p-6">
        <div className="mb-4">
          <h3 className="text-[15pt] font-bold text-[#0e4a84] mb-1">1차 조사 완료</h3>
          <p className="text-base text-[#6a7282]">조사 시점: 2023년 1학년 1학기</p>
        </div>

        <div className="flex gap-5 items-center">
          <div className="flex-1">
            <p className="text-lg text-[#6a7282] font-medium mb-1">1지망</p>
            <p className="text-[15pt] font-bold text-[#101828]">미정</p>
          </div>
          <div className="flex-1">
            <p className="text-lg text-[#6a7282] font-medium mb-1">2지망</p>
            <p className="text-[15pt] font-bold text-[#101828]">미정</p>
          </div>
          <div className="flex-1">
            <p className="text-lg text-[#6a7282] font-medium mb-1">전공 결정도</p>
            <div className="inline-block px-4 py-1.5 bg-gray-100 text-gray-700 rounded-full text-[15pt] font-bold">
              미정
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
