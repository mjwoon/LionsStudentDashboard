import { useState } from 'react';
import { Upload, Activity, BarChart } from 'lucide-react';
import DataUploadTab from './DataUploadTab';

type TabType = 'upload' | 'diagnosis' | 'stats';

export default function AdminView() {
  const [activeTab, setActiveTab] = useState<TabType>('upload');

  const tabs = [
    { id: 'upload' as TabType, label: '데이터 업로드', icon: Upload },
    { id: 'diagnosis' as TabType, label: '진단 관리', icon: Activity },
    { id: 'stats' as TabType, label: '시스템 현황', icon: BarChart },
  ];

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* 헤더 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">관리자</h1>
          <p className="text-gray-600">
            데이터 업로드, 진단 관리 및 시스템 현황을 확인할 수 있습니다
          </p>
        </div>

        {/* 탭 네비게이션 */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-6 py-4 border-b-2 font-medium text-sm transition-colors ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        {/* 탭 컨텐츠 */}
        <div>
          {activeTab === 'upload' && <DataUploadTab />}
          {activeTab === 'diagnosis' && (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              <Activity className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-lg font-medium mb-2">진단 관리</p>
              <p className="text-sm">곧 구현 예정입니다</p>
            </div>
          )}
          {activeTab === 'stats' && (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              <BarChart className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-lg font-medium mb-2">시스템 현황</p>
              <p className="text-sm">곧 구현 예정입니다</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
