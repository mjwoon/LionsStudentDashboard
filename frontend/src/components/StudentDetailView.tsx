import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { api } from '../api';
import type { Student } from './student/types';
import StudentListView from './student/StudentListView';
import StudentSurveyTab from './student/StudentSurveyTab';
import StudentEntryTab from './student/StudentEntryTab';
import StudentCoursesTab from './student/StudentCoursesTab';

type TabType = 'survey' | 'entry' | 'courses';

export default function StudentDetailView() {
  const { studentId } = useParams<{ studentId?: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('survey');

  // location.state에서 departmentId 가져오기
  useEffect(() => {
    if (location.state?.departmentId) {
      setSelectedDepartmentId(location.state.departmentId);
    }
  }, [location.state]);

  // studentId가 있으면 학생 정보 조회
  useEffect(() => {
    const fetchStudent = async () => {
      if (!studentId) {
        setSelectedStudent(null);
        return;
      }

      try {
        setLoading(true);
        const response = await api.students.list(1, 100, { search: studentId });
        const student = response.students.find((s: Student) => s.student_id === studentId);
        if (student) {
          setSelectedStudent(student);
        } else {
          setSelectedStudent(null);
          navigate('/student');
        }
      } catch (error) {
        console.error('Failed to fetch student:', error);
        navigate('/student');
      } finally {
        setLoading(false);
      }
    };

    fetchStudent();
  }, [studentId, navigate]);

  const handleStudentSelect = (student: Student, departmentId: number) => {
    setSelectedDepartmentId(departmentId);
    setActiveTab('survey');
    navigate(`/student/${student.student_id}`, { state: { departmentId } });
  };

  const handleBackToList = () => {
    navigate('/student');
  };

  // 로딩 중
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-[#6a7282]">로딩 중...</p>
      </div>
    );
  }

  // 학생 상세 정보 페이지 렌더링
  if (studentId && selectedStudent) {
    return (
      <div className="min-h-screen py-4 md:py-6">
        <div>
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-[32pt] font-bold text-[#101828] mb-4">{selectedStudent.name}</h1>
            </div>
            <button
              onClick={handleBackToList}
              className="flex items-center gap-3 px-4 py-2 bg-white border border-black/10 rounded-lg hover:bg-gray-50"
            >
              <ChevronLeft className="w-5 h-5 text-[#101828]" />
              <span className="text-lg font-medium text-[#101828]">목록으로 돌아가기</span>
            </button>
          </div>

          {/* 학생 학적 정보 */}
          <div className="mb-6">
            <p className="text-xl text-[#6a7282] font-medium">
              {selectedStudent.student_id} ⋅ {selectedStudent.academic_info.class_number}반 ⋅ {selectedStudent.department.name}
            </p>
            <p className="text-lg text-[#BBBFC8]">
              학생의 학적 및 전공 선택 정보를 확인합니다.
            </p>
          </div>

          {/* 탭 네비게이션 */}
          <div className="flex items-start gap-0 mb-6 border-b border-[#e5e7eb]">
            <button
              onClick={() => setActiveTab('survey')}
              className={`px-6 py-6 text-xl font-semibold transition-all ${activeTab === 'survey'
                ? 'text-[#0e4a84] border-b-2 border-[#0e4a84]'
                : 'text-[#6a7282]'
                }`}
            >
              희망 전공 조사 결과
            </button>
            <button
              onClick={() => setActiveTab('entry')}
              className={`px-6 py-6 text-xl font-semibold transition-all ${activeTab === 'entry'
                ? 'text-[#0e4a84] border-b-2 border-[#0e4a84]'
                : 'text-[#6a7282]'
                }`}
            >
              희망 전공 진입
            </button>
            <button
              onClick={() => setActiveTab('courses')}
              className={`px-6 py-6 text-xl font-semibold transition-all ${activeTab === 'courses'
                ? 'text-[#0e4a84] border-b-2 border-[#0e4a84]'
                : 'text-[#6a7282]'
                }`}
            >
              수강 과목 리스트
            </button>
          </div>

          {/* 탭 컨텐츠 */}
          {activeTab === 'survey' && <StudentSurveyTab student={selectedStudent} />}
          {activeTab === 'entry' && <StudentEntryTab student={selectedStudent} initialDepartmentId={selectedDepartmentId} />}
          {activeTab === 'courses' && <StudentCoursesTab student={selectedStudent} />}
        </div>
      </div>
    );
  }

  // 학생 목록 페이지
  return <StudentListView onStudentSelect={handleStudentSelect} />;
}
