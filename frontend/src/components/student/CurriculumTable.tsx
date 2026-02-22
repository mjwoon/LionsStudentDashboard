
import type { CurriculumCourse } from '../../types';

interface CurriculumTableProps {
  curriculumData: Record<string, Record<string, CurriculumCourse[]>>;
}

export default function CurriculumTable({ curriculumData }: CurriculumTableProps) {
  if (!curriculumData || Object.keys(curriculumData).length === 0) {
    return (
      <div className="bg-white border border-black/10 rounded-[12px] p-[24px] items-center text-center">
        <p className="text-[15px] text-[#6a7282]">
          평가 데이터가 없습니다.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-[16px]">
      {Object.entries(curriculumData).sort(([a], [b]) => a.localeCompare(b)).map(([year, semesters]) => (
        <div key={year} className="bg-white border border-black/10 rounded-[12px] overflow-hidden flex flex-col items-center">
          {/* Year Header */}
          <div className="bg-white px-[24px] py-[20px] w-full items-start justify-center flex flex-col">
            <h3 className="text-[20px] font-semibold leading-[normal] text-[#101828]">
              {year} 교육과정
            </h3>
          </div>

          <div>
            {Object.entries(semesters).sort(([a], [b]) => a.localeCompare(b)).map(([semester, courses]) => (
              <div key={semester}>
                <table className="w-full text-center border-collapse table-fixed">
                  <thead className="bg-[#f9fafb] border-[#e5e7eb] border-y">
                    <tr>
                      <th className="h-[46px] px-[24px] w-[100px] font-bold text-[18px] text-[#6a7282] align-middle whitespace-nowrap">학기</th>
                      <th className="h-[46px] px-[24px] font-bold text-[15px] text-[#6a7282] align-middle">과목명</th>
                      <th className="h-[46px] px-[24px] w-[150px] font-bold text-[15px] text-[#6a7282] align-middle whitespace-nowrap">구분</th>
                      <th className="h-[46px] px-[24px] w-[100px] font-bold text-[15px] text-[#6a7282] align-middle whitespace-nowrap">학점</th>
                      <th className="h-[46px] px-[24px] w-[200px] font-bold text-[15px] text-[#6a7282] align-middle whitespace-nowrap">이수현황</th>
                      <th className="h-[46px] px-[24px] w-[200px] font-bold text-[15px] text-[#6a7282] align-middle whitespace-nowrap">비고</th>
                    </tr>
                  </thead>

                  <tbody>
                    {(Array.isArray(courses) ? courses : []).map((course: CurriculumCourse, idx: number) => (
                      <tr key={idx} className={`h-[56px] ${idx % 2 === 0 ? 'bg-white' : 'bg-[#FAFBFC]'}`}>
                        <td className="px-[24px] text-[15px] text-[#6A7282] align-middle">
                          {course.semester === 1 ? '1학기' : '2학기'}
                        </td>
                        <td className="px-[24px] text-[15px] text-[#101828] align-middle">
                          {course.course_name}
                        </td>
                        <td className="px-[24px] align-middle">
                          {(() => {
                            const displayType = course.requirement_type || course.course_type;
                            if (!displayType) return <span className="text-[15px] text-[#6A7282]">-</span>;

                            if (displayType === '전공진입') {
                              return (
                                <div className="bg-[#dbeafe] inline-flex items-center justify-center px-[16px] py-[6px] rounded-[100px]">
                                  <span className="text-[#1e40af] text-[14px] whitespace-nowrap">{displayType}</span>
                                </div>
                              );
                            }
                            if (displayType === '권장과목') {
                              return (
                                <div className="bg-[#fef9c3] inline-flex items-center justify-center px-[16px] py-[6px] rounded-[100px]">
                                  <span className="text-[#8d601f] text-[14px] whitespace-nowrap">{displayType}</span>
                                </div>
                              );
                            }
                            return <span className="text-[15px] text-[#6A7282]">{displayType}</span>;
                          })()}
                        </td>
                        <td className="px-[24px] text-[15px] text-[#6A7282] align-middle">
                          {course.credits}
                        </td>

                        <td className="px-[24px] align-middle">
                          <div className="flex items-center justify-center gap-[8px]">
                            {course.enrolled && course.grade ? (
                              <>
                                <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="#26BD89" xmlns="http://www.w3.org/2000/svg">
                                  <circle cx="12" cy="12" r="10" strokeWidth="2" />
                                  <path d="M9 12l2 2 4-4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                                <span className="text-[15px] text-[#26BD89]">
                                  이수완료 {course.grade !== 'P/F' && course.grade !== 'S/U' ? `(${course.grade})` : ''}
                                </span>
                              </>
                            ) : course.enrolled && !course.grade ? (
                              <>
                                <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="#898F99" xmlns="http://www.w3.org/2000/svg">
                                  <circle cx="12" cy="12" r="10" strokeWidth="2" />
                                  <path d="M12 8v4m0 4h.01" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                                <span className="text-[15px] text-[#898F99]">수강중</span>
                              </>
                            ) : (
                              <>
                                <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="#F04462" xmlns="http://www.w3.org/2000/svg">
                                  <circle cx="12" cy="12" r="10" strokeWidth="2" />
                                  <path d="M15 9l-6 6m0-6l6 6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                                <span className="text-[15px] text-[#F04462]">미이수</span>
                              </>
                            )}
                          </div>
                        </td>
                        <td className="px-[24px] text-[15px] text-[#6a7282] align-middle">
                          {(course as any).enrolled_department_name && course.course_type !== '교양필수'
                            ? `유사/동등 인정`
                            : '-'}
                        </td>
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
  );
}
