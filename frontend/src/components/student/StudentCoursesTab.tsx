import type { Student } from './types';

interface StudentCoursesTabProps {
  student: Student;
}

export default function StudentCoursesTab({ student }: StudentCoursesTabProps) {
  return (
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
          <p className="text-[22pt] font-bold text-[#101828]">{student.latest_major_choice || '-'}</p>
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
                <th className="px-9 py-4 text-center font-bold text-lg text-[#6a7282] whitespace-nowrap w-28">년도</th>
                <th className="px-9 py-4 text-center font-bold text-lg text-[#6a7282] whitespace-nowrap w-28">학기</th>
                <th className="px-9 py-4 text-center font-bold text-lg text-[#6a7282] whitespace-nowrap w-28">과목코드</th>
                <th className="px-9 py-4 text-center font-bold text-lg text-[#6a7282] whitespace-nowrap w-44">과목명</th>
                <th className="px-9 py-4 text-center font-bold text-lg text-[#6a7282] whitespace-nowrap w-20">학점</th>
                <th className="px-9 py-4 text-center font-bold text-lg text-[#6a7282] whitespace-nowrap w-20  bg-[#F2F5F9] ">성적</th>
                <th className="px-9 py-4 text-center font-bold text-lg text-[#6a7282] whitespace-nowrap w-40  bg-[#F2F5F9] ">이수구분</th>
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
                  <td className="px-9 py-5 text-center text-lg text-[#6a7282]">{course.year}</td>
                  <td className="px-9 py-5 text-center text-lg text-[#6a7282]">{course.semester}</td>
                  <td className="px-9 py-5 text-center text-lg text-[#6a7282]">{course.code}</td>
                  <td className="px-9 py-5 text-center text-lg font-medium text-[#101828]">{course.name}</td>
                  <td className="px-9 py-5 text-center text-lg text-[#6a7282]">{course.credits}</td>
                  <td className="px-9 py-5 text-center text-lg bg-[#F8FAFD]">
                    <div className="rounded-lg px-3 py-2 inline-flex items-center justify-center w-16"
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
                  <td className="px-9 py-5 text-center text-lg bg-[#F8FAFD]">
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
  );
}
