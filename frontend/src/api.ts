// API 기본 설정
// Docker 환경에서는 호스트의 백엔드 포트(8080)를 직접 사용
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080'

// API 요청 헬퍼 함수
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred')
  }
}

// API 엔드포인트 함수들
export const api = {
  // 학생 관련 API
  students: {
    list: (page = 1, perPage = 10, filters?: {
      department_id?: number
      pride?: string
      class_number?: number
      status?: string
    }) => {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
        ...(filters?.department_id && { department_id: filters.department_id.toString() }),
        ...(filters?.pride && { pride: filters.pride }),
        ...(filters?.class_number && { class_number: filters.class_number.toString() }),
        ...(filters?.status && { status: filters.status }),
      })
      return fetchAPI<StudentsResponse>(`/api/students?${params}`)
    },
    
    get: (studentId: string) => 
      fetchAPI<StudentDetail>(`/api/students/${studentId}`),
    
    courses: (studentId: string) => 
      fetchAPI<StudentCoursesResponse>(`/api/students/${studentId}/courses`),
    
    surveys: (studentId: string) => 
      fetchAPI<StudentSurveysResponse>(`/api/students/${studentId}/surveys`),
    
    create: (data: StudentCreate) => 
      fetchAPI<StudentCreateResponse>('/api/students', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  // 학과 관련 API
  departments: {
    list: () => 
      fetchAPI<DepartmentsResponse>('/api/departments'),
    
    courses: (departmentId: number, page = 1, perPage = 20) => {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      })
      return fetchAPI<CoursesResponse>(`/api/departments/${departmentId}/courses?${params}`)
    },
    
    curriculum: (departmentId: number) => 
      fetchAPI<DepartmentCurriculum>(`/api/departments/${departmentId}/curriculum`),
  },

  // 평가 관련 API
  evaluation: {
    getStudentEvaluation: (studentId: string, departmentId: number, forceRecalculate = false) => {
      const params = new URLSearchParams()
      if (forceRecalculate) {
        params.append('force_recalculate', 'true')
      }
      return fetchAPI<EvaluationResult>(
        `/api/evaluation/student/${studentId}/department/${departmentId}${params.toString() ? '?' + params : ''}`
      )
    },
  },

  // 과목 관련 API
  courses: {
    list: (page = 1, perPage = 20, filters?: {
      course_type?: string
      department_id?: number
      is_entry_requirement?: boolean
    }) => {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
        ...(filters?.course_type && { course_type: filters.course_type }),
        ...(filters?.department_id && { department_id: filters.department_id.toString() }),
        ...(filters?.is_entry_requirement !== undefined && { 
          is_entry_requirement: filters.is_entry_requirement.toString() 
        }),
      })
      return fetchAPI<CoursesResponse>(`/api/courses?${params}`)
    },
    
    entryRequirements: () => 
      fetchAPI<EntryRequirementsResponse>('/api/courses/entry-requirements'),
  },

  // 설문 관련 API
  surveys: {
    summary: () => 
      fetchAPI<SurveySummaryResponse>('/api/surveys/summary'),
    
    submit: (data: SurveySubmit) => 
      fetchAPI<SurveySubmitResponse>('/api/surveys', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    
    getRound: (roundId: number, page = 1, limit = 20) => {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      })
      return fetchAPI<SurveyRoundResponse>(`/api/major-surveys/rounds/${roundId}?${params}`)
    },
  },

  // 대시보드 관련 API
  dashboard: {
    stats: () => 
      fetchAPI<DashboardStatsResponse>('/api/dashboard/stats'),
  },
}

// 타입 정의
export interface StudentsResponse {
  count: number
  page: number
  per_page: number
  students: Student[]
}

export interface Student {
  student_id: string
  name: string
  email: string
  phone?: string
  department: {
    id: number
    name: string
  }
  academic_info: {
    pride: string
    class_number: number
    advisor_name?: string
    status: string
  }
}

export interface StudentDetail extends Student {
  academic_info: Student['academic_info'] & {
    advisor_id?: number
    updated_at?: string
  }
}

export interface StudentCoursesResponse {
  student_id: string
  total_credits: number
  course_history: CourseEnrollment[]
}

export interface CourseEnrollment {
  course_id: number
  course_code: string
  course_name: string
  credits: number
  year: number
  semester: number
  completion_type: string
  is_entry_requirement: boolean
  is_retake: boolean
}

export interface StudentSurveysResponse {
  history: SurveyHistory[]
}

export interface SurveyHistory {
  survey_id: number
  round: number
  submitted_at: string
  first_choice: { id: number; name: string }
  second_choice?: { id: number; name: string }
  decision_scale: number
}

export interface StudentCreate {
  student_id: string
  name: string
  email: string
  phone?: string
  department_id: number
  advisor_id?: number
  pride: string
  class_number: number
}

export interface StudentCreateResponse {
  message: string
  student_id: string
}

export interface DepartmentsResponse {
  count: number
  departments: Department[]
}

export interface Department {
  id: number
  code: string
  name: string
  college_name: string
  min_credits: number
  homepage_url?: string
}

export interface DepartmentCurriculum {
  department_name: string
  graduation_min_credits: number
  tracks: string[]
  entry_requirements_description: string
}

export interface CoursesResponse {
  count: number
  page: number
  per_page: number
  courses: Course[]
}

export interface Course {
  course_id: number
  course_code: string
  course_name: string
  credits: number
  course_type: string
  department: {
    id: number
    name: string
  }
  flags: {
    is_entry_requirement: boolean
    is_recommended: boolean
    is_retake_only: boolean
  }
  description?: string
}

export interface EntryRequirementsResponse {
  count: number
  courses: EntryRequirementCourse[]
}

export interface EntryRequirementCourse {
  course_id: number
  course_code: string
  course_name: string
  credits: number
  course_type: string
  department_id: number
  department_name: string
  is_recommended: boolean
}

export interface SurveySummaryResponse {
  overview: {
    total_students: number
    total_departments: number
    entry_requirement_completion_rate: number
  }
  major_preferences: {
    dept_name: string
    count: number
    avg_decision_scale: number
  }[]
  survey_status: {
    current_round: number
    participation_rate: number
  }
}

export interface SurveySubmit {
  student_id: string
  first_choice_dept_id: number
  second_choice_dept_id?: number
  survey_round: number
  decision_scale: number
}

export interface SurveySubmitResponse {
  success: boolean
  message: string
  data: {
    survey_id: number
    submitted_at: string
  }
}

export interface SurveyRoundResponse {
  meta: {
    total_count: number
    current_page: number
    total_pages: number
    per_page: number
  }
  round_info: {
    round_id: number
    title: string
    status: string
  }
  submissions: SurveySubmission[]
}

export interface SurveySubmission {
  survey_id: number
  student_id: string
  name: string
  department_name: string
  first_choice: { id: number; name: string }
  second_choice?: { id: number; name: string }
  decision_scale: number
  submitted_at: string
}

// Dashboard Types
export interface DashboardStatsResponse {
  colleges: College[]
  departments: DepartmentWithStats[]
  current_data: DepartmentWithStats[]
  trend_data: TrendDataPoint[]
}

export interface College {
  id: number
  name: string
}

export interface DepartmentWithStats {
  id: string
  name: string
  college: string
  color: string
  students: number
  percent: number
}

export interface TrendDataPoint {
  period: string
  data: Record<string, number>
}
// Evaluation Types
export interface EvaluationResult {
  student_id: number
  department_id: number
  department_name: string
  admission_year: number
  required_courses: {
    score: number
    total_requirements: number
    satisfied_requirements: number
    pass: boolean
    message: string
    details: any[]
  }
  recommended_courses: {
    score: number
    total_courses: number
    completed_courses: number
    total_credits: number
    completed_credits: number
    completion_rate: number
    message: string
    details: any[]
  }
  related_credits: {
    score: number
    total_available_credits: number
    earned_credits: number
    message: string
  }
  overall_score: number
  grade: string
  summary_message: string
  evaluated_at: string
}