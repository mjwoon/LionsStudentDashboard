import { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell, PieChart, Pie } from 'recharts';
import { TrendingUp, Users, Download, ChevronDown } from 'lucide-react';
import { api } from '../api';

export default function DashboardView() {
  const [selectedCollege, setSelectedCollege] = useState('all');
  const [selectedDepts, setSelectedDepts] = useState<string[]>(['cs', 'ee', 'bio', 'business']);
  const [showTopN, setShowTopN] = useState(10);
  const [loading, setLoading] = useState(true);
  const [colleges, setColleges] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [currentData, setCurrentData] = useState<any[]>([]);
  const [trendData, setTrendData] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const data = await api.dashboard.stats();
        
        // Add 'all' option to colleges
        const collegesWithAll = [
          { id: 'all', name: '전체' },
          ...data.colleges.map(c => ({ id: c.name, name: c.name }))
        ];
        
        // Map college names to IDs
        const collegeMap: Record<string, string> = {
          '공과대학': 'engineering',
          '자연과학대학': 'science',
          '경영대학': 'business',
          '인문대학': 'humanities',
          '사회과학대학': 'social'
        };
        
        const mappedColleges = collegesWithAll.map(c => ({
          id: c.id === 'all' ? 'all' : collegeMap[c.name] || c.id,
          name: c.name
        }));
        
        setColleges(mappedColleges);
        setDepartments(data.departments);
        setCurrentData(data.current_data.map(d => ({
          dept: d.name,
          students: d.students,
          percent: d.percent,
          id: d.id
        })));
        
        // Convert trend data to format expected by chart
        const formattedTrend = data.trend_data.map(t => ({
          period: t.period,
          ...t.data
        }));
        setTrendData(formattedTrend);
        
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen flex items-center justify-center">
        <div className="text-gray-600">데이터를 불러오는 중...</div>
      </div>
    );
  }

  // 단과대학별로 필터링
  const filteredDepartments = selectedCollege === 'all' 
    ? departments 
    : departments.filter((d) => d.college === selectedCollege);

  // 현재 데이터 필터링
  const filteredCurrentData = currentData
    .filter((d) => {
      const dept = departments.find((dep) => dep.id === d.id);
      return selectedCollege === 'all' || dept?.college === selectedCollege;
    })
    .slice(0, showTopN);

  const handleDeptToggle = (deptId: string) => {
    setSelectedDepts((prev) =>
      prev.includes(deptId)
        ? prev.filter((id) => id !== deptId)
        : [...prev, deptId]
    );
  };

  const downloadCSV = () => {
    const csv = [
      ['학과', '학생 수', '비율(%)'],
      ...filteredCurrentData.map((d) => [d.dept, d.students, d.percent])
    ].map((row) => row.join(',')).join('\n');
    
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', '희망학과_통계.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const totalStudents = filteredCurrentData.reduce((sum, d) => sum + d.students, 0);

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">대시보드</h1>
        <p className="text-gray-600">학과별 희망 학생 현황 및 트렌드를 확인할 수 있습니다.</p>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow-md border-2 border-gray-300 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">총 희망 학생 수</h3>
            <Users className="h-5 w-5 text-blue-600" />
          </div>
          <div className="text-3xl font-bold text-gray-900">{totalStudents}명</div>
          <p className="text-sm text-gray-500 mt-2">전체 학과 기준</p>
        </div>

        <div className="bg-white rounded-lg shadow-md border-2 border-gray-300 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">가장 인기 있는 학과</h3>
            <TrendingUp className="h-5 w-5 text-green-600" />
          </div>
          <div className="text-2xl font-bold text-gray-900">{filteredCurrentData[0]?.dept}</div>
          <p className="text-sm text-gray-500 mt-2">{filteredCurrentData[0]?.students}명 ({filteredCurrentData[0]?.percent}%)</p>
        </div>

        <div className="bg-white rounded-lg shadow-md border-2 border-gray-300 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">전체 학과 수</h3>
            <ChevronDown className="h-5 w-5 text-purple-600" />
          </div>
          <div className="text-3xl font-bold text-gray-900">{departments.length}개</div>
          <p className="text-sm text-gray-500 mt-2">{colleges.length - 1}개 단과대학</p>
        </div>
      </div>


      {/* 필터 영역 */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="flex gap-4 items-center flex-wrap">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">단과대학</label>
            <select 
              value={selectedCollege}
              onChange={(e) => {
                setSelectedCollege(e.target.value);
                setSelectedDepts([]);
              }}
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {colleges.map((college) => (
                <option key={college.id} value={college.id}>
                  {college.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">표시 학과 수</label>
            <select
              value={showTopN}
              onChange={(e) => setShowTopN(Number(e.target.value))}
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={5}>상위 5개</option>
              <option value={10}>상위 10개</option>
              <option value={15}>상위 15개</option>
              <option value={29}>전체</option>
            </select>
          </div>

          <div className="ml-auto">
            <button
              onClick={downloadCSV}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <Download className="h-4 w-4" />
              CSV 다운로드
            </button>
          </div>
        </div>
      </div>

    
      {/* 차트 영역 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* 학과별 희망 학생 수 (Bar Chart) */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">학과별 희망 학생 현황</h2>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={filteredCurrentData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="dept" 
                angle={-45}
                textAnchor="end"
                height={120}
                interval={0}
                tick={{ fontSize: 12 }}
              />
              <YAxis />
              <Tooltip />
              <Bar dataKey="students" name="학생 수">
                {filteredCurrentData.map((entry) => {
                  const dept = departments.find((d) => d.id === entry.id);
                  return <Cell key={entry.id} fill={dept?.color || '#3b82f6'} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 트렌드 차트 */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
        <h2 className="text-lg font-bold text-gray-900 mb-4">시점별 변화 트렌드</h2>
        
        {/* 학과 선택 체크박스 */}
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm font-medium text-gray-700 mb-3">비교할 학과 선택 (최대 5개 권장)</p>
          <div className="flex flex-wrap gap-3">
            {filteredDepartments.slice(0, 15).map((dept) => (
              <label key={dept.id} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedDepts.includes(dept.id)}
                  onChange={() => handleDeptToggle(dept.id)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{dept.name}</span>
              </label>
            ))}
          </div>
        </div>

        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period" />
            <YAxis />
            <Tooltip />
            <Legend />
            {selectedDepts.map((deptId) => {
              const dept = departments.find((d) => d.id === deptId);
              return (
                <Line
                  key={deptId}
                  type="monotone"
                  dataKey={deptId}
                  name={dept?.name}
                  stroke={dept?.color}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 상세 테이블 */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">전체 학과 목록</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  순위
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  학과명
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  학생 수
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  비율
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  진행률
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredCurrentData.map((item, index) => {
                const dept = departments.find((d) => d.id === item.id);
                return (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {index + 1}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: dept?.color }}
                        />
                        <span className="text-sm font-medium text-gray-900">{item.dept}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.students}명
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.percent}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="h-2 rounded-full"
                          style={{ 
                            width: `${item.percent * 3}%`,
                            backgroundColor: dept?.color
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
