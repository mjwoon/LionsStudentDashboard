import { useState } from 'react';
import { Activity, Play, AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../api';
import type { BulkEvaluationResponse } from '../types';

export default function DiagnosisManagementTab() {
  const [forceRecalculate, setForceRecalculate] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [result, setResult] = useState<BulkEvaluationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleEvaluate = async () => {
    setEvaluating(true);
    setResult(null);
    setError(null);

    try {
      const request = {
        force_recalculate: forceRecalculate,
      };

      const response = await api.admin.bulkEvaluate(request);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : '진단 실행 중 오류가 발생했습니다');
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 안내 메시지 */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-800">
            <p className="font-medium mb-1">대량 진단 안내</p>
            <ul className="list-disc list-inside space-y-1 text-yellow-700">
              <li>모든 학생-학과 조합에 대한 진단 결과를 미리 계산하여 저장합니다</li>
              <li>학생 수와 학과 수에 따라 시간이 오래 걸릴 수 있습니다</li>
              <li>강제 재계산 옵션을 선택하면 기존 캐시를 무시하고 재계산합니다</li>
            </ul>
          </div>
        </div>
      </div>

      {/* 진단 실행 */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-3 mb-6">
          <Activity className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">전체 학생 진단</h3>
        </div>

        <div className="space-y-6">
          {/* 설명 */}
          <div className="bg-blue-50 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              모든 학생에 대해 모든 학과의 전공 적합도를 진단합니다.
              진단 결과는 캐시되어 빠른 조회가 가능합니다.
            </p>
          </div>

          {/* 강제 재계산 옵션 */}
          <div className="flex items-start gap-3 p-4 border border-gray-200 rounded-lg">
            <input
              type="checkbox"
              id="force-recalculate"
              checked={forceRecalculate}
              onChange={(e) => setForceRecalculate(e.target.checked)}
              className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
              disabled={evaluating}
            />
            <div className="flex-1">
              <label htmlFor="force-recalculate" className="text-sm font-medium text-gray-900 cursor-pointer block mb-1">
                강제 재계산
              </label>
              <p className="text-xs text-gray-600">
                기존에 캐시된 진단 결과를 무시하고 모든 데이터를 다시 계산합니다.
                진단 알고리즘이나 과목 데이터가 변경된 경우에 사용하세요.
              </p>
            </div>
          </div>

          {/* 실행 버튼 */}
          <button
            onClick={handleEvaluate}
            disabled={evaluating}
            className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-semibold text-lg shadow-lg hover:shadow-xl"
          >
            {evaluating ? (
              <>
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                <span>진단 실행 중...</span>
              </>
            ) : (
              <>
                <Play className="h-6 w-6" />
                <span>전체 진단 실행</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 결과 표시 */}
      {result && (
        <div
          className={`bg-white rounded-lg shadow p-6 ${
            result.success ? 'border-l-4 border-green-500' : 'border-l-4 border-red-500'
          }`}
        >
          <div className="flex items-start gap-3 mb-4">
            {result.success ? (
              <CheckCircle className="h-6 w-6 text-green-600 flex-shrink-0" />
            ) : (
              <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0" />
            )}
            <div className="flex-1">
              <h4
                className={`text-lg font-semibold ${
                  result.success ? 'text-green-800' : 'text-red-800'
                }`}
              >
                {result.message}
              </h4>
            </div>
          </div>

          {result.success && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-blue-600 font-medium mb-1">총 학생</p>
                <p className="text-2xl font-bold text-blue-900">{result.total_students}</p>
              </div>
              <div className="bg-purple-50 rounded-lg p-4">
                <p className="text-sm text-purple-600 font-medium mb-1">총 학과</p>
                <p className="text-2xl font-bold text-purple-900">{result.total_departments}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 font-medium mb-1">총 진단</p>
                <p className="text-2xl font-bold text-gray-900">{result.total_evaluations}</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-sm text-green-600 font-medium mb-1">성공</p>
                <p className="text-2xl font-bold text-green-900">{result.success_count}</p>
              </div>
              <div className="bg-red-50 rounded-lg p-4">
                <p className="text-sm text-red-600 font-medium mb-1">실패</p>
                <p className="text-2xl font-bold text-red-900">{result.error_count}</p>
              </div>
            </div>
          )}

          {result.errors && result.errors.length > 0 && (
            <div className="mt-4 p-4 bg-red-50 rounded-lg">
              <p className="text-sm font-medium text-red-800 mb-2">
                ⚠️ 오류 목록 ({result.errors.length}건)
              </p>
              <ul className="text-sm text-red-700 space-y-1 max-h-40 overflow-y-auto">
                {result.errors.slice(0, 10).map((error, index) => (
                  <li key={index} className="pl-4 border-l-2 border-red-300">
                    {error}
                  </li>
                ))}
                {result.errors.length > 10 && (
                  <li className="text-red-600 italic">
                    ...외 {result.errors.length - 10}건
                  </li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 에러 표시 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-800">오류 발생</p>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
