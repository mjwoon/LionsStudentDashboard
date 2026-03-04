/**
 * Type definitions for the Lions Student Dashboard API
 * 
 * This file contains all TypeScript interfaces and types used throughout
 * the frontend application for API responses and requests.
 */

// ============================================================================
// Student Types
// ============================================================================

export interface StudentsResponse {
  count: number
  page: number
  per_page: number
  students: Student[]
}

export interface Student {
  student_id: number
  name: string
  email: string
  phone?: string
  department: {
    id: string
    name: string
  }
  academic_info: {
    pride: string
    class_number: number
    track?: string  // 전계열, 자연계열, 인문사회계열
    advisor_name?: string
    status: string
  }
  latest_major_choice?: string  // 최신 희망 학과
  decision_certainty?: number  // 전공결정도 (1-5)
  completion_status?: string  // 이수현황 (예: "15/20")
  course_suitability?: string  // 수강과목 적합성
}

export interface StudentDetail extends Student {
  academic_info: Student['academic_info'] & {
    advisor_id?: number
    updated_at?: string
  }
}

export interface StudentCoursesResponse {
  student_id: number
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
  grade?: string
  numeric_grade?: number
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
  student_id: number
  name: string
  email: string
  phone?: string
  department_id: string
  advisor_id?: number
  pride: string
  class_number: number
}

export interface StudentCreateResponse {
  message: string
  student_id: number
}

// ============================================================================
// Department Types
// ============================================================================

export interface DepartmentsResponse {
  count: number
  departments: Department[]
}

export interface Department {
  id: string
  code: string
  name: string
  college_name: string
  min_credits: number
  is_evaluation_available?: boolean
}

export interface DepartmentCurriculum {
  department_name: string
  graduation_min_credits: number
  tracks: string[]
  entry_requirements_description: string
}

// ============================================================================
// Course Types
// ============================================================================

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
    id: string
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
  department_id: string
  department_name: string
  is_recommended: boolean
}

// ============================================================================
// Survey Types
// ============================================================================

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
  student_id: number
  first_choice_dept_id: string
  second_choice_dept_id?: string
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
  student_id: number
  name: string
  department_name: string
  first_choice: { id: number; name: string }
  second_choice?: { id: number; name: string }
  decision_scale: number
  submitted_at: string
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface DashboardStatsResponse {
  colleges: College[]
  departments: DepartmentWithStats[]
  current_data: DepartmentWithStats[]
  trend_data: TrendDataPoint[]
  survey_info?: {
    round_number: number
    title: string
    status: string
    end_date: string | null
  }
  survey_rounds?: {
    round_number: number
    title: string
  }[]
  current_data_by_round?: Record<number, DepartmentWithStats[]>
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

// ============================================================================
// Evaluation Types
// ============================================================================

export interface CurriculumCourse {
  course_code: string
  course_name: string
  credits: number
  course_type?: string
  year: number
  semester: number
  enrolled: boolean
  grade?: string
  evaluation_type?: string
  requirement_type?: string | null
  enrolled_department_name?: string
}

export interface EvaluationResult {
  student_id: number
  department_id: string
  department_name: string
  gpa_score: number
  required_courses_score: number
  recommended_completion_score: number
  recommended_grade_score: number
  curriculum_completion_score: number
  overall_score: number
  grade: string
  summary_message?: string
  curriculum_details?: Record<number, CurriculumCourse[]>
  analysis_json?: {
    entry_requirements: {
      status: string
      completed_requirements: string[]
      details: {
        requirement_text: string
        target_grade_level: string
        required_count: number
        logic_operator: string
        is_satisfied: boolean
        courses: {
          course_code: string
          course_name: string
          grade: string
          numeric_grade: number
          satisfied: boolean
        }[]
      }[]
    }
    gpa: {
      current_gpa: number
      max_gpa: number
      score: number
    }
    recommended_courses: {
      total: number
      completed: number
      completion_rate: number
      completed_list: string[]
      score: number
    }
    recommended_grades: {
      score: number
    }
    curriculum_completion: {
      score: number
    }
    overall: {
      score: number
      weights: {
        required_courses: number
        gpa: number
        recommended_completion: number
        recommended_grade: number
        curriculum_completion: number
      }
    }
  }
  evaluated_at: string
  cached?: boolean
  ai_summary?: string
}

export interface EvaluationStatistics {
  total_evaluated: number
  average_score: number
  max_score: number
  min_score: number
  grade_distribution: {
    A: number
    B: number
    C: number
    D: number
    F: number
  }
  satisfaction_rate: number
}

export interface DepartmentRankings {
  department_name: string
  total_evaluated: number
  rankings: {
    rank: number
    student_id: number
    student_name: string
    overall_score: number
    is_satisfied: boolean
    gpa: number
  }[]
}

// ============================================================================
// Admin Types
// ============================================================================

export interface ErrorDetail {
  row: number
  item_id: string
  reason: string
}

export interface UploadResponse {
  success: boolean
  message: string
  uploaded_count: number
  updated_count: number
  errors?: string[]
  detailed_errors?: ErrorDetail[]
}

export interface SubUploadResult {
  label: string
  success: boolean
  message: string
  uploaded_count: number
  updated_count: number
  errors?: string[] | null
  detailed_errors?: ErrorDetail[] | null
}

export interface GroupedUploadResponse extends UploadResponse {
  sub_results?: SubUploadResult[]
}

export interface BulkEvaluationRequest {
  student_ids?: string[]
  department_ids?: number[]
  force_recalculate?: boolean
}

export interface BulkEvaluationResponse {
  success: boolean
  message: string
  total_students: number
  total_departments: number
  total_evaluations: number
  success_count: number
  error_count: number
  errors?: string[]
}

export interface CachedEvaluationStats {
  total_cached: number
  cached_by_department: { [key: string]: number }
  last_update: string | null
}

export interface ClearCacheResponse {
  success: boolean
  message: string
  deleted_count: number
}
