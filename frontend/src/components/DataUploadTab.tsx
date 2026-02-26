import { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Download, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../api';
import type { UploadResponse } from '../api';
import { DEFAULT_MAX_GPA } from '../constants';

interface UploadState {
  file: File | null;
  uploading: boolean;
  result: UploadResponse | null;
}

type UploadType = 'colleges' | 'departments' | 'advisors' | 'courses' | 'major_surveys' | 'students' | 'enrollments' | 'curriculums' | 'recommendations' | 'requirements' | 'requirement_courses';

interface BulkFileItem {
  file: File;
  type: UploadType | 'unknown';
  status: 'pending' | 'uploading' | 'success' | 'error';
  message?: string;
  uploadedCount?: number;
  updatedCount?: number;
}

const UPLOAD_CONFIG: Record<UploadType, { label: string; fn: (file: File) => Promise<UploadResponse> }> = {
  colleges: { label: '대학 데이터', fn: api.admin.uploadCollegesFile },
  departments: { label: '학과 데이터', fn: api.admin.uploadDepartmentsFile },
  advisors: { label: '지도교수 데이터', fn: api.admin.uploadAdvisorsFile },
  courses: { label: '과목 데이터', fn: api.admin.uploadCoursesFile },
  major_surveys: { label: '희망 전공 조사', fn: api.admin.uploadMajorSurveysFile },
  students: { label: '학생 데이터', fn: api.admin.uploadStudentsFile },
  enrollments: { label: '수강 데이터', fn: api.admin.uploadEnrollmentsFile },
  curriculums: { label: '교육과정 데이터', fn: api.admin.uploadCurriculumsFile },
  recommendations: { label: '권장과목 데이터', fn: api.admin.uploadRecommendationsFile },
  requirements: { label: '학과요건 데이터', fn: api.admin.uploadRequirementsFile },
  requirement_courses: { label: '요건 과목 매핑 데이터', fn: api.admin.uploadRequirementCoursesFile },
};

function detectFileType(filename: string): UploadType | 'unknown' {
  const lower = filename.toLowerCase();
  // 더 구체적인 패턴을 먼저 체크
  if (lower.includes('requirement_course') || lower.includes('req_course') || lower.includes('요건_과목') || lower.includes('요건과목')) return 'requirement_courses';
  if (lower.includes('requirement') || lower.includes('요건')) return 'requirements';
  if (lower.includes('recommendation') || lower.includes('권장')) return 'recommendations';
  if (lower.includes('curriculum') || lower.includes('교육과정') || lower.includes('커리큘럼')) return 'curriculums';
  if (lower.includes('enrollment') || lower.includes('수강')) return 'enrollments';
  if (lower.includes('survey') || lower.includes('설문') || lower.includes('희망')) return 'major_surveys';
  if (lower.includes('student') || lower.includes('학생')) return 'students';
  if (lower.includes('advisor') || lower.includes('지도교수') || lower.includes('교수')) return 'advisors';
  if (lower.includes('department') || lower.includes('학과')) return 'departments';
  if (lower.includes('college') || lower.includes('대학')) return 'colleges';
  if (lower.includes('course') || lower.includes('과목')) return 'courses';
  return 'unknown';
}

export default function DataUploadTab() {
  // 일괄 업로드 상태
  const [bulkFiles, setBulkFiles] = useState<BulkFileItem[]>([]);
  const [isBulkUploading, setIsBulkUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [showIndividual, setShowIndividual] = useState(false);
  const bulkInputRef = useRef<HTMLInputElement>(null);

  // 개별 업로드 상태
  const [collegesState, setCollegesState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [departmentsState, setDepartmentsState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [advisorsState, setAdvisorsState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [majorSurveysState, setMajorSurveysState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [coursesState, setCoursesState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [studentsState, setStudentsState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [enrollmentsState, setEnrollmentsState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [curriculumsState, setCurriculumsState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [recommendationsState, setRecommendationsState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [requirementsState, setRequirementsState] = useState<UploadState>({ file: null, uploading: false, result: null });
  const [reqCoursesState, setReqCoursesState] = useState<UploadState>({ file: null, uploading: false, result: null });

  // 일괄 업로드 파일 추가
  const addBulkFiles = (files: FileList | File[]) => {
    const newItems: BulkFileItem[] = Array.from(files).map((file) => ({
      file,
      type: detectFileType(file.name),
      status: 'pending',
    }));
    setBulkFiles((prev) => {
      // 중복 파일명 제거
      const existingNames = new Set(prev.map((f) => f.file.name));
      const unique = newItems.filter((item) => !existingNames.has(item.file.name));
      return [...prev, ...unique];
    });
  };

  const handleBulkDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    addBulkFiles(e.dataTransfer.files);
  };

  const handleBulkFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addBulkFiles(e.target.files);
      e.target.value = '';
    }
  };

  const removeBulkFile = (index: number) => {
    setBulkFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const updateBulkFileType = (index: number, type: UploadType | 'unknown') => {
    setBulkFiles((prev) => prev.map((item, i) => i === index ? { ...item, type } : item));
  };

  const handleBulkUpload = async () => {
    const uploadable = bulkFiles.filter((f) => f.type !== 'unknown' && f.status === 'pending');
    if (uploadable.length === 0) return;

    setIsBulkUploading(true);

    for (let i = 0; i < bulkFiles.length; i++) {
      const item = bulkFiles[i];
      if (item.type === 'unknown' || item.status !== 'pending') continue;

      setBulkFiles((prev) => prev.map((f, idx) => idx === i ? { ...f, status: 'uploading' } : f));

      try {
        const config = UPLOAD_CONFIG[item.type];
        const result = await config.fn(item.file);
        setBulkFiles((prev) => prev.map((f, idx) =>
          idx === i ? {
            ...f,
            status: result.success ? 'success' : 'error',
            message: result.message,
            uploadedCount: result.uploaded_count,
            updatedCount: result.updated_count,
          } : f
        ));
      } catch (err) {
        setBulkFiles((prev) => prev.map((f, idx) =>
          idx === i ? { ...f, status: 'error', message: err instanceof Error ? err.message : '업로드 실패' } : f
        ));
      }
    }

    setIsBulkUploading(false);
  };

  const clearBulkCompleted = () => {
    setBulkFiles((prev) => prev.filter((f) => f.status === 'pending' || f.status === 'uploading'));
  };

  const pendingCount = bulkFiles.filter((f) => f.status === 'pending' && f.type !== 'unknown').length;
  const unknownCount = bulkFiles.filter((f) => f.type === 'unknown').length;

  // 개별 업로드 핸들러
  const handleFileSelect = (
    event: React.ChangeEvent<HTMLInputElement>,
    setState: React.Dispatch<React.SetStateAction<UploadState>>
  ) => {
    const file = event.target.files?.[0];
    if (file) setState((prev) => ({ ...prev, file, result: null }));
  };

  const handleUpload = async (
    uploadFn: (file: File) => Promise<UploadResponse>,
    state: UploadState,
    setState: React.Dispatch<React.SetStateAction<UploadState>>
  ) => {
    if (!state.file) return;
    setState((prev) => ({ ...prev, uploading: true, result: null }));
    try {
      const result = await uploadFn(state.file);
      setState((prev) => ({ ...prev, uploading: false, result }));
      if (result.success) {
        setTimeout(() => setState((prev) => ({ ...prev, file: null })), 3000);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '업로드 실패';
      setState((prev) => ({
        ...prev,
        uploading: false,
        result: { success: false, message: errorMessage, uploaded_count: 0, updated_count: 0 },
      }));
    }
  };

  const downloadSampleJSON = (type: UploadType) => {
    let sampleData: any[] = [];
    let filename = '';

    if (type === 'colleges') {
      sampleData = [{ id: 100, name: '융합공학대학' }];
      filename = 'sample_colleges.json';
    } else if (type === 'departments') {
      sampleData = [{ id: 100, code: 'CS', name: '컴퓨터학부', college_id: 100, min_credits: 130 }];
      filename = 'sample_departments.json';
    } else if (type === 'advisors') {
      sampleData = [{ id: 1, name: '이순신', email: 'leesunsin@hanyang.ac.kr', department_id: 100 }];
      filename = 'sample_advisors.json';
    } else if (type === 'courses') {
      sampleData = [{ '학년': 1, '학기': 1, '이수구분': '전공기초', '학수번호': 'CSE101', '교과목 이름': '컴퓨터공학개론', '설강학과': '컴퓨터학부', '교과목개요': '컴퓨터공학의 기초 개념을 학습한다', '선수강 과목': '', '학점': 3 }];
      filename = 'sample_courses.json';
    } else if (type === 'major_surveys') {
      sampleData = [{ id: 1, student_id: "2024123456", survey_round_id: 1, first_choice_id: 101, second_choice_id: 102, decision_status_id: 1, decision_scale: 5 }];
      filename = 'sample_major_surveys.json';
    } else if (type === 'students') {
      sampleData = [{ student_id: "2024123456", name: '홍길동', email: 'hong@hanyang.ac.kr', phone: '010-1234-5678', department_id: 100, advisor_id: 1, pride: 'L', class_number: 1, track: '자연계열' }];
      filename = 'sample_students.json';
    } else if (type === 'enrollments') {
      sampleData = [{ id: 1, '학번': "2024123456", '학수번호': "GEN0063", '과목명': "일반물리학1", '학점': 3, '년도': 2024, '학기': 1, '이수구분': '전공필수', '재수강여부': false, '성적': 'A+', '평점': DEFAULT_MAX_GPA }];
      filename = 'sample_enrollments.json';
    } else if (type === 'curriculums') {
      sampleData = [{ department_code: 'CSE', course_year: 1, course_code: 'CSE101', course_name: '컴퓨터공학개론', credits: 3, course_type: '전공기초', semester: 1 }];
      filename = 'sample_curriculums.json';
    } else if (type === 'recommendations') {
      sampleData = [{ department_code: 'CSE', course_name: '자료구조' }];
      filename = 'sample_recommendations.json';
    } else if (type === 'requirements') {
      sampleData = [{ department_code: 'CSE', admission_year: 2025, requirement_group: 1, target_grade_level: 'A', required_count: 2, requirement_text: 'A등급 2과목 이상 이수', is_alert_required: false, logic_operator: 'AND' }];
      filename = 'sample_requirements.json';
    } else if (type === 'requirement_courses') {
      sampleData = [{ id: 1, '요건 ID': 1, '학수번호': 'CSE101' }];
      filename = 'sample_requirement_courses.json';
    }

    const json = JSON.stringify(sampleData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const renderUploadSection = (
    title: string,
    icon: React.ReactNode,
    state: UploadState,
    setState: React.Dispatch<React.SetStateAction<UploadState>>,
    uploadFn: (file: File) => Promise<UploadResponse>,
    type: UploadType
  ) => (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center gap-3 mb-4">
        {icon}
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      </div>
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <input
            type="file"
            accept=".json,.csv,.xlsx"
            onChange={(e) => handleFileSelect(e, setState)}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
            disabled={state.uploading}
          />
          <button
            onClick={() => downloadSampleJSON(type)}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors whitespace-nowrap"
            title="샘플 다운로드"
          >
            <Download className="h-4 w-4" />
            샘플
          </button>
        </div>
        {state.file && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <FileText className="h-4 w-4" />
            <span>{state.file.name}</span>
            <span className="text-gray-400">({(state.file.size / 1024).toFixed(2)} KB)</span>
          </div>
        )}
        <button
          onClick={() => handleUpload(uploadFn, state, setState)}
          disabled={!state.file || state.uploading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {state.uploading ? (
            <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div><span>업로드 중...</span></>
          ) : (
            <><Upload className="h-4 w-4" /><span>업로드</span></>
          )}
        </button>
        {state.result && (
          <div className={`p-4 rounded-lg ${state.result.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            <div className="flex items-start gap-2">
              {state.result.success ? (
                <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <p className={`font-medium ${state.result.success ? 'text-green-800' : 'text-red-800'}`}>{state.result.message}</p>
                {state.result.success && (
                  <div className="mt-2 text-sm text-green-700">
                    <p>✓ 새로 추가: {state.result.uploaded_count}개</p>
                    <p>✓ 업데이트: {state.result.updated_count}개</p>
                  </div>
                )}
                {state.result.detailed_errors && state.result.detailed_errors.length > 0 && (
                  <div className="mt-3 text-sm text-red-700">
                    <p className="font-medium mb-2">⚠️ 오류 내역 ({state.result.detailed_errors.length}건):</p>
                    <div className="max-h-60 overflow-y-auto border border-red-200 rounded">
                      <table className="min-w-full divide-y divide-red-200">
                        <thead className="bg-red-50 sticky top-0">
                          <tr>
                            <th className="px-3 py-2 text-left text-xs font-medium text-red-800 uppercase">Row</th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-red-800 uppercase">Item</th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-red-800 uppercase">Reason</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-red-100">
                          {state.result.detailed_errors.map((error, index) => (
                            <tr key={index}>
                              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">{error.row}</td>
                              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">{error.item_id}</td>
                              <td className="px-3 py-2 text-sm text-gray-500">{error.reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                {!state.result.detailed_errors && state.result.errors && state.result.errors.length > 0 && (
                  <div className="mt-2 text-sm text-red-700">
                    <p className="font-medium">⚠️ 일반 오류 ({state.result.errors.length}건):</p>
                    <ul className="mt-1 list-disc list-inside space-y-1">
                      {state.result.errors.slice(0, 5).map((error, index) => (
                        <li key={index} className="truncate">{error}</li>
                      ))}
                      {state.result.errors.length > 5 && <li className="text-gray-600">외 {state.result.errors.length - 5}건</li>}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const statusIcon = (status: BulkFileItem['status']) => {
    if (status === 'success') return <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />;
    if (status === 'error') return <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />;
    if (status === 'uploading') return <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 shrink-0" />;
    return <div className="h-4 w-4 rounded-full border-2 border-gray-300 shrink-0" />;
  };

  return (
    <div className="space-y-6">
      {/* 일괄 업로드 섹션 */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Upload className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">일괄 업로드</h3>
            <span className="text-sm text-gray-500">파일명으로 타입 자동 감지</span>
          </div>

          {/* 드래그 앤 드롭 영역 */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleBulkDrop}
            onClick={() => bulkInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
            }`}
          >
            <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-700">파일을 여기에 드래그하거나 클릭하여 선택</p>
            <p className="text-xs text-gray-500 mt-1">여러 파일 동시 선택 가능 · JSON, CSV, XLSX</p>
            <input
              ref={bulkInputRef}
              type="file"
              accept=".json,.csv,.xlsx"
              multiple
              className="hidden"
              onChange={handleBulkFileInput}
            />
          </div>

          {/* 파일 이름 → 타입 힌트 */}
          <div className="mt-3 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 font-medium mb-1">파일명 자동 감지 패턴</p>
            <p className="text-xs text-gray-400">
              college · department · advisor · course · enrollment · curriculum · student · survey/희망 · recommendation/권장 · requirement_course/요건과목 · requirement/요건
            </p>
          </div>

          {/* 파일 목록 */}
          {bulkFiles.length > 0 && (
            <div className="mt-4 space-y-2">
              {bulkFiles.map((item, index) => (
                <div key={index} className={`flex items-center gap-3 p-3 rounded-lg border ${
                  item.status === 'success' ? 'bg-green-50 border-green-200' :
                  item.status === 'error' ? 'bg-red-50 border-red-200' :
                  item.type === 'unknown' ? 'bg-yellow-50 border-yellow-200' :
                  'bg-gray-50 border-gray-200'
                }`}>
                  {statusIcon(item.status)}
                  <FileText className="h-4 w-4 text-gray-400 shrink-0" />
                  <span className="text-sm text-gray-700 flex-1 truncate min-w-0" title={item.file.name}>
                    {item.file.name}
                  </span>
                  <select
                    value={item.type}
                    onChange={(e) => updateBulkFileType(index, e.target.value as UploadType | 'unknown')}
                    disabled={item.status === 'uploading' || item.status === 'success'}
                    className={`text-xs border rounded px-2 py-1 shrink-0 ${
                      item.type === 'unknown' ? 'border-yellow-400 text-yellow-700 bg-yellow-50' : 'border-gray-300 text-gray-700 bg-white'
                    }`}
                  >
                    <option value="unknown">⚠ 타입 선택</option>
                    {(Object.keys(UPLOAD_CONFIG) as UploadType[]).map((t) => (
                      <option key={t} value={t}>{UPLOAD_CONFIG[t].label}</option>
                    ))}
                  </select>
                  {item.status === 'success' && (
                    <span className="text-xs text-green-600 shrink-0">+{item.uploadedCount} / ↑{item.updatedCount}</span>
                  )}
                  {item.status === 'error' && (
                    <span className="text-xs text-red-600 shrink-0 max-w-[120px] truncate" title={item.message}>{item.message}</span>
                  )}
                  {(item.status === 'pending') && (
                    <button
                      onClick={() => removeBulkFile(index)}
                      className="text-gray-400 hover:text-red-500 text-xs shrink-0"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}

              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={handleBulkUpload}
                  disabled={isBulkUploading || pendingCount === 0}
                  className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {isBulkUploading ? (
                    <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /><span>업로드 중...</span></>
                  ) : (
                    <><Upload className="h-4 w-4" /><span>전체 업로드 ({pendingCount}개)</span></>
                  )}
                </button>
                {unknownCount > 0 && (
                  <span className="text-xs text-yellow-600">⚠ 타입 미감지 {unknownCount}개 — 드롭다운으로 직접 선택하세요</span>
                )}
                <button
                  onClick={clearBulkCompleted}
                  className="ml-auto text-xs text-gray-500 hover:text-gray-700"
                >
                  완료된 항목 제거
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 안내 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">데이터 업로드 안내</p>
            <ul className="list-disc list-inside space-y-1 text-blue-700">
              <li>JSON, CSV, Excel(.xlsx) 형식의 파일 업로드가 가능합니다</li>
              <li>기존 데이터는 자동으로 업데이트됩니다</li>
              <li>오류 발생 시 해당 파일의 업로드가 취소됩니다 (트랜잭션)</li>
            </ul>
          </div>
        </div>
      </div>

      {/* 개별 업로드 (접기/펼치기) */}
      <div className="bg-white rounded-lg shadow">
        <button
          onClick={() => setShowIndividual((v) => !v)}
          className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition-colors rounded-lg"
        >
          <span className="font-semibold text-gray-700">개별 업로드</span>
          {showIndividual ? <ChevronUp className="h-5 w-5 text-gray-500" /> : <ChevronDown className="h-5 w-5 text-gray-500" />}
        </button>
      </div>

      {showIndividual && (
        <div className="space-y-6">
          {renderUploadSection('대학 데이터', <FileText className="h-5 w-5 text-yellow-600" />, collegesState, setCollegesState, api.admin.uploadCollegesFile, 'colleges')}
          {renderUploadSection('학과 데이터', <FileText className="h-5 w-5 text-cyan-600" />, departmentsState, setDepartmentsState, api.admin.uploadDepartmentsFile, 'departments')}
          {renderUploadSection('지도교수 데이터', <FileText className="h-5 w-5 text-teal-600" />, advisorsState, setAdvisorsState, api.admin.uploadAdvisorsFile, 'advisors')}
          {renderUploadSection('과목 데이터', <FileText className="h-5 w-5 text-amber-600" />, coursesState, setCoursesState, api.admin.uploadCoursesFile, 'courses')}
          {renderUploadSection('수강 데이터', <FileText className="h-5 w-5 text-purple-600" />, enrollmentsState, setEnrollmentsState, api.admin.uploadEnrollmentsFile, 'enrollments')}
          {renderUploadSection('교육과정 데이터', <FileText className="h-5 w-5 text-orange-600" />, curriculumsState, setCurriculumsState, api.admin.uploadCurriculumsFile, 'curriculums')}
          {renderUploadSection('학생 데이터', <FileText className="h-5 w-5 text-green-600" />, studentsState, setStudentsState, api.admin.uploadStudentsFile, 'students')}
          {renderUploadSection('희망 전공 조사', <FileText className="h-5 w-5 text-blue-600" />, majorSurveysState, setMajorSurveysState, api.admin.uploadMajorSurveysFile, 'major_surveys')}
          {renderUploadSection('권장과목 데이터', <FileText className="h-5 w-5 text-pink-600" />, recommendationsState, setRecommendationsState, api.admin.uploadRecommendationsFile, 'recommendations')}
          {renderUploadSection('학과요건 데이터', <FileText className="h-5 w-5 text-indigo-600" />, requirementsState, setRequirementsState, api.admin.uploadRequirementsFile, 'requirements')}
          {renderUploadSection('요건 과목 매핑 데이터', <FileText className="h-5 w-5 text-indigo-400" />, reqCoursesState, setReqCoursesState, api.admin.uploadRequirementCoursesFile, 'requirement_courses')}
        </div>
      )}
    </div>
  );
}
