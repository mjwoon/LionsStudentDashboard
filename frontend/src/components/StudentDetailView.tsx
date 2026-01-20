import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { ChevronLeft, Download, CheckCircle2, AlertCircle, XCircle, Circle } from 'lucide-react';

// 단과대학 및 학과 데이터
const colleges = [
  { id: 'engineering', name: '공과대학', color: 'blue' },
  { id: 'natural', name: '자연과학대학', color: 'green' },
  { id: 'business', name: '경영대학', color: 'purple' },
  { id: 'humanities', name: '인문대학', color: 'orange' },
];

const departmentsByCollege: Record<string, any[]> = {
  engineering: [
    { id: 'cs', name: '컴퓨터공학과', college: 'engineering' },
    { id: 'ee', name: '전자공학과', college: 'engineering' },
    { id: 'me', name: '기계공학과', college: 'engineering' },
  ],
  natural: [
    { id: 'math', name: '수학과', college: 'natural' },
    { id: 'physics', name: '물리학과', college: 'natural' },
    { id: 'chem', name: '화학과', college: 'natural' },
    { id: 'bio', name: '생명과학과', college: 'natural' },
  ],
  business: [
    { id: 'biz', name: '경영학과', college: 'business' },
    { id: 'econ', name: '경제학과', college: 'business' },
  ],
  humanities: [
    { id: 'korean', name: '국어국문학과', college: 'humanities' },
    { id: 'english', name: '영어영문학과', college: 'humanities' },
    { id: 'history', name: '사학과', college: 'humanities' },
  ],
};

// 학과별 교육과정 데이터
const departmentCurriculum: Record<string, any> = {
  cs: {
    name: '컴퓨터공학과',
    curriculum: [
      { grade: 1, semester: 1, code: 'CS101', name: '프로그래밍 기초', type: '전공진입', credits: 3, equivalents: ['SW101', 'PROG101'] },
      { grade: 1, semester: 1, code: 'MATH101', name: '미적분학 I', type: '전공진입', credits: 3, equivalents: [] },
      { grade: 1, semester: 2, code: 'MATH102', name: '미적분학 II', type: '전공진입', credits: 3, equivalents: [] },
      { grade: 2, semester: 1, code: 'CS201', name: '자료구조', type: '전공진입', credits: 3, equivalents: ['SW201', 'DS101'] },
      { grade: 2, semester: 1, code: 'MATH201', name: '선형대수학', type: '전공진입', credits: 3, equivalents: ['LA101'] },
      { grade: 2, semester: 2, code: 'CS202', name: '알고리즘', type: '전공진입', credits: 3, equivalents: ['SW301', 'ALG101'] },
      { grade: 2, semester: 2, code: 'STAT201', name: '확률과 통계', type: '권장과목', credits: 3, equivalents: [] },
    ],
  },
  math: {
    name: '수학과',
    curriculum: [
      { grade: 1, semester: 1, code: 'MATH101', name: '미적분학 I', type: '전공진입', credits: 3, equivalents: [] },
      { grade: 1, semester: 1, code: 'MATH103', name: '선형대수학 I', type: '전공진입', credits: 3, equivalents: ['MATH201'] },
      { grade: 1, semester: 2, code: 'MATH102', name: '미적분학 II', type: '전공진입', credits: 3, equivalents: [] },
      { grade: 2, semester: 1, code: 'MATH205', name: '해석학 I', type: '전공진입', credits: 3, equivalents: [] },
      { grade: 2, semester: 2, code: 'MATH207', name: '해석학 II', type: '전공진입', credits: 3, equivalents: [] },
    ],
  },
};

// 학생 데이터
interface Student {
  id: string;
  name: string;
  grade: number;
  major: string;
  firstChoice: string;
  pride: string;
  class: number;
}

const students: Student[] = [
  { id: '202301234', name: '홍길동', grade: 2, major: '이공계열', firstChoice: '컴퓨터공학과', pride: 'L', class: 3 },
  { id: '20210001', name: '김민수', grade: 3, major: '이공계열', firstChoice: '컴퓨터공학과', pride: 'I', class: 7 },
  { id: '20210045', name: '이서연', grade: 3, major: '이공계열', firstChoice: '컴퓨터공학과', pride: 'O', class: 2 },
  { id: '20220012', name: '박지훈', grade: 2, major: '전계열', firstChoice: '컴퓨터공학과', pride: 'N', class: 5 },
  { id: '20220078', name: '최예진', grade: 2, major: '이공계열', firstChoice: '컴퓨터공학과', pride: 'S', class: 9 },
];

// 과목 데이터
interface Course {
  year: string;
  semester: string;
  name: string;
  credits: number;
  grade: string;
  category: string;
}

const coursesByStudent: Record<string, Course[]> = {
  '202301234': [
    { year: '2023', semester: '1학기', name: '프로그래밍 기초', credits: 3, grade: 'A+', category: '전공필수' },
    { year: '2023', semester: '1학기', name: '미적분학 I', credits: 3, grade: 'A0', category: '기초교양' },
    { year: '2023', semester: '2학기', name: '자료구조', credits: 3, grade: 'A+', category: '전공필수' },
    { year: '2024', semester: '1학기', name: '알고리즘', credits: 3, grade: 'A0', category: '전공필수' },
  ],
};

// 과목에 코드 추가
interface CourseWithCode extends Course {
  code?: string;
}

const courseData: Record<string, CourseWithCode[]> = {
  '202301234': [
    { year: '2023', semester: '1학기', code: 'SW101', name: '프로그래밍 기초', credits: 3, grade: 'A+', category: '전공필수' },
    { year: '2023', semester: '1학기', code: 'MATH101', name: '미적분학 I', credits: 3, grade: 'A0', category: '기초교양' },
    { year: '2023', semester: '2학기', code: 'SW201', name: '자료구조', credits: 3, grade: 'A+', category: '전공필수' },
    { year: '2024', semester: '1학기', code: 'SW301', name: '알고리즘', credits: 3, grade: 'A0', category: '전공필수' },
  ],
};

// 학과별 색상
const deptColors: Record<string, string> = {
  '컴퓨터공학과': '#3b82f6',
  '전자공학과': '#10b981',
  '수학과': '#06b6d4',
  '경영학과': '#f59e0b',
};

export default function StudentDetailView() {
  const [selectedStudent, setSelectedStudent] = useState<string>('');
  const [showDetail, setShowDetail] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'survey' | 'entry' | 'courses'>('survey');
  const [selectedCollege, setSelectedCollege] = useState<string>('engineering');
  const [pathwayDept, setPathwayDept] = useState<string>('');

  const student = students.find((s) => s.id === selectedStudent);
  const courses = courseData[selectedStudent] || [];

  // 학점 통계
  const totalCredits = courses.reduce((sum, c) => sum + c.credits, 0);
  const gradePoints = courses.map((c) => {
    if (c.grade.includes('A+')) return 4.5;
    if (c.grade.includes('A')) return 4.0;
    if (c.grade.includes('B+')) return 3.5;
    if (c.grade.includes('B')) return 3.0;
    return 2.5;
  });
  const averageGrade = gradePoints.length > 0
    ? (gradePoints.reduce((a, b) => a + b, 0) / gradePoints.length).toFixed(2)
    : '0.00';

  // 카테고리별 과목 수
  const categoryData = [
    { name: '전공필수', value: courses.filter((c) => c.category === '전공필수').length, color: '#3b82f6' },
    { name: '전공선택', value: courses.filter((c) => c.category === '전공선택').length, color: '#10b981' },
    { name: '기초교양', value: courses.filter((c) => c.category === '기초교양').length, color: '#f59e0b' },
    { name: '교양필수', value: courses.filter((c) => c.category === '교양필수').length, color: '#ef4444' },
  ].filter((d) => d.value > 0);

  // 학기별 평균 학점 데이터 (예시)
  const semesterData = [
    { semester: '2023-1', gpa: 4.25 },
    { semester: '2023-2', gpa: 4.5 },
    { semester: '2024-1', gpa: 3.75 },
  ];

  const downloadCSV = () => {
    const csv = [
      ['학생명', '학번', '학년', '전공', '희망학과', 'Pride', '분반'],
      ...(showDetail && student 
        ? [[student.name, student.id, student.grade, student.major, student.firstChoice, student.pride, student.class]]
        : students.map((s) => [s.name, s.id, s.grade, s.major, s.firstChoice, s.pride, s.class]))
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
  const checkCourseStatus = (curriculumCourse: any, studentCourses: any[]) => {
    const exactMatch = studentCourses.find((c) => c.code === curriculumCourse.code);
    if (exactMatch) {
      return { status: 'completed', course: exactMatch };
    }

    const equivalentMatch = studentCourses.find((c) =>
      curriculumCourse.equivalents.includes(c.code),
    );
    if (equivalentMatch) {
      return { status: 'equivalent', course: equivalentMatch };
    }

    const currentGrade = student?.grade || 1;
    if (curriculumCourse.grade > currentGrade) {
      return { status: 'future', course: null };
    }

    return { status: 'missing', course: null };
  };

  const getPathwayAnalysis = () => {
    const deptCurriculum = departmentCurriculum[pathwayDept];
    if (!deptCurriculum) return null;

    const { curriculum } = deptCurriculum;
    const currentGrade = student?.grade || 1;

    const requiredCourses = curriculum.filter(
      (c: any) => c.type === '전공진입' && c.grade <= currentGrade,
    );
    const completedRequired = requiredCourses.filter((c: any) => {
      const status = checkCourseStatus(c, courses);
      return status.status === 'completed' || status.status === 'equivalent';
    }).length;

    const recommendedCourses = curriculum.filter(
      (c: any) => c.type === '권장과목' && c.grade <= currentGrade,
    );
    const completedRecommended = recommendedCourses.filter((c: any) => {
      const status = checkCourseStatus(c, courses);
      return status.status === 'completed' || status.status === 'equivalent';
    }).length;

    const requiredCompletionRate =
      requiredCourses.length > 0 ? (completedRequired / requiredCourses.length) * 100 : 0;

    const recommendedCompletionRate =
      recommendedCourses.length > 0 ? (completedRecommended / recommendedCourses.length) * 100 : 0;

    const overallRate =
      ((completedRequired + completedRecommended) /
        (requiredCourses.length + recommendedCourses.length)) * 100;

    return {
      requiredCourses,
      completedRequired,
      requiredCompletionRate,
      recommendedCourses,
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'equivalent':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      case 'missing':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'future':
        return <Circle className="h-5 w-5 text-gray-400" />;
      default:
        return null;
    }
  };

  const getStatusText = (status: string, course: any) => {
    switch (status) {
      case 'completed':
        return <span className="text-green-600">수강완료</span>;
      case 'equivalent':
        return <span className="text-yellow-600">유사과목 이수 ({course.name})</span>;
      case 'missing':
        return <span className="text-red-600">미이수</span>;
      case 'future':
        return <span className="text-gray-400">향후 개설</span>;
      default:
        return null;
    }
  };

  const getCollegeColor = (collegeId: string) => {
    const college = colleges.find(c => c.id === collegeId);
    return college?.color || 'blue';
  };

  const currentCollegeColor = getCollegeColor(selectedCollege);

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
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">학년</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">전공</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">희망학과</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">Pride</th>
                  <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">분반</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {students.map((s) => (
                  <tr
                    key={s.id}
                    onClick={() => {
                      setSelectedStudent(s.id);
                      setShowDetail(true);
                    }}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-6 py-6 whitespace-nowrap text-sm font-medium text-blue-600 hover:underline">
                      {s.name}
                    </td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{s.id}</td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{s.grade}학년</td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{s.major}</td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{s.firstChoice}</td>
                    <td className="px-6 py-6 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                        {s.pride}
                      </span>
                    </td>
                    <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{s.class}반</td>
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
            <span>학번: {student?.id}</span>
            <span>•</span>
            <span>{student?.grade}학년</span>
            <span>•</span>
            <span>{student?.major}</span>
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

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">총 취득학점</h3>
          <div className="text-3xl font-bold text-gray-900">{totalCredits}학점</div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">평균 학점</h3>
          <div className="text-3xl font-bold text-gray-900">{averageGrade}</div>
          <p className="text-sm text-gray-500 mt-1">총 {courses.length}과목</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">희망 전공</h3>
          <div className="text-2xl font-bold text-gray-900">{student?.firstChoice}</div>
        </div>
      </div>

      {/* 탭 메뉴 */}
      <div className="bg-white rounded-lg shadow-sm mb-8">
        <div className="border-b border-gray-200">
          <nav className="flex">
            <button
              onClick={() => setActiveTab('survey')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'survey'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              희망 전공 조사 결과
            </button>
            <button
              onClick={() => setActiveTab('entry')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'entry'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              희망 전공 진입
            </button>
            <button
              onClick={() => setActiveTab('courses')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'courses'
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
          <div className="space-y-4">
            <div className="flex justify-between items-center py-3 border-b">
              <span className="text-sm font-medium text-gray-700">1지망</span>
              <span className="text-sm text-gray-900">{student?.firstChoice}</span>
            </div>
            <div className="flex justify-between items-center py-3 border-b">
              <span className="text-sm font-medium text-gray-700">Pride 구분</span>
              <span className="px-3 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                {student?.pride}
              </span>
            </div>
            <div className="flex justify-between items-center py-3 border-b">
              <span className="text-sm font-medium text-gray-700">분반</span>
              <span className="text-sm text-gray-900">{student?.class}반</span>
            </div>
          </div>
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
                    setSelectedCollege(e.target.value);
                    const firstDept = departmentsByCollege[e.target.value]?.[0];
                    if (firstDept) {
                      setPathwayDept(firstDept.id);
                    }
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {colleges.map((college) => (
                    <option key={college.id} value={college.id}>
                      {college.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* 학과 선택 */}
              {selectedCollege && (
                <div className="flex-shrink-0">
                  <label className="block mb-2 text-sm font-medium text-gray-700">학과</label>
                  <select
                    value={pathwayDept}
                    onChange={(e) => setPathwayDept(e.target.value)}
                    className="px-4 py-2 border-2 border-blue-300 bg-blue-50/50 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">학과를 선택하세요</option>
                    {(departmentsByCollege[selectedCollege] || []).map((dept) => (
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

          {/* 학년별 교육과정 및 수강 현황 */}
          {pathwayDept && departmentCurriculum[pathwayDept] && [1, 2, 3, 4].map((gradeNum) => {
            const gradeCourses = departmentCurriculum[pathwayDept]?.curriculum.filter(
              (c: any) => c.grade === gradeNum,
            ) || [];

            if (gradeCourses.length === 0) return null;

            return (
              <div key={gradeNum} className="bg-white rounded-lg shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-bold text-gray-900">
                    {gradeNum}학년 교육과정
                  </h2>
                  <p className="text-sm text-gray-500 mt-1">
                    {departmentCurriculum[pathwayDept]?.name} {gradeNum}학년 과정
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">학기</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">과목명</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">구분</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">학점</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">이수현황</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">비고</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {gradeCourses.map((course: any) => {
                        const status = checkCourseStatus(course, courses);
                        return (
                          <tr key={course.code} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {course.semester}학기
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {course.name}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                                course.type === '전공진입'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-blue-100 text-blue-800'
                              }`}>
                                {course.type}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {course.credits}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center gap-2">
                                {getStatusIcon(status.status)}
                                {getStatusText(status.status, status.course)}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {status.status === 'equivalent' && status.course && (
                                <span>동등과목 인정</span>
                              )}
                              {status.status === 'future' && (
                                <span>{gradeNum}학년 과정</span>
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
      )}

      {activeTab === 'courses' && (
        <>
          {/* 차트 영역 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* 카테고리별 과목 수 */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">과목 카테고리별 분포</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={categoryData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" name="과목 수">
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* 학기별 GPA 추이 */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">학기별 평균 학점</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={semesterData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="semester" />
                  <YAxis domain={[0, 4.5]} />
                  <Tooltip />
                  <Bar dataKey="gpa" fill="#3b82f6" name="GPA" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 수강 과목 테이블 */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-bold text-gray-900">수강 과목 목록</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">년도</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">학기</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">과목명</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">학점</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">등급</th>
                    <th className="px-6 py-5 text-left text-xs font-medium text-gray-500 uppercase">구분</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {courses.map((course, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{course.year}</td>
                      <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{course.semester}</td>
                      <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{course.name}</td>
                      <td className="px-6 py-6 whitespace-nowrap text-sm text-gray-900">{course.credits}</td>
                      <td className="px-6 py-6 whitespace-nowrap">
                        <span className={`text-sm font-semibold ${
                          course.grade.startsWith('A') ? 'text-green-600' :
                          course.grade.startsWith('B') ? 'text-blue-600' :
                          'text-yellow-600'
                        }`}>
                          {course.grade}
                        </span>
                      </td>
                      <td className="px-6 py-6 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          course.category === '전공필수' ? 'bg-blue-100 text-blue-800' :
                          course.category === '전공선택' ? 'bg-green-100 text-green-800' :
                          course.category === '기초교양' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-orange-100 text-orange-800'
                        }`}>
                          {course.category}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
