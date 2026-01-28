import { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Download } from 'lucide-react';
import { api } from '../api';
import type { UploadResponse } from '../api';

interface UploadState {
  file: File | null;
  uploading: boolean;
  result: UploadResponse | null;
}

export default function DataUploadTab() {
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

  const downloadSampleJSON = (type: 'courses' | 'students' | 'enrollments') => {
    let sampleData: any[] = [];
    let filename = '';

    if (type === 'courses') {
      sampleData = [
        {
          course_code: 'CSE101',
          course_name: '컴퓨터공학개론',
          credits: 3,
          course_type: '전공필수',
          department_code: 'CSE',
          course_year: 1,
          semester: 1,
          is_retake_only: false,
          description: '컴퓨터공학의 기초',
        },
      ];
      filename = 'sample_courses.json';
    } else if (type === 'students') {
      sampleData = [
        {
          student_id: '2024123456',
          name: '홍길동',
          email: 'hong@hanyang.ac.kr',
          phone: '010-1234-5678',
          department_code: 'LION',
          pride: 'L',
          class_number: 1,
          track: '자연계열',
        },
      ];
      filename = 'sample_students.json';
    } else {
      sampleData = [
        {
          student_id: '2024123456',
          course_code: 'CSE101',
          year: 2024,
          semester: 1,
          completion_type: '전공필수',
          is_retake: false,
          grade: 'A+',
          numeric_grade: 4.5,
        },
      ];
      filename = 'sample_enrollments.json';
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
    type: 'courses' | 'students' | 'enrollments'
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
            accept=".json"
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
            className={`p-4 rounded-lg ${
              state.result.success
                ? 'bg-green-50 border border-green-200'
                : 'bg-red-50 border border-red-200'
            }`}
          >
            <div className="flex items-start gap-2">
              {state.result.success ? (
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <p
                  className={`font-medium ${
                    state.result.success ? 'text-green-800' : 'text-red-800'
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
                {state.result.errors && state.result.errors.length > 0 && (
                  <div className="mt-2 text-sm text-red-700">
                    <p className="font-medium">⚠️ 오류 ({state.result.errors.length}건):</p>
                    <ul className="mt-1 list-disc list-inside space-y-1">
                      {state.result.errors.slice(0, 5).map((error, index) => (
                        <li key={index} className="truncate">{error}</li>
                      ))}
                      {state.result.errors.length > 5 && (
                        <li className="text-gray-600">
                          ...외 {state.result.errors.length - 5}건
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
          <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">데이터 업로드 안내</p>
            <ul className="list-disc list-inside space-y-1 text-blue-700">
              <li>JSON 형식의 파일만 업로드 가능합니다</li>
              <li>기존 데이터는 자동으로 업데이트됩니다</li>
              <li>샘플 버튼을 클릭하여 형식을 확인하세요</li>
              <li>오류 발생 시 전체 업로드가 취소됩니다 (트랜잭션)</li>
            </ul>
          </div>
        </div>
      </div>

      {renderUploadSection(
        '과목 데이터',
        <FileText className="h-5 w-5 text-blue-600" />,
        coursesState,
        setCoursesState,
        api.admin.uploadCoursesFile,
        'courses'
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
        '수강 데이터',
        <FileText className="h-5 w-5 text-purple-600" />,
        enrollmentsState,
        setEnrollmentsState,
        api.admin.uploadEnrollmentsFile,
        'enrollments'
      )}
    </div>
  );
}
