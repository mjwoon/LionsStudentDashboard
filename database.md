**데이터 구조**

기초정보 및 학과 테이블

```sql
-- 1. 단과대 테이블
CREATE TABLE colleges (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- 2. 학과 테이블
CREATE TABLE departments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL UNIQUE,
    college_id INT,
    min_credits INT DEFAULT 130, -- 졸업 최소 학점
    FOREIGN KEY (college_id) REFERENCES colleges(id)
);

-- 3. 과목 테이블
CREATE TABLE courses (
    course_id INT PRIMARY KEY AUTO_INCREMENT,
    course_code VARCHAR(20) UNIQUE NOT NULL, -- 과목코드 (예: CSE101)
    course_name VARCHAR(100) NOT NULL,
    credits INT NOT NULL,
    course_type VARCHAR(30), -- 전공기초, 전공필수 등
    course_department INT, -- 관장학과
    course_year INT NOT NULL, -- 권장 학년
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_department) REFERENCES departments(id)
);
```

학생 및 수강기록

```sql
-- 4. 학생 테이블
CREATE TABLE students (
    student_id VARCHAR(10) PRIMARY KEY, -- 학번
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    department_id INT NOT NULL, -- 현재 소속 (전계열, 자연계 등)
    advisor_id INT,
    pride VARCHAR(10), -- LIONSE 등급 등
    class INT, -- 분반
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- 5. 학생 수강과목 테이블
CREATE TABLE student_courses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(10) NOT NULL,
    course_id INT NOT NULL,
    grade VARCHAR(5) NOT NULL, -- A+, B0, F 등
    numeric_grade DECIMAL(3,2), -- 4.5, 3.0 등 계산용 점수
    
    year INT NOT NULL, -- 수강 연도
    semester INT NOT NULL, -- 수강 학기
    
    completion_type VARCHAR(20) NOT NULL, -- 이수구분 (수강생 기준)
    is_retake BOOLEAN DEFAULT FALSE, -- 재수강 여부
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);
```

희망전공 조사 관련

```sql
-- 6. 결정 상태 코드 테이블
CREATE TABLE decision_statuses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    status_name VARCHAR(50) NOT NULL -- 최종결정, 고민중 등
);

-- 7. 희망전공조사 테이블
CREATE TABLE major_surveys (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(10) NOT NULL,
    
    survey_round INT NOT NULL, -- 1회차, 2회차
    first_choice_id INT NOT NULL, -- 1지망 학과 ID
    second_choice_id INT NOT NULL, -- 2지망 학과 ID
    
    decision_status_id INT,
    decision_scale INT, -- 리커트 척도 (1~5)
    
    survey_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (first_choice_id) REFERENCES departments(id),
    FOREIGN KEY (second_choice_id) REFERENCES departments(id),
    FOREIGN KEY (decision_status_id) REFERENCES decision_statuses(id)
);
```

전공진입 요건 및 진단 캐싱

```sql
-- 8. 학과별 진입 요건 정의 (학년도별/그룹별)
CREATE TABLE department_entry_requirements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    department_id INT NOT NULL,
    
    admission_year INT NOT NULL, -- 적용 학번 (2026 등)
    requirement_group INT NOT NULL, -- 1번 그룹(필수과목군) 등
    
    target_grade_level ENUM('A', 'B', 'C') NOT NULL, -- 기준 성적
    required_count INT NOT NULL, -- 필요한 과목 수
    requirement_text TEXT NOT NULL, -- 사용자 노출용 설명
    is_alert_required BOOLEAN DEFAULT FALSE, -- 설계전공 등 알림창 여부
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- 9. 요건 대상 과목 맵핑
CREATE TABLE requirement_courses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    requirement_id INT NOT NULL,
    course_code VARCHAR(20) NOT NULL,
    FOREIGN KEY (requirement_id) REFERENCES department_entry_requirements(id) ON DELETE CASCADE,
    FOREIGN KEY (course_code) REFERENCES courses(course_code)
);

-- 10. 학생별 진단 결과 캐시 테이블 (성능 최적화 및 AI 총평)
CREATE TABLE student_requirement_status (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(10) NOT NULL,
    department_id INT NOT NULL, -- 진단 대상 학과
    is_satisfied BOOLEAN DEFAULT FALSE, -- 최종 충족 여부
    
    -- 진단 상세 데이터 (JSON)
    -- 예: {"completed": 2, "required": 2, "details": [{"code": "MAT101", "grade": "A0"}]}
    analysis_json JSON, 
    
    ai_summary TEXT, -- LLM이 생성한 맞춤형 커멘트
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id),
    UNIQUE KEY unique_student_dept_eval (student_id, department_id)
);
```