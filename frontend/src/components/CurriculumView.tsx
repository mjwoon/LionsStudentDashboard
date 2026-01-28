import { useState, useEffect } from 'react';
import { BookOpen, Filter } from 'lucide-react';

interface Course {
  course_id: number;
  course_code: string;
  course_name: string;
  credits: number;
  course_type: string;
  is_entry_requirement: boolean;
  is_recommended: boolean;
  department_name: string | null;
}

interface Curriculum {
  [year: string]: {
    [semester: string]: Course[];
  };
}

interface Department {
  id: number;
  name: string;
}

// 교육과정이 있는 6개 학과
const AVAILABLE_DEPARTMENTS: Department[] = [
  { id: 300, name: '컴퓨터학부' },
  { id: 303, name: '데이터인텔리전스전공' },
  { id: 304, name: '디자인컨버전스전공' },
  { id: 200, name: '건축학전공' },
  { id: 204, name: '전자공학부' },
  { id: 207, name: '산업경영공학과' }
];

export default function CurriculumView() {
  const [curriculum, setCurriculum] = useState<Curriculum>({});
  const [totalCourses, setTotalCourses] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedDepartment, setSelectedDepartment] = useState<number>(300); // 기본값: 컴퓨터학부

  useEffect(() => {
    const fetchCurriculum = async () => {
      try {
        setLoading(true);
        console.log('Fetching curriculum for department:', selectedDepartment);
        const response = await fetch(`http://localhost:8080/api/courses/curriculum?department_id=${selectedDepartment}`);
        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);
        
        const text = await response.text();
        console.log('Raw response (first 500 chars):', text.substring(0, 500));
        
        const data = JSON.parse(text);
        console.log('Parsed data:', data);
        console.log('Curriculum keys:', Object.keys(data.curriculum || {}));
        
        setCurriculum(data.curriculum);
        setTotalCourses(data.total_courses);
      } catch (error) {
        console.error('Failed to fetch curriculum:', error);
        console.error('Error details:', error instanceof Error ? error.message : String(error));
      } finally {
        setLoading(false);
      }
    };

    fetchCurriculum();
  }, [selectedDepartment]);

  if (loading) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen flex items-center justify-center">
        <div className="text-gray-600">교육과정을 불러오는 중...</div>
      </div>
    );
  }

  const courseTypes = ['all', '전공기초', '전공핵심', '전공심화', '전공선택', '교양필수', '교양선택'];

  const filterCourses = (courses: Course[]) => {
    if (selectedType === 'all') return courses;
    return courses.filter(c => c.course_type === selectedType);
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


  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      
      {/* 학과 선택 */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">분석할 학과 선택</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {AVAILABLE_DEPARTMENTS.map(dept => (
            <button
              key={dept.id}
              onClick={() => setSelectedDepartment(dept.id)}
              className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                selectedDepartment === dept.id
                  ? 'bg-blue-600 text-white shadow-md transform scale-105'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {dept.name}
            </button>
          ))}
        </div>
      </div>

      {/* 필터 */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="flex items-center gap-4">
          <Filter className="h-5 w-5 text-gray-500" />
          <div className="flex gap-2 flex-wrap">
            {courseTypes.map(type => (
              <button
                key={type}
                onClick={() => setSelectedType(type)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  selectedType === type
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {type === 'all' ? '전체' : type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 교육과정 */}
      <div className="space-y-6">
        {Object.entries(curriculum).sort(([a], [b]) => a.localeCompare(b)).map(([year, semesters]) => (
          <div key={year} className="bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                {year}
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
              {Object.entries(semesters).sort(([a], [b]) => a.localeCompare(b)).map(([semester, courses]) => {
                const filteredCourses = filterCourses(courses);
                const totalCredits = filteredCourses.reduce((sum, c) => sum + c.credits, 0);

                return (
                  <div key={semester} className="border border-gray-200 rounded-lg">
                    <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                      <h3 className="font-semibold text-gray-900">
                        {semester}
                        <span className="ml-2 text-sm text-gray-600">
                          ({filteredCourses.length}과목, {totalCredits}학점)
                        </span>
                      </h3>
                    </div>
                    <div className="p-4">
                      <div className="space-y-3">
                        {filteredCourses.map(course => (
                          <div
                            key={course.course_id}
                            className="border border-gray-200 rounded-lg p-3 hover:shadow-md transition-shadow"
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <h4 className="font-medium text-gray-900">{course.course_name}</h4>
                                  {course.is_entry_requirement && (
                                    <span className="px-2 py-0.5 bg-red-100 text-red-800 text-xs font-medium rounded">
                                      진입요건
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm text-gray-600">{course.course_code}</p>
                              </div>
                              <div className="text-right">
                                <div className="text-sm font-semibold text-blue-600">
                                  {course.credits}학점
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-1 text-xs font-medium rounded ${getCourseTypeBadgeColor(course.course_type)}`}>
                                {course.course_type}
                              </span>
                              {course.is_recommended && (
                                <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs font-medium rounded">
                                  추천
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
