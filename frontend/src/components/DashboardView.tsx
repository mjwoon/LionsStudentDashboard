import { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { Download } from 'lucide-react';
import { api } from '../api';

// 학과별 랜덤 색상 팔레트
const COLOR_PALETTE = [
  '#0e4a84', '#1e40af', '#2563eb', '#3b82f6', '#60a5fa',
  '#dc2626', '#ef4444', '#f87171', '#fca5a5', '#fecaca',
  '#7c3aed', '#a855f7', '#c084fc', '#e879f9', '#f0abfc',
  '#059669', '#10b981', '#34d399', '#6ee7b7', '#a7f3d0',
  '#d97706', '#f59e0b', '#fbbf24', '#fcd34d', '#fde68a',
  '#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe', '#e0e7ff',
  '#be123c', '#be185d', '#ec4899', '#f472b6', '#fbbbf9'
];

// 각 학과에 할당된 색상을 추적하는 Map
const departmentColorMap = new Map<string | number, string>();

function getRandomColor(deptId: string | number): string {
  if (departmentColorMap.has(deptId)) {
    return departmentColorMap.get(deptId)!;
  }
  const randomColor = COLOR_PALETTE[Math.floor(Math.random() * COLOR_PALETTE.length)];
  departmentColorMap.set(deptId, randomColor);
  return randomColor;
}

export default function DashboardView() {
  const [selectedSurvey, setSelectedSurvey] = useState('3');
  const [selectedCollege, setSelectedCollege] = useState('all');
  const [checkedColleges, setCheckedColleges] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [colleges, setColleges] = useState<{ id: string | number; name: string }[]>([]);
  const [departments, setDepartments] = useState<{ id: string | number; name: string; college?: string; color?: string }[]>([]);
  const [currentData, setCurrentData] = useState<{ dept: string; students: number; percent: number; id: string | number }[]>([]);
  const [trendData, setTrendData] = useState<Record<string, string | number>[]>([]);
  const [totalStudents, setTotalStudents] = useState(0);
  const [topDept, setTopDept] = useState<{ dept: string; students: number; percent: number } | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const data = await api.dashboard.stats();

        // Filter out college with id=1 (라이언스 칼리지) and add 'all' option
        const filteredColleges = data.colleges.filter(c => c.id !== 1);
        const collegesWithAll = [
          { id: 'all', name: '전체' },
          ...filteredColleges.map(c => ({ id: String(c.id), name: c.name }))
        ];

        setColleges(collegesWithAll);
        // 추세 차트: 첫 번째 단과대학을 기본으로 체크
        if (filteredColleges.length > 0) {
          setCheckedColleges(new Set([String(filteredColleges[0].id)]));
        }
        // 각 학과에 랜덤 색상 할당
        const departmentsWithRandomColors = data.departments.map(d => ({
          ...d,
          color: getRandomColor(d.id)
        }));
        setDepartments(departmentsWithRandomColors);
        console.log('Departments with random colors:', departmentsWithRandomColors.map(d => ({ name: d.name, color: d.color })));

        const formattedCurrent = data.current_data.map(d => ({
          dept: d.name,
          students: d.students,
          percent: d.percent,
          id: d.id
        }));
        setCurrentData(formattedCurrent);

        // Set statistics
        const total = formattedCurrent.reduce((sum, d) => sum + d.students, 0);
        setTotalStudents(total);
        setTopDept(formattedCurrent[0] || null);

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
      <div className="flex items-center justify-center">
        <div className="text-gray-600">데이터를 불러오는 중...</div>
      </div>
    );
  }

  // 추세 차트: 체크된 단과대학에 속한 학과 ID 목록
  const trendDeptIds = departments
    .filter(d => checkedColleges.has(String(d.college)))
    .map(d => String(d.id));

  // 현재 데이터 필터링 (상위 15개로 제한)
  const filteredCurrentData = currentData
    .filter((d) => {
      const dept = departments.find((dep) => dep.id === d.id);
      return selectedCollege === 'all' || dept?.college === selectedCollege;
    })
    .slice(0, 15);

  const downloadData = () => {
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

  return (
    <div className="py-4 md:py-6">
      {/* Title Section */}
      <div className="flex items-start justify-between  mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl lg:text-3xl font-bold text-[#101828]">학과 관심 현황 대시보드</h1>
        </div>
        <button
          onClick={downloadData}
          className="flex items-center gap-2 px-3 md:px-4 py-2 bg-[#0e4a84] text-white rounded-lg hover:bg-[#0a3a6b] transition self-start sm:self-auto"
        >
          <Download className="w-4 h-4 md:w-5 md:h-5" />
          <span className="text-xs md:text-sm font-medium">데이터 다운로드</span>
        </button>
      </div>

      {/*Main body */}
      <div className="flex flex-col gap-4 md:gap-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
          <div className="bg-white rounded-xl border border-black/10 p-3 md:p-4 lg:p-5">
            <div className="flex items-center gap-2 mb-1 md:mb-2">
              <p className="text-[#6a7282] text-xs md:text-sm lg:text-base font-medium">전체 응답 학생</p>
              <p className="text-[#9ca3af] text-[10px] md:text-xs font-medium">3차 조사 기준</p>
            </div>
            <p className="text-[#101828] text-lg md:text-xl lg:text-2xl font-bold">{totalStudents}명</p>
          </div>

          <div className="bg-white rounded-xl border border-black/10 p-3 md:p-4 lg:p-5">
            <div className="flex items-center gap-2 mb-1 md:mb-2">
              <p className="text-[#6a7282] text-xs md:text-sm lg:text-base font-medium">최다 희망 학과</p>
              <p className="text-[#9ca3af] text-[10px] md:text-xs font-medium">{topDept?.students}명 ({topDept?.percent}%)</p>
            </div>
            <p className="text-[#101828] text-lg md:text-xl lg:text-2xl font-bold">{topDept?.dept || '-'}</p>
          </div>

          <div className="bg-white rounded-xl border border-black/10 p-3 md:p-4 lg:p-5 sm:col-span-2 lg:col-span-1">
            <div className="flex items-center gap-2 mb-1 md:mb-2">
              <p className="text-[#6a7282] text-xs md:text-sm lg:text-base font-medium">조사 진행률</p>
              <p className="text-[#9ca3af] text-[10px] md:text-xs font-medium">2025.11.06 기준</p>
            </div>
            <p className="text-[#101828] text-lg md:text-xl lg:text-2xl font-bold">3차 조사 완료</p>
          </div>
        </div>

        {/* Department Ratio Chart */}
        <div className="bg-white rounded-2xl border border-black/10 p-4 md:p-5 lg:p-7">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 md:mb-8">
            <h2 className="text-lg md:text-xl lg:text-[16pt] font-semibold text-[#101828]">학과별 희망 학생 비율</h2>
            <div className="flex flex-wrap gap-2">
              <select
                value={selectedSurvey}
                onChange={(e) => setSelectedSurvey(e.target.value)}
                className="px-3 md:px-4 py-2 md:py-3 bg-white border border-black/10 rounded-lg text-[#101828] text-sm md:text-base lg:text-lg font-medium cursor-pointer hover:border-black/20 transition"
              >
                <option value="1">1차 조사</option>
                <option value="2">2차 조사</option>
                <option value="3">3차 조사</option>
              </select>
              <select
                value={selectedCollege}
                onChange={(e) => {
                  setSelectedCollege(e.target.value);
                }}
                className="px-3 md:px-4 py-2 md:py-3 bg-white border border-black/10 rounded-lg text-[#101828] text-sm md:text-base lg:text-lg font-medium cursor-pointer hover:border-black/20 transition w-32 md:w-40 lg:w-44"
              >
                {colleges.map((college) => (
                  <option key={college.id} value={college.id}>
                    {college.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="h-[300px] md:h-[350px] lg:h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={filteredCurrentData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="dept"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  tick={{ fontSize: 10, fill: '#6a7282' }}
                  interval={0}
                />
                <YAxis tick={{ fontSize: 10, fill: '#6a7282' }} />
                <Tooltip />
                <Bar dataKey="students" fill="#0e4a84" radius={[8, 8, 0, 0]}>
                  {filteredCurrentData.map((entry) => {
                    const dept = departments.find((d) => d.id === entry.id);
                    return <Cell key={entry.id} fill={dept?.color || '#0e4a84'} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Trend Chart */}
        <div className="bg-white rounded-2xl border border-black/10 p-4 md:p-5 lg:p-7">
          <div className="mb-6 md:mb-8">
            <h2 className="text-lg md:text-xl lg:text-2xl font-semibold text-[#101828] mb-2">시점별 변화 추세</h2>
          </div>

          {/* College Selection */}
          <div className="mb-6 flex gap-2 flex-wrap">
            {colleges.filter(c => c.id !== 'all').map((college) => (
              <label key={college.id} className="flex items-center gap-1.5 md:gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checkedColleges.has(String(college.id))}
                  onChange={(e) => {
                    setCheckedColleges(prev => {
                      const next = new Set(prev);
                      if (e.target.checked) next.add(String(college.id));
                      else next.delete(String(college.id));
                      return next;
                    });
                  }}
                  className="w-3.5 h-3.5 md:w-4 md:h-4 rounded border-gray-300"
                />
                <span className="text-sm md:text-base lg:text-lg text-[#101828]">{college.name}</span>
              </label>
            ))}
          </div>

          <div className="h-[300px] md:h-[350px] lg:h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="period" tick={{ fontSize: 12, fill: '#6a7282' }} />
                <YAxis tick={{ fontSize: 12, fill: '#6a7282' }} />
                <Tooltip />
                <Legend />
                {trendDeptIds.map((deptId) => {
                  const dept = departments.find((d) => String(d.id) === deptId);
                  return (
                    <Line
                      key={deptId}
                      type="monotone"
                      dataKey={deptId}
                      stroke={dept?.color || getRandomColor(deptId)}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      name={dept?.name}
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
