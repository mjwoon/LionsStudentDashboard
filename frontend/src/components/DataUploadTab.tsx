import { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Download } from 'lucide-react';
import { api } from '../api';
import type { UploadResponse } from '../api';
import { DEFAULT_MAX_GPA } from '../constants';

interface UploadState {
  file: File | null;
  uploading: boolean;
  result: UploadResponse | null;
}

export default function DataUploadTab() {
  const [collegesState, setCollegesState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [departmentsState, setDepartmentsState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [advisorsState, setAdvisorsState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [majorSurveysState, setMajorSurveysState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [coursesState, setCoursesState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [studentsState, setStudentsState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [enrollmentsState, setEnrollmentsState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [curriculumsState, setCurriculumsState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [recommendationsState, setRecommendationsState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [requirementsState, setRequirementsState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const [reqCoursesState, setReqCoursesState] = useState<UploadState>({
    file: null,
    uploading: false,
    result: null,
  });

  const handleFileSelect = (
    event: React.ChangeEvent<HTMLInputElement>,
    setState: React.Dispatch<React.SetStateAction<UploadState>>
  ) => {
    const file = event.target.files?.[0];
    if (file) {
      setState((prev) => ({ ...prev, file, result: null }));
    }
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

      // 성공 시 파일 선택 초기화
      if (result.success) {
        setTimeout(() => {
          setState((prev) => ({ ...prev, file: null }));
        }, 3000);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '업로드 실패';
      setState((prev) => ({
        ...prev,
        uploading: false,
        result: {
          success: false,
          message: errorMessage,
          uploaded_count: 0,
          updated_count: 0,
        },
      }));
    }
  };

  const downloadSampleJSON = (type: 'colleges' | 'departments' | 'advisors' | 'courses' | 'major_surveys' | 'students' | 'enrollments' | 'curriculums' | 'recommendations' | 'requirements' | 'requirement_courses') => {
    let sampleData: any[] = [];
    let filename = '';

    if (type === 'colleges') {
      sampleData = [
        {
          id: 100,
          name: '융합공학대학',
        },
      ];
      filename = 'sample_colleges.json';
    } else if (type === 'departments') {
      sampleData = [
        {
          id: 100,
          code: 'CS',
          name: '컴퓨터학부',
          college_id: 100,
          min_credits: 130,
        },
      ];
      filename = 'sample_departments.json';
    } else if (type === 'advisors') {
      sampleData = [
        {
          id: 1,
          name: '이순신',
          email: 'leesunsin@hanyang.ac.kr',
          department_id: 100,
        },
      ];
      filename = 'sample_advisors.json';
    } else if (type === 'courses') {
      sampleData = [
        {
          '학년': 1,
          '학기': 1,
          '이수구분': '전공기초',
          '학수번호': 'CSE101',
          '교과목 이름': '컴퓨터공학개론',
          '설강학과': '컴퓨터학부',
          '교과목개요': '컴퓨터공학의 기초 개념을 학습한다',
          '선수강 과목': '',
          '학점': 3
        },
      ];
      filename = 'sample_courses.json';
    } else if (type === 'major_surveys') {
      sampleData = [
        {
          id: 1,
          student_id: "2024123456",
          survey_round_id: 1,
          first_choice_id: 101,
          second_choice_id: 102,
          decision_status_id: 1,
          decision_scale: 5
        },
      ];
      filename = 'sample_major_surveys.json';
    } else if (type === 'students') {
      sampleData = [
        {
          student_id: "2024123456",
          name: '홍길동',
          email: 'hong@hanyang.ac.kr',
          phone: '010-1234-5678',
          department_id: 100,
          advisor_id: 1,
          pride: 'L',
          class_number: 1,
          track: '자연계열',
        },
      ];
      filename = 'sample_students.json';
    } else if (type === 'enrollments') {
      sampleData = [
        {
          id: 1,
          '학번': "2024123456",
          '학수번호': "GEN0063",
          '과목명': "일반물리학1",
          '학점': 3,
          '년도': 2024,
          '학기': 1,
          '이수구분': '전공필수',
          '재수강여부': false,
          '성적': 'A+',
          '평점': DEFAULT_MAX_GPA,
        },
      ];
      filename = 'sample_enrollments.json';
    } else if (type === 'curriculums') {
      sampleData = [
        {
          department_code: 'CSE',
          course_year: 1,
          course_code: 'CSE101',
          course_name: '컴퓨터공학개론',
          credits: 3,
          course_type: '전공기초',
          semester: 1
        },
      ];
      filename = 'sample_curriculums.json';
    } else if (type === 'recommendations') {
      sampleData = [
        {
          department_code: 'CSE',
          course_name: '자료구조'
        },
      ];
      filename = 'sample_recommendations.json';
    } else if (type === 'requirements') {
      sampleData = [
        {
          department_code: 'CSE',
          admission_year: 2025,
          requirement_group: 1,
          target_grade_level: 'A',
          required_count: 2,
          requirement_text: 'A등급 2과목 이상 이수',
          is_alert_required: false,
          logic_operator: 'AND'
        },
      ];
      filename = 'sample_requirements.json';
    } else if (type === 'requirement_courses') {
      sampleData = [
        {
          id: 1,
          '요건 ID': 1,
          '학수번호': 'CSE101'
        },
      ];
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
    type: 'colleges' | 'departments' | 'advisors' | 'courses' | 'major_surveys' | 'students' | 'enrollments' | 'curriculums' | 'recommendations' | 'requirements' | 'requirement_courses'
  ) => (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center gap-3 mb-4">
        {icon}
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      </div>

      <div className="space-y-4">
        {/* 파일 선택 */}
        <div className="flex items-center gap-3">
          <input
            type="file"
            accept=".json,.csv,.xlsx"
            onChange={(e) => handleFileSelect(e, setState)}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-lg file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100
              cursor-pointer"
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

        {/* 선택된 파일 */}
        {state.file && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <FileText className="h-4 w-4" />
            <span>{state.file.name}</span>
            <span className="text-gray-400">
              ({(state.file.size / 1024).toFixed(2)} KB)
            </span>
          </div>
        )}

        {/* 업로드 버튼 */}
        <button
          onClick={() => handleUpload(uploadFn, state, setState)}
          disabled={!state.file || state.uploading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {state.uploading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>업로드 중...</span>
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              <span>업로드</span>
            </>
          )}
        </button>

        {/* 결과 표시 */}
        {state.result && (
          <div
            className={`p-4 rounded-lg ${state.result.success
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
              }`}
          >
            <div className="flex items-start gap-2">
              {state.result.success ? (
                <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <p
                  className={`font-medium ${state.result.success ? 'text-green-800' : 'text-red-800'
                    }`}
                >
                  {state.result.message}
                </p>
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
                            <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-red-800 uppercase tracking-wider">
                              Row
                            </th>
                            <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-red-800 uppercase tracking-wider">
                              Item
                            </th>
                            <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-red-800 uppercase tracking-wider">
                              Reason
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-red-100">
                          {state.result.detailed_errors.map((error, index) => (
                            <tr key={index}>
                              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">
                                {error.row}
                              </td>
                              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">
                                {error.item_id}
                              </td>
                              <td className="px-3 py-2 text-sm text-gray-500">
                                {error.reason}
                              </td>
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
                      {state.result.errors.length > 5 && (
                        <li className="text-gray-600">
                          외 {state.result.errors.length - 5}건
                        </li>
                      )}
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

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">데이터 업로드 안내</p>
            <ul className="list-disc list-inside space-y-1 text-blue-700">
              <li>JSON, CSV, Excel(.xlsx) 형식의 파일 업로드가 가능합니다</li>
              <li>기존 데이터는 자동으로 업데이트됩니다</li>
              <li>샘플 버튼을 클릭하여 형식을 확인하세요</li>
              <li>오류 발생 시 전체 업로드가 취소됩니다 (트랜잭션)</li>
            </ul>
          </div>
        </div>
      </div>

      {renderUploadSection(
        '대학 데이터',
        <FileText className="h-5 w-5 text-yellow-600" />,
        collegesState,
        setCollegesState,
        api.admin.uploadCollegesFile,
        'colleges'
      )}

      {renderUploadSection(
        '학과 데이터',
        <FileText className="h-5 w-5 text-cyan-600" />,
        departmentsState,
        setDepartmentsState,
        api.admin.uploadDepartmentsFile,
        'departments'
      )}

      {renderUploadSection(
        '지도교수 데이터',
        <FileText className="h-5 w-5 text-teal-600" />,
        advisorsState,
        setAdvisorsState,
        api.admin.uploadAdvisorsFile,
        'advisors'
      )}

      {renderUploadSection(
        '과목 데이터',
        <FileText className="h-5 w-5 text-amber-600" />,
        coursesState,
        setCoursesState,
        api.admin.uploadCoursesFile,
        'courses'
      )}

      {renderUploadSection(
        '수강 데이터',
        <FileText className="h-5 w-5 text-purple-600" />,
        enrollmentsState,
        setEnrollmentsState,
        api.admin.uploadEnrollmentsFile,
        'enrollments'
      )}

      {renderUploadSection(
        '교육과정 데이터',
        <FileText className="h-5 w-5 text-orange-600" />,
        curriculumsState,
        setCurriculumsState,
        api.admin.uploadCurriculumsFile,
        'curriculums'
      )}

      {renderUploadSection(
        '학생 데이터',
        <FileText className="h-5 w-5 text-green-600" />,
        studentsState,
        setStudentsState,
        api.admin.uploadStudentsFile,
        'students'
      )}

      {renderUploadSection(
        '희망 전공 조사',
        <FileText className="h-5 w-5 text-blue-600" />,
        majorSurveysState,
        setMajorSurveysState,
        api.admin.uploadMajorSurveysFile,
        'major_surveys'
      )}

      {renderUploadSection(
        '권장과목 데이터',
        <FileText className="h-5 w-5 text-pink-600" />,
        recommendationsState,
        setRecommendationsState,
        api.admin.uploadRecommendationsFile,
        'recommendations'
      )}

      {renderUploadSection(
        '학과요건 데이터',
        <FileText className="h-5 w-5 text-indigo-600" />,
        requirementsState,
        setRequirementsState,
        api.admin.uploadRequirementsFile,
        'requirements'
      )}

      {renderUploadSection(
        '요건 과목 매핑 데이터',
        <FileText className="h-5 w-5 text-indigo-400" />,
        reqCoursesState,
        setReqCoursesState,
        api.admin.uploadRequirementCoursesFile,
        'requirement_courses'
      )}
    </div>
  );
}
