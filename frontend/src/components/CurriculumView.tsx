import { useState, useEffect } from 'react';
import { BookOpen, Filter } from 'lucide-react';
import { api } from '../api';
import { getCourseTypeBadgeColor } from '../constants';
import type { Department } from '../types';

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

export default function CurriculumView() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [curriculum, setCurriculum] = useState<Curriculum>({});
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedDepartment, setSelectedDepartment] = useState<string>('');

  useEffect(() => {
    const fetchDepartments = async () => {
      try {
        const data = await api.departments.list();
        const evalDepts = data.departments.filter(d => d.is_evaluation_available);
        setDepartments(evalDepts);
        if (evalDepts.length > 0) {
          setSelectedDepartment(evalDepts[0].id);
        }
      } catch (error) {
        console.error('Failed to fetch departments:', error);
        setLoading(false);
      }
    };
    fetchDepartments();
  }, []);

  useEffect(() => {
    const fetchCurriculum = async () => {
      if (!selectedDepartment) return;
      try {
        setLoading(true);
        const data = await api.courses.curriculum(selectedDepartment);
        setCurriculum(data.curriculum);
      } catch (error) {
        console.error('Failed to fetch curriculum:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCurriculum();
  }, [selectedDepartment]);

  if (loading && departments.length === 0) {
    return (
      <div className="p-8 bg-gray-50 flex items-center justify-center min-h-screen">
        <div className="text-gray-600">데이터를 불러오는 중...</div>
      </div>
    );
  }

  const courseTypes = ['all', '전공기초', '전공핵심', '전공심화', '전공선택', '교양필수', '교양선택'];

  const filterCourses = (courses: Course[]) => {
    if (selectedType === 'all') return courses;
    return courses.filter(c => c.course_type === selectedType);
  };


  return (
    <div className="p-4 md:p-6 lg:p-8 bg-gray-50 min-h-screen">

      {/* 학과 선택 */}
      <div className="bg-white rounded-lg shadow-sm p-4 md:p-6 mb-4 md:mb-6">
        <h2 className="text-base md:text-lg font-semibold text-gray-900 mb-3 md:mb-4">교육과정 학과 선택</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 md:gap-4">
          {departments.map(dept => (
            <button
              key={dept.id}
              onClick={() => setSelectedDepartment(dept.id)}
              className={`px-2 md:px-4 py-2 md:py-3 rounded-lg text-xs md:text-sm font-medium transition-all ${selectedDepartment === dept.id
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
      <div className="bg-white rounded-lg shadow-sm p-3 md:p-4 mb-4 md:mb-6">
        <div className="flex items-center gap-2 md:gap-4">
          <Filter className="h-4 w-4 md:h-5 md:w-5 text-gray-500 shrink-0" />
          <div className="flex gap-1.5 md:gap-2 flex-wrap">
            {courseTypes.map(type => (
              <button
                key={type}
                onClick={() => setSelectedType(type)}
                className={`px-2 md:px-3 py-1 rounded-lg text-xs md:text-sm font-medium transition-colors ${selectedType === type
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
      <div className="space-y-4 md:space-y-6">
        {Object.entries(curriculum).sort(([a], [b]) => a.localeCompare(b)).map(([year, semesters]) => (
          <div key={year} className="bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="bg-linear-to-r from-blue-600 to-blue-700 px-4 md:px-6 py-3 md:py-4">
              <h2 className="text-base md:text-xl font-bold text-white flex items-center gap-2">
                <BookOpen className="h-4 w-4 md:h-5 md:w-5" />
                {year}
              </h2>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 p-4 md:p-6">
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
