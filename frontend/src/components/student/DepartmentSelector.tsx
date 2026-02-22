import type { Department } from '../../types';

interface DepartmentSelectorProps {
  departments: Department[];
  selectedCollege: string;
  selectedDepartmentId: string | null;
  onCollegeChange: (college: string) => void;
  onDepartmentChange: (departmentId: string) => void;
}

export default function DepartmentSelector({
  departments,
  selectedCollege,
  selectedDepartmentId,
  onCollegeChange,
  onDepartmentChange,
}: DepartmentSelectorProps) {
  // 고유한 단과대학 목록 추출 (라이언스 제외 필터 유지)
  const uniqueColleges = Array.from(new Set(departments.map(d => d.college_name)))
    .filter(college => college && !college.includes('라이언스') && !college.toLowerCase().includes('lions'));

  // 현재 선택된 단과대학에 속한 학과 필터링
  const filteredDepartments = departments.filter(d => !selectedCollege || d.college_name === selectedCollege);

  return (
    <div className="flex gap-[12px] mt-2">
      <div className="flex flex-col gap-[10px]">
        <label className="block text-[18px] text-[#6a7282]">단과대학</label>
        <div className="relative">
          <select
            className="w-[200px] h-[56px] px-5 border border-black/10 rounded-lg text-[16px] text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84] appearance-none"
            value={selectedCollege}
            onChange={(e) => {
              const newCollege = e.target.value;
              onCollegeChange(newCollege);
              onDepartmentChange('');
            }}
          >
            <option value="">전체</option>
            {uniqueColleges.map((college) => (
              <option key={college} value={college}>{college}</option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-[17px] flex items-center">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M4 6L8 10L12 6" stroke="#666666" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
      </div>
      
      <div className="flex flex-col gap-[10px]">
        <label className="block text-[18px] text-[#6a7282]">학과</label>
        <div className="relative">
          <select
            className="w-[200px] h-[56px] px-5 border border-black/10 rounded-lg text-[16px] text-[#101828] focus:outline-none focus:ring-2 focus:ring-[#0e4a84] disabled:bg-gray-100 disabled:text-gray-400 appearance-none"
            value={selectedDepartmentId || ''}
            onChange={(e) => onDepartmentChange(e.target.value)}
            disabled={!selectedCollege}
          >
            <option value="">학과를 선택하세요</option>
            {filteredDepartments.map((dept) => (
              <option key={dept.id} value={dept.id}>{dept.name}</option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-[17px] flex items-center">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M4 6L8 10L12 6" stroke={!selectedCollege ? "#CCCCCC" : "#666666"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
