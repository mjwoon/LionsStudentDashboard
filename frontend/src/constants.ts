/**
 * Application-wide constants for the frontend
 * These should match the backend constants where applicable
 */

// ============================================================================
// Grade System Constants
// ============================================================================

/**
 * Default maximum GPA value (fallback if not provided by backend)
 * Backend provides the actual max_gpa in API responses
 */
export const DEFAULT_MAX_GPA = 4.5;

/**
 * Failing grade identifier
 */
export const FAILING_GRADE = 'F';

/**
 * Grade display options for UI
 */
export const GRADE_OPTIONS = [
  'A+', 'A0', 
  'B+', 'B0', 
  'C+', 'C0',
  'D+', 'D0', 
  'F'
] as const;

/**
 * Decision certainty scale (1-5)
 */
export const DECISION_SCALE = {
  MIN: 1,
  MAX: 5,
  LABELS: {
    1: '매우 불확실',
    2: '불확실',
    3: '보통',
    4: '확실',
    5: '매우 확실'
  }
} as const;

// ============================================================================
// Evaluation System Display
// ============================================================================

/**
 * Metric weight labels for display
 * Actual weights come from backend
 */
export const METRIC_LABELS = {
  required_courses: '필수과목 학점',
  gpa: 'GPA',
  recommended_completion: '권장과목 이수',
  recommended_grade: '권장과목 학점',
  curriculum_completion: '교육과정 완성도'
} as const;

/**
 * Grade threshold colors for UI
 */
export const GRADE_COLORS = {
  A: 'text-green-600 bg-green-50',
  B: 'text-blue-600 bg-blue-50',
  C: 'text-yellow-600 bg-yellow-50',
  D: 'text-orange-600 bg-orange-50',
  F: 'text-red-600 bg-red-50'
} as const;

/**
 * Score threshold colors for progress bars
 */
export const SCORE_COLORS = {
  excellent: 'bg-green-500',  // 90+
  good: 'bg-blue-500',        // 80-89
  average: 'bg-yellow-500',   // 70-79
  below: 'bg-orange-500',     // 60-69
  poor: 'bg-red-500'          // <60
} as const;

/**
 * Course type badge colors
 */
export const COURSE_TYPE_COLORS: Record<string, string> = {
  '전공기초': 'bg-blue-100 text-blue-800',
  '전공핵심': 'bg-purple-100 text-purple-800',
  '전공심화': 'bg-indigo-100 text-indigo-800',
  '전공선택': 'bg-green-100 text-green-800',
  '교양필수': 'bg-yellow-100 text-yellow-800',
  '교양선택': 'bg-gray-100 text-gray-800',
} as const;

// ============================================================================
// Pagination Constants
// ============================================================================

export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_PER_PAGE: 20,
  STUDENT_LIST_PER_PAGE: 50,
  MAX_PER_PAGE: 100
} as const;

// ============================================================================
// API Configuration
// ============================================================================

export const API_CONFIG = {
  TIMEOUT: 30000,  // 30 seconds
  RETRY_COUNT: 3,
  RETRY_DELAY: 1000  // 1 second
} as const;
