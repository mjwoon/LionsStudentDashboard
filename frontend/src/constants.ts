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
  'A+', 'A0', 'A-',
  'B+', 'B0', 'B-',
  'C+', 'C0', 'C-',
  'D+', 'D0', 'D-',
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
 * Get score color based on value
 */
export function getScoreColor(score: number): string {
  if (score >= 90) return SCORE_COLORS.excellent;
  if (score >= 80) return SCORE_COLORS.good;
  if (score >= 70) return SCORE_COLORS.average;
  if (score >= 60) return SCORE_COLORS.below;
  return SCORE_COLORS.poor;
}

/**
 * Get grade badge color
 */
export function getGradeBadgeColor(grade: string): string {
  const firstChar = grade.charAt(0) as keyof typeof GRADE_COLORS;
  return GRADE_COLORS[firstChar] || GRADE_COLORS.F;
}

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

/**
 * Get course type badge color
 */
export function getCourseTypeBadgeColor(type: string): string {
  return COURSE_TYPE_COLORS[type] || 'bg-gray-100 text-gray-800';
}

/**
 * Get decision certainty label and color
 */
export function getDecisionCertaintyDisplay(certainty?: number): { label: string; color: string } {
  if (!certainty) {
    return { label: '-', color: 'text-gray-500' };
  }
  
  const label = DECISION_SCALE.LABELS[certainty as keyof typeof DECISION_SCALE.LABELS] || '-';
  
  const colorMap: Record<number, string> = {
    5: 'bg-green-100 text-green-800',
    4: 'bg-blue-100 text-blue-800',
    3: 'bg-gray-100 text-gray-800',
    2: 'bg-orange-100 text-orange-800',
    1: 'bg-red-100 text-red-800'
  };
  
  const color = colorMap[certainty] || 'bg-gray-100 text-gray-800';
  
  return { label, color };
}

/**
 * Get score badge color based on value
 */
export function getScoreBadgeColor(score: number | string): string {
  const numScore = typeof score === 'string' ? parseInt(score) : score;
  
  if (numScore >= 80) return 'bg-green-100 text-green-800';
  if (numScore >= 60) return 'bg-blue-100 text-blue-800';
  if (numScore >= 40) return 'bg-yellow-100 text-yellow-800';
  return 'bg-red-100 text-red-800';
}

/**
 * Get badge variant for UI Badge component
 */
export function getScoreBadgeVariant(score: number | string): 'green' | 'blue' | 'yellow' | 'red' {
  const numScore = typeof score === 'string' ? parseInt(score) : score;
  
  if (numScore >= 80) return 'green';
  if (numScore >= 60) return 'blue';
  if (numScore >= 40) return 'yellow';
  return 'red';
}

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
