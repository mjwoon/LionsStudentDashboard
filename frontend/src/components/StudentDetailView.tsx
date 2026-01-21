import { useState, useEffect } from 'react';
import { ChevronLeft, Download, CheckCircle2, AlertCircle, XCircle } from 'lucide-react';
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
}

interface CourseEnrollment {
  course_id: number;
  course_code: string;
  course_name: string;
  credits: number;
  year: number;
  semester: number;
  completion_type: string;
  is_entry_requirement: boolean;
  is_retake: boolean;
}

interface SurveyHistory {
  survey_id: number;
  round: number;
  submitted_at: string;
  first_choice: { id: number; name: string };
  second_choice?: { id: number; name: string };
  decision_scale: number;
}

interface Department {
  id: number;
  code: string;
  name: string;
  college_name: string;
  min_credits: number;
}

interface College {
  id: number;
  name: string;
}

export default function StudentDetailView() {
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string>('');
  const [studentDetail, setStudentDetail] = useState<Student | null>(null);
  const [showDetail, setShowDetail] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'survey' | 'entry' | 'courses'>('survey');
  const [courses, setCourses] = useState<CourseEnrollment[]>([]);
  const [surveys, setSurveys] = useState<SurveyHistory[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [colleges, setColleges] = useState<College[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCollege, setSelectedCollege] = useState<number>(0);
  const [pathwayDept, setPathwayDept] = useState<number | null>(null);
  const [curriculum, setCurriculum] = useState<any>(null);
  const [loadingCurriculum, setLoadingCurriculum] = useState(false);
  const [courseFilter, setCourseFilter] = useState<string>('all');

  // Fetch students list
  useEffect(() => {
    const fetchStudents = async () => {
      try {
        setLoading(true);
        const response = await api.students.list(1, 100);
        setStudents(response.students);
      } catch (error) {
        console.error('Failed to fetch students:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStudents();
  }, []);

  // Fetch departments and colleges
  useEffect(() => {
    const fetchDepartmentsAndColleges = async () => {
      try {
        const deptResponse = await api.departments.list();
        setDepartments(deptResponse.departments);

        // Extract unique colleges from departments
        const uniqueColleges: College[] = [];
        const collegeMap = new Map<number, string>();

        deptResponse.departments.forEach(dept => {
          const collegeName = dept.college_name;
          // Extract college ID from department (departments belong to colleges)
          if (!collegeMap.has(dept.id)) {
            // This is a simplified approach - in real scenario you'd get this from backend
            const collegeId = Math.floor(dept.id / 100);
            if (!collegeMap.has(collegeId)) {
              collegeMap.set(collegeId, collegeName);
              uniqueColleges.push({ id: collegeId, name: collegeName });
            }
          }
        });

        setColleges([{ id: 0, name: '전체' }, ...uniqueColleges]);
      } catch (error) {
        console.error('Failed to fetch departments:', error);
      }
    };
    fetchDepartmentsAndColleges();
  }, []);

  // Fetch student detail when selected
  useEffect(() => {
    if (selectedStudent && showDetail) {
      const fetchStudentDetail = async () => {
        try {
          setLoading(true);
          const [detail, coursesRes, surveysRes] = await Promise.all([
            api.students.get(selectedStudent),
            api.students.courses(selectedStudent),
            api.students.surveys(selectedStudent)
          ]);
          setStudentDetail(detail);
          setCourses(coursesRes.course_history);
          setSurveys(surveysRes.history);
        } catch (error) {
          console.error('Failed to fetch student detail:', error);
        } finally {
          setLoading(false);
        }
      };
      fetchStudentDetail();
    }
  }, [selectedStudent, showDetail]);

  // Fetch curriculum when pathwayDept changes (소프트웨어융합대학 > 컴퓨터학부)
  useEffect(() => {
    if (pathwayDept === 301 && selectedCollege === 3) {
      const fetchCurriculum = async () => {
        try {
          setLoadingCurriculum(true);
          const response = await fetch('http://localhost:8080/api/courses/curriculum');
          const data = await response.json();
          setCurriculum(data);
        } catch (error) {
          console.error('Failed to fetch curriculum:', error);
        } finally {
          setLoadingCurriculum(false);
        }
      };
      fetchCurriculum();
    } else {
      setCurriculum(null);
    }
  }, [pathwayDept, selectedCollege]);

  const student = studentDetail;

  // 학점 통계 (간단히 총 학점만 계산 - 실제 성적은 백엔드에서 관리)
  const totalCredits = courses.reduce((sum, c) => sum + c.credits, 0);

  // 학기별 이수 학점 데이터
  const semesterData = courses.reduce((acc, course) => {
    const semesterKey = `${course.year}-${course.semester}`;
    const existing = acc.find(s => s.semester === semesterKey);
    if (existing) {
      existing.credits += course.credits;
    } else {
      acc.push({ semester: semesterKey, credits: course.credits });
    }
    return acc;
  }, [] as { semester: string; credits: number }[]);

  const downloadCSV = () => {
    const csv = [
      ['학생명', '학번', '학과', 'Pride', '분반', '상태'],
      ...(showDetail && student
        ? [[student.name, student.student_id, student.department.name, student.academic_info.pride, student.academic_info.class_number, student.academic_info.status]]
        : students.map((s) => [s.name, s.student_id, s.department.name, s.academic_info.pride, s.academic_info.class_number, s.academic_info.status]))
    ].map((row) => row.join(',')).join('\n');

    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', '학생정보.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 희망 전공 진입 분석 함수

  const getPathwayAnalysis = () => {
    if (!pathwayDept) return null;

    // For now, we'll use the actual courses from the department
    // In a real implementation, you'd fetch department curriculum from API
    const currentGrade = 1; // All students are 1st year from seed_data

    // Count entry requirement courses
    const requiredCourses = courses.filter(c => c.is_entry_requirement);
    const completedRequired = requiredCourses.length;

    // Count recommended courses (completion_type includes 기초 or 핵심)
    const recommendedCourses = courses.filter(c =>
      c.completion_type === '전공기초' || c.completion_type === '전공핵심'
    );
    const completedRecommended = recommendedCourses.length;

    // Simple completion metrics based on enrolled courses
    const totalEnrolled = courses.length;
    const requiredCompletionRate = totalEnrolled > 0 ? (completedRequired / totalEnrolled) * 100 : 0;
    const recommendedCompletionRate = totalEnrolled > 0 ? (completedRecommended / totalEnrolled) * 100 : 0;
    const overallRate = totalEnrolled > 0 ? ((completedRequired + completedRecommended) / totalEnrolled) * 100 : 0;

    return {
      requiredCourses: requiredCourses,
      completedRequired,
      requiredCompletionRate,
      recommendedCourses: recommendedCourses,
      completedRecommended,
      recommendedCompletionRate,
      overallRate,
      currentGrade,
    };
  };

  const pathwayAnalysis = getPathwayAnalysis();

  const getStatusMessage = () => {
    if (!pathwayAnalysis) return '';

    const { requiredCompletionRate, recommendedCompletionRate } = pathwayAnalysis;

    if (requiredCompletionRate >= 80 && recommendedCompletionRate >= 60) {
      return '우수: 전공진입 준비가 매우 잘 되어있습니다!';
    } else if (requiredCompletionRate >= 60) {
      return '양호: 전공진입 필수 과목을 충실히 이수하고 있습니다.';
    } else if (requiredCompletionRate >= 40) {
      return '주의: 전공진입 필수 과목 이수율을 높일 필요가 있습니다.';
    } else {
      return '경고: 전공진입을 위해 더 많은 필수 과목 이수가 필요합니다.';
    }
  };

  // Helper functions for course status checking
  const checkCourseStatus = (curriculumCourse: any, studentCourses: CourseEnrollment[]) => {
    // Check if student has completed this exact course
    const exactMatch = studentCourses.find(
      sc => sc.course_code === curriculumCourse.course_code
    );

    if (exactMatch) {
      return { status: 'completed', course: exactMatch };
    }

    // Check if it's a future course (based on course_year)
    if (curriculumCourse.course_year && curriculumCourse.course_year > 1) {
      return { status: 'future', course: null };
    }

    // Not completed yet
    return { status: 'not-completed', course: null };
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'future':
        return <AlertCircle className="h-5 w-5 text-gray-400" />;
      case 'not-completed':
        return <XCircle className="h-5 w-5 text-red-400" />;
      default:
        return null;
    }
  };

  const getStatusText = (status: string, course: CourseEnrollment | null) => {
    switch (status) {
      case 'completed':
        return <span className="text-green-600 font-medium">이수완료</span>;
      case 'future':
        return <span className="text-gray-500">미개설</span>;
      case 'not-completed':
        return <span className="text-red-600">미이수</span>;
      default:
        return null;
    }
  };

  const getCourseTypeBadgeColor = (type: string) => {
    const colors: Record<string, string> = {
      '전공기초': 'bg-blue-100 text-blue-800',
      '전공핵심': 'bg-purple-100 text-purple-800',
      '전공심화': 'bg-indigo-100 text-indigo-800',
      '전공선택': 'bg-green-100 text-green-800',
      '교양필수': 'bg-yellow-100 text-yellow-800',
      '교양선택': 'bg-gray-100 text-gray-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  // Filter courses based on selected filter
  const filteredCourses = courseFilter === 'all' 
    ? courses 
    : courses.filter(c => c.completion_type === courseFilter);

  if (loading) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen flex items-center justify-center">
        <div className="text-gray-600">데이터를 불러오는 중...</div>
      </div>
    );
  }

  if (!showDetail) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">학생 관리</h1>
            <p className="text-gray-600">학생 검색 및 관리를 할 수 있습니다.</p>
          </div>
          <button
            onClick={downloadCSV}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            <Download className="h-4 w-4" />
            CSV 다운로드
          </button>
        </div>

        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-bold text-gray-900">전체 학생 리스트</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">이름</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">학번</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">학과</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">Pride</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">분반</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">최신 희망 학과</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">전공결정도</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">이수현황</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">수강과목 적합성</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {[...students].sort((a, b) => a.name.localeCompare(b.name, 'ko-KR')).map((s) => (
                  <tr
                    key={s.student_id}
                    onClick={() => {
                      setSelectedStudent(s.student_id);
                      setShowDetail(true);
                    }}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-6 py-6 whitespace-nowrap text-sm font-medium text-blue-600 hover:underline">
                      {s.name}
                    </td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{s.student_id}</td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{s.department.name}</td>
                    <td className="px-6 py-6 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                        {s.academic_info.pride}
                      </span>
                    </td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{s.academic_info.class_number}</td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-500">-</td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-500">-</td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-500">-</td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-500">-</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* 헤더 */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">{student?.name}</h1>
          <div className="flex items-center gap-4 text-gray-600">
            <span>학번: {student?.student_id}</span>
            <span>•</span>
            <span>1학년</span>
            <span>•</span>
            <span>{student?.department.name}</span>
          </div>
        </div>
        <button
          onClick={() => setShowDetail(false)}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          목록으로
        </button>
      </div>

      {/* 탭 메뉴 */}
      <div className="bg-white rounded-lg shadow-sm mb-8">
        <div className="border-b border-gray-200">
          <nav className="flex">
            <button
              onClick={() => setActiveTab('survey')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'survey'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
            >
              희망 전공 조사 결과
            </button>
            <button
              onClick={() => setActiveTab('entry')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'entry'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
            >
              희망 전공 진입
            </button>
            <button
              onClick={() => setActiveTab('courses')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'courses'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
            >
              수강 과목 리스트
            </button>
          </nav>
        </div>
      </div>

      {/* 탭 내용 */}
      {activeTab === 'survey' && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">희망 전공 조사 결과</h2>
          {surveys.length > 0 ? (
            <div className="space-y-4">
              {surveys.map((survey) => (
                <div key={survey.survey_id} className="border-b pb-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">{survey.round}차 조사 ({survey.submitted_at})</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-gray-700">1지망</span>
                      <span className="text-sm text-gray-900">{survey.first_choice.name}</span>
                    </div>
                    {survey.second_choice && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium text-gray-700">2지망</span>
                        <span className="text-sm text-gray-900">{survey.second_choice.name}</span>
                      </div>
                    )}
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-gray-700">결정 확신도</span>
                      <span className="text-sm text-gray-900">{survey.decision_scale}/5</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">조사 결과가 없습니다.</p>
          )}
        </div>
      )}

      {activeTab === 'entry' && (
        <div className="space-y-6">
          {/* 학과 선택 및 적합도 요약 */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">분석할 학과 선택</h2>
            <div className="flex gap-3 items-start">
              {/* 단과대 선택 */}
              <div className="flex-shrink-0">
                <label className="block mb-2 text-sm font-medium text-gray-700">단과대학</label>
                <select
                  value={selectedCollege}
                  onChange={(e) => {
                    setSelectedCollege(Number(e.target.value));
                    setPathwayDept(null);
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {colleges.filter(college => college.id !== 1).map((college) => (
                    <option key={college.id} value={college.id}>
                      {college.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* 학과 선택 */}
              {selectedCollege > 0 && (
                <div className="flex-shrink-0">
                  <label className="block mb-2 text-sm font-medium text-gray-700">학과</label>
                  <select
                    value={pathwayDept || ''}
                    onChange={(e) => setPathwayDept(Number(e.target.value))}
                    className="px-4 py-2 border-2 border-blue-300 bg-blue-50/50 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">학과를 선택하세요</option>
                    {departments
                      .filter(d => {
                        const deptCollegeId = Math.floor(d.id / 100);
                        return deptCollegeId === selectedCollege;
                      })
                      .map((dept) => (
                        <option key={dept.id} value={dept.id}>
                          {dept.name}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              {/* 적합도 요약 카드들 */}
              {pathwayDept && pathwayAnalysis && (
                <div className="flex gap-3 flex-1 ml-4">
                  {/* 전공진입 필수 */}
                  <div className="flex-1 p-4 rounded-lg border bg-gradient-to-br from-gray-50 to-gray-100 border-gray-300">
                    <div className="text-sm font-medium text-gray-900 mb-1">전공진입 필수</div>
                    <div className="text-2xl font-bold text-gray-700 mb-1">
                      {Math.round(pathwayAnalysis.requiredCompletionRate)}%
                    </div>
                    <div className="text-xs text-gray-600 mb-2">
                      {pathwayAnalysis.completedRequired} / {pathwayAnalysis.requiredCourses.length} 과목
                    </div>
                    <div className="w-full rounded-full h-2 bg-gray-200">
                      <div
                        className="h-2 rounded-full bg-gray-600"
                        style={{ width: `${pathwayAnalysis.requiredCompletionRate}%` }}
                      />
                    </div>
                  </div>

                  {/* 권장과목 */}
                  <div className="flex-1 p-4 rounded-lg border bg-gradient-to-br from-gray-50 to-gray-100 border-gray-300">
                    <div className="text-sm font-medium text-gray-900 mb-1">권장과목</div>
                    <div className="text-2xl font-bold text-gray-700 mb-1">
                      {Math.round(pathwayAnalysis.recommendedCompletionRate)}%
                    </div>
                    <div className="text-xs text-gray-600 mb-2">
                      {pathwayAnalysis.completedRecommended} / {pathwayAnalysis.recommendedCourses.length} 과목
                    </div>
                    <div className="w-full rounded-full h-2 bg-gray-200">
                      <div
                        className="h-2 rounded-full bg-gray-600"
                        style={{ width: `${pathwayAnalysis.recommendedCompletionRate}%` }}
                      />
                    </div>
                  </div>

                  {/* 전체 적합도 */}
                  <div className="flex-1 p-4 rounded-lg border bg-gradient-to-br from-gray-50 to-gray-100 border-gray-300">
                    <div className="text-sm font-medium text-gray-900 mb-1">전체 적합도</div>
                    <div className="text-2xl font-bold text-gray-700 mb-1">
                      {Math.round(pathwayAnalysis.overallRate)}%
                    </div>
                    <div className="text-xs text-gray-600 mb-2">
                      종합 진입 준비도
                    </div>
                    <div className="w-full rounded-full h-2 bg-gray-200">
                      <div
                        className="h-2 rounded-full bg-gray-600"
                        style={{ width: `${pathwayAnalysis.overallRate}%` }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 현황 메시지 */}
          {pathwayDept && pathwayAnalysis && (
            <div className="bg-blue-100 border-2 border-blue-500 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-6 w-6 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-blue-900 font-semibold text-lg">
                  {getStatusMessage()}
                </p>
              </div>
            </div>
          )}

          {/* 과목 구분 안내 */}
          {pathwayDept && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <p className="text-amber-900 text-sm">
                  과목 구분은 현재 소속인 라이언스 칼리지 기준으로 구분된 정보이며,
                  향후 전공 진입에 따라 바뀔 수 있음을 유의하십시오.
                </p>
              </div>
            </div>
          )}

          {/* 소프트웨어융합대학 > 컴퓨터학부 선택 시 전체 교육과정 및 이수 현황 표시 */}
          {pathwayDept && selectedCollege === 3 && pathwayDept === 301 && (
            <div className="space-y-6">
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg px-6 py-4">
                <h2 className="text-xl font-bold text-white">전체 교육과정 및 이수 현황</h2>
                <p className="text-blue-100 text-sm mt-1">4개년 전체 교육과정과 학생의 이수 현황을 확인할 수 있습니다</p>
              </div>

              {loadingCurriculum ? (
                <div className="bg-white rounded-lg shadow-sm p-8 text-center">
                  <div className="text-gray-600">교육과정을 불러오는 중...</div>
                </div>
              ) : curriculum ? (
                <>
                  {/* 학년별 교육과정 및 수강 현황 */}
                  {['1학년', '2학년', '3학년', '4학년'].map((yearLabel) => {
                    const yearData = curriculum.curriculum[yearLabel];

                    if (!yearData) return null;

                    return (
                      <div key={yearLabel} className="bg-white rounded-lg shadow-sm overflow-hidden">
                        <div className="bg-gradient-to-r from-gray-100 to-gray-200 px-6 py-4 border-b">
                          <h3 className="text-lg font-bold text-gray-900">{yearLabel} 교육과정</h3>
                          <p className="text-sm text-gray-600 mt-1">컴퓨터학부 {yearLabel} 과정</p>
                        </div>

                        {/* 학기별로 표시 */}
                        <div className="p-6 space-y-6">
                          {['1학기', '2학기'].map((semesterLabel) => {
                            const semesterCourses = yearData[semesterLabel] || [];

                            if (semesterCourses.length === 0) return null;

                            return (
                              <div key={semesterLabel}>
                                <h4 className="text-md font-semibold text-gray-800 mb-3 bg-gray-50 px-4 py-2 rounded">
                                  {semesterLabel}
                                </h4>
                                <div className="overflow-x-auto">
                                  <table className="w-full table-fixed">
                                    <thead className="bg-gray-50 border-b-2 border-gray-200">
                                      <tr>
                                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase w-28">과목코드</th>
                                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase w-64">과목명</th>
                                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase w-24">이수구분</th>
                                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase w-20">학점</th>
                                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase w-24">진입요건</th>
                                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase w-28">이수현황</th>
                                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase w-40">비고</th>
                                      </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                      {semesterCourses.map((course: any) => {
                                        const status = checkCourseStatus(course, courses);
                                        return (
                                          <tr key={course.course_id} className="hover:bg-gray-50">
                                            <td className="px-4 py-3 text-center align-middle text-sm font-medium text-gray-900 w-28">
                                              {course.course_code}
                                            </td>
                                            <td className="px-4 py-3 text-center align-middle text-sm text-gray-900 w-64">
                                              {course.course_name}
                                            </td>
                                            <td className="px-4 py-3 text-center align-middle w-24">
                                              <span className={`px-2 py-1 text-xs font-medium rounded ${getCourseTypeBadgeColor(course.course_type)}`}>
                                                {course.course_type}
                                              </span>
                                            </td>
                                            <td className="px-4 py-3 text-center align-middle text-sm text-gray-900 w-20">
                                              {course.credits}
                                            </td>
                                            <td className="px-4 py-3 text-center align-middle w-24">
                                              {course.is_entry_requirement ? (
                                                <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded">
                                                  필수
                                                </span>
                                              ) : (
                                                <span className="text-gray-400">-</span>
                                              )}
                                            </td>
                                            <td className="px-4 py-3 text-center align-middle w-28">
                                              <div className="flex items-center justify-center gap-2">
                                                {getStatusIcon(status.status)}
                                                {getStatusText(status.status, status.course)}
                                              </div>
                                            </td>
                                            <td className="px-4 py-3 text-center align-middle text-sm text-gray-500 w-40">
                                              {status.status === 'future' && (
                                                <span>{yearLabel} 과정</span>
                                              )}
                                              {status.status === 'completed' && status.course && (
                                                <span className="text-green-600">
                                                  {status.course.year}-{status.course.semester} 이수
                                                </span>
                                              )}
                                              {course.is_recommended && (
                                                <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs font-medium rounded ml-1">
                                                  추천
                                                </span>
                                              )}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </>
              ) : null}
            </div>
          )}
        </div>
      )}

      {activeTab === 'courses' && (
        <div className="space-y-6">
          {/* 학점 통계 카드 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">총 취득학점</h3>
              <div className="text-3xl font-bold text-gray-900">{totalCredits}학점</div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">평균학점</h3>
              <div className="text-3xl font-bold text-gray-900">-</div>
              <p className="text-sm text-gray-500 mt-1">총 {courses.length}과목 이수</p>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">희망 전공</h3>
              <div className="text-2xl font-bold text-gray-900">
                {surveys.length > 0 ? surveys[0].first_choice.name : '미제출'}
              </div>
            </div>
          </div>

          {/* 수강 과목 테이블 */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-gray-900">수강 과목 목록</h2>
                <p className="text-sm text-gray-500 mt-1">
                  {courseFilter === 'all' ? '전체' : courseFilter} 과목 {filteredCourses.length}개
                </p>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700">필터:</label>
                <select
                  value={courseFilter}
                  onChange={(e) => setCourseFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                >
                  <option value="all">전체 과목</option>
                  <option value="전공기초">전공기초</option>
                  <option value="전공핵심">전공핵심</option>
                  <option value="전공심화">전공심화</option>
                  <option value="전공선택">전공선택</option>
                  <option value="교양필수">교양필수</option>
                  <option value="교양선택">교양선택</option>
                </select>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">년도</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">학기</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">과목코드</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">과목명</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">학점</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">성적</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">이수구분</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredCourses.map((course) => (
                    <tr key={course.course_id} className="hover:bg-gray-50">
                      <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">
                        {course.year}
                      </td>
                      <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">
                        {course.semester}
                      </td>
                      <td className="px-6 py-6 whitespace-nowrap text-sm font-medium text-gray-600">
                        {course.course_code}
                      </td>
                      <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">
                        {course.course_name}
                      </td>
                      <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">
                        {course.credits}
                      </td>
                      <td className="px-6 py-6 whitespace-nowrap text-sm font-semibold text-gray-900">
                        -
                      </td>
                      <td className="px-6 py-6 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          course.completion_type === '전공기초' ? 'bg-blue-100 text-blue-800' :
                          course.completion_type === '전공핵심' ? 'bg-green-100 text-green-800' :
                          course.completion_type === '전공심화' ? 'bg-purple-100 text-purple-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {course.completion_type}
                        </span>
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
  );
}
