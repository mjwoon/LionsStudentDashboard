// API 기본 설정
// 개발 환경에서는 백엔드 포트(8080)를 사용
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080'

// Import only types that are used in this file
import type {
  StudentsResponse,
  StudentDetail,
  StudentCoursesResponse,
  StudentSurveysResponse,
  StudentCreate,
  StudentCreateResponse,
  DepartmentsResponse,
  DepartmentCurriculum,
  CoursesResponse,
  EntryRequirementsResponse,
  SurveySummaryResponse,
  SurveySubmit,
  SurveySubmitResponse,
  SurveyRoundResponse,
  DashboardStatsResponse,
  EvaluationResult,
  EvaluationStatistics,
  DepartmentRankings,
  UploadResponse,
  BulkEvaluationRequest,
  BulkEvaluationResponse,
  CachedEvaluationStats,
  ClearCacheResponse,
} from './types'

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
      let errorMessage = `HTTP error! status: ${response.status}`
      try {
        const errorData = await response.json()
        if (errorData.detail) {
          errorMessage = typeof errorData.detail === 'string' 
            ? errorData.detail 
            : JSON.stringify(errorData.detail)
        }
      } catch (e) {
        // JSON 파싱 실패 시 기본 메시지 사용
      }
      throw new Error(errorMessage)
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
      search?: string
    }) => {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
        ...(filters?.department_id && { department_id: filters.department_id.toString() }),
        ...(filters?.pride && { pride: filters.pride }),
        ...(filters?.class_number && { class_number: filters.class_number.toString() }),
        ...(filters?.status && { status: filters.status }),
        ...(filters?.search && { search: filters.search }),
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
    
    getStatistics: () => 
      fetchAPI<EvaluationStatistics>('/api/evaluation/statistics'),
    
    getDepartmentRankings: (departmentId: number, limit = 10) => {
      const params = new URLSearchParams({ limit: limit.toString() })
      return fetchAPI<DepartmentRankings>(`/api/evaluation/department/${departmentId}/rankings?${params}`)
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
    
    curriculum: (departmentId: number) => {
      const params = new URLSearchParams({ department_id: departmentId.toString() })
      return fetchAPI<any>(`/api/courses/curriculum?${params}`)
    },
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

  // 관리자 관련 API
  admin: {
    // 파일 업로드
    uploadCoursesFile: async (file: File): Promise<UploadResponse> => {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch(`${API_BASE}/api/admin/upload/courses/file`, {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Upload failed: ${response.status}`)
      }
      
      return await response.json()
    },

    uploadStudentsFile: async (file: File): Promise<UploadResponse> => {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch(`${API_BASE}/api/admin/upload/students/file`, {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Upload failed: ${response.status}`)
      }
      
      return await response.json()
    },

    uploadEnrollmentsFile: async (file: File): Promise<UploadResponse> => {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch(`${API_BASE}/api/admin/upload/enrollments/file`, {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Upload failed: ${response.status}`)
      }
      
      return await response.json()
    },

    // 진단 관리 (비동기)
    bulkEvaluate: (request: BulkEvaluationRequest) =>
      fetchAPI<{ job_id: string; status: string; message: string }>('/api/admin/evaluate/bulk', {
        method: 'POST',
        body: JSON.stringify(request),
      }),

    getJobStatus: (jobId: string) =>
      fetchAPI<{
        job_id: string
        status: string
        progress?: {
          current: number
          total: number
          percent: number
          status: string
          success_count?: number
          error_count?: number
        }
        result?: BulkEvaluationResponse
        error?: string
      }>(`/api/admin/evaluate/jobs/${jobId}`),

    getEvaluationStats: () =>
      fetchAPI<CachedEvaluationStats>('/api/admin/evaluate/stats'),

    clearCache: (departmentId?: number) => {
      const params = departmentId 
        ? `?department_id=${departmentId}` 
        : ''
      return fetchAPI<ClearCacheResponse>(`/api/admin/evaluate/cache${params}`, {
        method: 'DELETE',
      })
    },
  },
}


// Re-export all types for backward compatibility
export type {
  StudentsResponse,
  Student,
  StudentDetail,
  StudentCoursesResponse,
  CourseEnrollment,
  StudentSurveysResponse,
  SurveyHistory,
  StudentCreate,
  StudentCreateResponse,
  DepartmentsResponse,
  Department,
  DepartmentCurriculum,
  CoursesResponse,
  Course,
  EntryRequirementsResponse,
  EntryRequirementCourse,
  SurveySummaryResponse,
  SurveySubmit,
  SurveySubmitResponse,
  SurveyRoundResponse,
  SurveySubmission,
  DashboardStatsResponse,
  College,
  DepartmentWithStats,
  TrendDataPoint,
  EvaluationResult,
  EvaluationStatistics,
  DepartmentRankings,
  UploadResponse,
  BulkEvaluationRequest,
  BulkEvaluationResponse,
  CachedEvaluationStats,
  ClearCacheResponse,
} from './types'
