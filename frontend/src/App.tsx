import { useState, useEffect } from 'react'
import './App.css'
import { api } from './api'
import type { Student, Department, SurveySummaryResponse } from './api'

function App() {
  const [activeTab, setActiveTab] = useState<'students' | 'departments' | 'surveys'>('students')
  const [students, setStudents] = useState<Student[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [surveySummary, setSurveySummary] = useState<SurveySummaryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch Students
  const fetchStudents = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.students.list(1, 10)
      setStudents(data.students)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  // Fetch Departments
  const fetchDepartments = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.departments.list()
      setDepartments(data.departments)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  // Fetch Survey Summary
  const fetchSurveySummary = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.surveys.summary()
      setSurveySummary(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  // Load data when tab changes
  useEffect(() => {
    if (activeTab === 'students') {
      fetchStudents()
    } else if (activeTab === 'departments') {
      fetchDepartments()
    } else if (activeTab === 'surveys') {
      fetchSurveySummary()
    }
  }, [activeTab])

  return (
    <div className="app">
      <header className="header">
        <h1>🦁 Lions Student Dashboard</h1>
        <p>Backend API Testing Interface</p>
      </header>

      <div className="tabs">
        <button 
          className={activeTab === 'students' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('students')}
        >
          학생 관리
        </button>
        <button 
          className={activeTab === 'departments' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('departments')}
        >
          학과 정보
        </button>
        <button 
          className={activeTab === 'surveys' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('surveys')}
        >
          전공 희망 조사
        </button>
      </div>

      <div className="content">
        {loading && <div className="loading">Loading...</div>}
        {error && <div className="error">Error: {error}</div>}

        {/* Students Tab */}
        {activeTab === 'students' && !loading && (
          <div className="students-section">
            <h2>학생 목록</h2>
            <button onClick={fetchStudents} className="refresh-btn">🔄 새로고침</button>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>학번</th>
                    <th>이름</th>
                    <th>이메일</th>
                    <th>학과</th>
                    <th>PRIDE</th>
                    <th>분반</th>
                    <th>지도교수</th>
                    <th>상태</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => (
                    <tr key={student.student_id}>
                      <td>{student.student_id}</td>
                      <td>{student.name}</td>
                      <td>{student.email}</td>
                      <td>{student.department.name}</td>
                      <td>{student.academic_info.pride}</td>
                      <td>{student.academic_info.class_number}</td>
                      <td>{student.academic_info.advisor_name || '-'}</td>
                      <td>
                        <span className={`status ${student.academic_info.status}`}>
                          {student.academic_info.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Departments Tab */}
        {activeTab === 'departments' && !loading && (
          <div className="departments-section">
            <h2>학과 목록</h2>
            <button onClick={fetchDepartments} className="refresh-btn">🔄 새로고침</button>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>학과 코드</th>
                    <th>학과명</th>
                    <th>단과대학</th>
                    <th>졸업 최소 학점</th>
                  </tr>
                </thead>
                <tbody>
                  {departments.map((dept) => (
                    <tr key={dept.id}>
                      <td>{dept.code}</td>
                      <td>{dept.name}</td>
                      <td>{dept.college_name}</td>
                      <td>{dept.min_credits}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Surveys Tab */}
        {activeTab === 'surveys' && !loading && surveySummary && (
          <div className="surveys-section">
            <h2>전공 희망 조사 통계</h2>
            <button onClick={fetchSurveySummary} className="refresh-btn">🔄 새로고침</button>
            
            <div className="stats-grid">
              <div className="stat-card">
                <h3>전체 학생 수</h3>
                <p className="stat-value">{surveySummary.overview.total_students}</p>
              </div>
              <div className="stat-card">
                <h3>학과 수</h3>
                <p className="stat-value">{surveySummary.overview.total_departments}</p>
              </div>
              <div className="stat-card">
                <h3>진입 요건 완료율</h3>
                <p className="stat-value">{surveySummary.overview.entry_requirement_completion_rate}%</p>
              </div>
              <div className="stat-card">
                <h3>참여율</h3>
                <p className="stat-value">{surveySummary.survey_status.participation_rate}%</p>
              </div>
            </div>

            <h3>학과별 선호도</h3>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>학과명</th>
                    <th>지원자 수</th>
                    <th>평균 확신도</th>
                  </tr>
                </thead>
                <tbody>
                  {surveySummary.major_preferences.map((pref, idx) => (
                    <tr key={idx}>
                      <td>{pref.dept_name}</td>
                      <td>{pref.count}</td>
                      <td>{pref.avg_decision_scale.toFixed(1)} / 5.0</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
