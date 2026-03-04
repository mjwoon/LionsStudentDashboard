import { useState, useEffect } from 'react';
import { Trash2, RefreshCw, AlertCircle, CheckCircle, Database } from 'lucide-react';
import { api } from '../api';
import type { CachedEvaluationStats } from '../types';

export default function SystemStatsTab() {
  const [stats, setStats] = useState<CachedEvaluationStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadStats = async () => {
    setLoading(true);
    setMessage(null);
    
    try {
      const data = await api.admin.getEvaluationStats();
      setStats(data);
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : '통계 로드 실패',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async (departmentId?: string) => {
    if (!confirm(departmentId 
      ? '해당 학과의 캐시를 삭제하시겠습니까?' 
      : '전체 캐시를 삭제하시겠습니까?'
    )) {
      return;
    }

    setClearing(true);
    setMessage(null);

    try {
      const result = await api.admin.clearCache(departmentId);
      setMessage({
        type: 'success',
        text: result.message,
      });
      // 통계 새로고침
      await loadStats();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : '캐시 삭제 실패',
      });
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return '-';
    try {
      return new Date(dateString).toLocaleString('ko-KR');
    } catch {
      return dateString;
    }
  };

  return (
    <div className="space-y-6">
      {/* 안내 메시지 */}
      <div className="bg-[#FEF9C3] rounded-lg p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-[#95430E] shrink-0 mt-0.5" />
          <div className="text-sm text-[#95430E]">
            <p className="font-medium mb-1">시스템 현황 안내</p>
            <ul className="list-disc list-inside space-y-1 text-[#95430E]">
              <li>캐시된 진단 결과 현황을 확인할 수 있습니다</li>
              <li>학과별로 캐시된 진단 수를 확인할 수 있습니다</li>
              <li>불필요한 캐시는 삭제하여 공간을 확보할 수 있습니다</li>
            </ul>
          </div>
        </div>
      </div>

      {/* 메시지 표시 */}
      {message && (
        <div
          className={`rounded-lg p-4 ${
            message.type === 'success'
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
          }`}
        >
          <div className="flex items-start gap-2">
            {message.type === 'success' ? (
              <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            )}
            <p
              className={`text-sm font-medium ${
                message.type === 'success' ? 'text-green-800' : 'text-red-800'
              }`}
            >
              {message.text}
            </p>
          </div>
        </div>
      )}

      {/* 통계 요약 */}
      <div className="bg-white rounded-lg border border-[#E5E5E5] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900">캐시 통계</h3>
          </div>
          <button
            onClick={loadStats}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            새로고침
          </button>
        </div>

        {loading && !stats ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : stats ? (
          <div className="space-y-6">
            {/* 전체 통계 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-linear-to-br from-blue-50 to-blue-100 rounded-lg p-6">
                <p className="text-sm text-blue-600 font-medium mb-2">총 캐시된 진단 수</p>
                <p className="text-4xl font-bold text-blue-900">{stats.total_cached.toLocaleString()}</p>
              </div>
              <div className="bg-linear-to-br from-purple-50 to-purple-100 rounded-lg p-6">
                <p className="text-sm text-purple-600 font-medium mb-2">마지막 업데이트</p>
                <p className="text-lg font-semibold text-purple-900">
                  {formatDate(stats.last_update)}
                </p>
              </div>
            </div>

            {/* 전체 캐시 삭제 */}
            <div className="flex items-center justify-between p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-3">
                <Trash2 className="h-5 w-5 text-red-600" />
                <div>
                  <p className="font-medium text-red-900">전체 캐시 삭제</p>
                  <p className="text-sm text-red-700">모든 학과의 캐시를 삭제합니다</p>
                </div>
              </div>
              <button
                onClick={() => handleClearCache()}
                disabled={clearing || stats.total_cached === 0}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {clearing ? '삭제 중...' : '전체 삭제'}
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {/* 학과별 통계 */}
      {stats && stats.cached_by_department && Object.keys(stats.cached_by_department).length > 0 && (
        <div className="bg-white rounded-lg p-6 border-1 border-[#E5E5E5]">
          <div className="flex items-center gap-3 mb-6">
            <h3 className="text-lg font-semibold text-gray-900">학과별 캐시 현황</h3>
          </div>

          <div className="space-y-3">
            {Object.entries(stats.cached_by_department)
              .sort(([, a], [, b]) => b - a)
              .map(([department, count]) => {
                const percentage = stats.total_cached > 0 
                  ? ((count / stats.total_cached) * 100).toFixed(1)
                  : '0';
                
                return (
                  <div key={department} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="font-medium text-gray-900">{department}</h4>
                          <span className="text-sm text-gray-500">
                            {count.toLocaleString()}개 ({percentage}%)
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-[#0F4A84] h-2 rounded-full transition-all"
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                      </div>
                      {/* 개별 삭제 기능은 department_id가 필요하므로 주석 처리
                      <button
                        onClick={() => handleClearCache(departmentId)}
                        disabled={clearing}
                        className="ml-4 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="이 학과의 캐시 삭제"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                      */}
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* 캐시가 없을 때 */}
      {stats && stats.total_cached === 0 && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Database className="h-16 w-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">캐시된 진단 결과가 없습니다</h3>
          <p className="text-gray-600 mb-4">
            진단 관리 탭에서 대량 진단을 실행하면 결과가 캐시됩니다
          </p>
        </div>
      )}
    </div>
  );
}
