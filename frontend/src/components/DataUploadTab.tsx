import { useState } from 'react';
import { CheckCircle, AlertCircle, Download } from 'lucide-react';
import { api } from '../api';
import type { GroupedUploadResponse, SubUploadResult } from '../api';

interface GroupUploadState {
  file: File | null;
  uploading: boolean;
  result: GroupedUploadResponse | null;
}

const INITIAL_STATE: GroupUploadState = {
  file: null,
  uploading: false,
  result: null,
};

interface UploadGroup {
  id: string;
  title: string;
  uploadFn: (file: File) => Promise<GroupedUploadResponse>;
  sampleData: Record<string, unknown>[];
  sampleFilename: string;
}

const UPLOAD_GROUPS: UploadGroup[] = [
  {
    id: 'org',
    title: '단과대학 + 학과',
    uploadFn: api.admin.uploadGroupedOrg,
    sampleFilename: 'sample_org.csv',
    sampleData: [
      {
        college_id: 100,
        college_name: '융합공학대학',
        dept_id: 101,
        dept_code: 'CSE',
        dept_name: '컴퓨터학부',
        min_credits: 130,
      },
      {
        college_id: 100,
        college_name: '융합공학대학',
        dept_id: 102,
        dept_code: 'EE',
        dept_name: '전자공학부',
        min_credits: 130,
      },
    ],
  },
  {
    id: 'students',
    title: '학생 + 희망전공조사',
    uploadFn: api.admin.uploadGroupedStudents,
    sampleFilename: 'sample_students.csv',
    sampleData: [
      {
        student_id: '2024123456',
        name: '홍길동',
        email: 'hong@hanyang.ac.kr',
        phone: '010-1234-5678',
        department_id: 101,
        pride: 'L',
        class_number: 1,
        track: '자연계열',
        survey_round_id: 1,
        first_choice_id: 101,
        second_choice_id: 102,
        decision_status_id: 1,
        decision_scale: 5,
      },
    ],
  },
  {
    id: 'requirements',
    title: '진입요건 + 권장과목',
    uploadFn: api.admin.uploadGroupedRequirements,
    sampleFilename: 'sample_requirements.csv',
    sampleData: [
      {
        department_code: 'CSE',
        admission_year: 2025,
        requirement_group: 1,
        target_grade_level: 'A',
        required_count: 2,
        requirement_text: 'A등급 2과목 이상 이수',
        is_alert_required: false,
        logic_operator: 'AND',
        course_code: 'CSE101',
        recommended_course: '자료구조',
      },
    ],
  },
  {
    id: 'courses',
    title: '과목 + 교육과정',
    uploadFn: api.admin.uploadGroupedCourses,
    sampleFilename: 'sample_courses.csv',
    sampleData: [
      {
        학수번호: 'CSE101',
        '교과목 이름': '컴퓨터공학개론',
        학점: 3,
        이수구분: '전공기초',
        학년: 1,
        학기: 1,
        설강학과: '컴퓨터학부',
        교과목개요: '컴퓨터공학의 기초를 학습한다.',
        교육과정학과코드: 'CSE',
      },
    ],
  },
  {
    id: 'enrollments',
    title: '수강 데이터',
    uploadFn: api.admin.uploadGroupedEnrollments,
    sampleFilename: 'sample_enrollments.csv',
    sampleData: [
      {
        학번: '2024123456',
        학수번호: 'CSE101',
        과목명: '컴퓨터공학개론',
        학점: 3,
        이수구분: '전공기초',
        성적: 'A+',
        평점: 4.5,
        재수강여부: false,
        년도: 2024,
        학기: 1,
      },
    ],
  },
];

export default function DataUploadTab() {
  const [states, setStates] = useState<Record<string, GroupUploadState>>(
    Object.fromEntries(UPLOAD_GROUPS.map((g) => [g.id, { ...INITIAL_STATE }]))
  );

  const updateState = (groupId: string, update: Partial<GroupUploadState>) => {
    setStates((prev) => ({
      ...prev,
      [groupId]: { ...prev[groupId], ...update },
    }));
  };

  const handleFileSelect = (
    event: React.ChangeEvent<HTMLInputElement>,
    groupId: string
  ) => {
    const file = event.target.files?.[0];
    if (file) {
      updateState(groupId, { file, result: null });
    }
  };

  const handleUpload = async (group: UploadGroup) => {
    const state = states[group.id];
    if (!state.file) return;

    updateState(group.id, { uploading: true, result: null });

    try {
      const result = await group.uploadFn(state.file);
      updateState(group.id, { uploading: false, result });

      if (result.success) {
        setTimeout(() => {
          updateState(group.id, { file: null });
        }, 3000);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '업로드 실패';
      updateState(group.id, {
        uploading: false,
        result: {
          success: false,
          message: errorMessage,
          uploaded_count: 0,
          updated_count: 0,
        },
      });
    }
  };

  const downloadSampleCSV = (group: UploadGroup) => {
    if (group.sampleData.length === 0) return;

    const headers = Object.keys(group.sampleData[0]);
    const csvRows = [
      headers.join(','),
      ...group.sampleData.map((row) =>
        headers
          .map((h) => {
            const val = row[h];
            if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
              return `"${val.replace(/"/g, '""')}"`;
            }
            return String(val ?? '');
          })
          .join(',')
      ),
    ];

    const csv = csvRows.join('\n');
    const bom = '\uFEFF'; // UTF-8 BOM for Excel
    const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = group.sampleFilename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const renderSubResults = (subResults: SubUploadResult[]) => (
    <div className="mt-3 space-y-2">
      {subResults.map((sub, idx) => (
        <div
          key={idx}
          className={`flex items-center justify-between px-3 py-2 rounded-md text-sm ${
            sub.success
              ? 'bg-green-50 text-green-800'
              : 'bg-red-50 text-red-800'
          }`}
        >
          <span className="font-medium">{sub.label}</span>
          <span>
            {sub.success
              ? `추가 ${sub.uploaded_count} / 업데이트 ${sub.updated_count}`
              : sub.message}
          </span>
        </div>
      ))}
    </div>
  );

  const renderGroupCard = (group: UploadGroup) => {
    const state = states[group.id];

    return (
      <div
        key={group.id}
        className="bg-white rounded-xl border border-gray-200 p-6"
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{group.title}</h3>
          </div>
        </div>

        <div className="space-y-4">
          {/* 파일 선택 + 파일명 + 샘플 */}
          <div className="flex items-center gap-3">
            <label
              className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg cursor-pointer transition-colors whitespace-nowrap ${
                state.uploading
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
              }`}
            >
              파일 선택
              <input
                type="file"
                accept=".csv,.json,.xlsx"
                onChange={(e) => handleFileSelect(e, group.id)}
                className="hidden"
                disabled={state.uploading}
              />
            </label>
            {state.file ? (
              <span className="text-sm text-gray-600 truncate min-w-0">
                {state.file.name}{' '}
                <span className="text-gray-400">
                  ({(state.file.size / 1024).toFixed(2)} KB)
                </span>
              </span>
            ) : (
              <span className="text-sm text-gray-400">선택된 파일 없음</span>
            )}
            <button
              onClick={() => downloadSampleCSV(group)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors whitespace-nowrap ml-auto"
              title="샘플 CSV 다운로드"
            >
              <Download className="h-4 w-4" />
              샘플
            </button>
          </div>

          {/* 업로드 버튼 */}
          <button
            onClick={() => handleUpload(group)}
            disabled={!state.file || state.uploading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#0F4A84] text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {state.uploading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>업로드 중...</span>
              </>
            ) : (
              <>
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
                  <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p
                    className={`font-medium ${
                      state.result.success ? 'text-green-800' : 'text-red-800'
                    }`}
                  >
                    {state.result.message}
                  </p>

                  {/* 하위 결과 표시 */}
                  {state.result.sub_results && state.result.sub_results.length > 0 &&
                    renderSubResults(state.result.sub_results)}

                  {/* 총합 */}
                  {state.result.success && (
                    <div className="mt-2 text-sm text-green-700">
                      <p>✓ 총 새로 추가: {state.result.uploaded_count}개</p>
                      <p>✓ 총 업데이트: {state.result.updated_count}개</p>
                    </div>
                  )}

                  {/* 에러 상세 표시 */}
                  {state.result.detailed_errors && state.result.detailed_errors.length > 0 && (
                    <div className="mt-3 text-sm text-red-700">
                      <p className="font-medium mb-2">
                        ⚠️ 오류 내역 ({state.result.detailed_errors.length}건):
                      </p>
                      <div className="max-h-60 overflow-y-auto border border-red-200 rounded">
                        <table className="min-w-full divide-y divide-red-200">
                          <thead className="bg-red-50 sticky top-0">
                            <tr>
                              <th className="px-3 py-2 text-left text-xs font-medium text-red-800 uppercase">
                                Row
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-red-800 uppercase">
                                Item
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-red-800 uppercase">
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

                  {/* 일반 에러 */}
                  {!state.result.detailed_errors &&
                    state.result.errors &&
                    state.result.errors.length > 0 && (
                      <div className="mt-2 text-sm text-red-700">
                        <p className="font-medium">
                          ⚠️ 오류 ({state.result.errors.length}건):
                        </p>
                        <ul className="mt-1 list-disc list-inside space-y-1">
                          {state.result.errors.slice(0, 5).map((err, idx) => (
                            <li key={idx} className="truncate">
                              {err}
                            </li>
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
  };

  return (
    <div className="space-y-6">
      {/* 안내 배너 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">데이터 업로드 안내</p>
            <ul className="list-disc list-inside space-y-1 text-blue-700">
              <li>CSV 형식의 파일 업로드가 가능합니다</li>
              <li>기존 데이터는 자동으로 업데이트됩니다</li>
              <li>샘플 버튼을 클릭하여 CSV 형식을 확인하세요</li>
            </ul>
          </div>
        </div>
      </div>

      {/* 5개 그룹 카드 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {UPLOAD_GROUPS.map((group) => renderGroupCard(group))}
      </div>
    </div>
  );
}
