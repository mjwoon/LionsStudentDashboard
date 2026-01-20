## 1. 학생 관리

| **메서드** | **엔드포인트** | **설명** |
| --- | --- | --- |
| `GET` | `/api/students` | 학생 목록 조회 (필터링) |
| `GET` | `/api/students/{student_id}` | 특정 학생 상세 프로필 |
| `GET` | `/api/students/{student_id}/courses` | 학생 수강 이력 조회 |
| `GET` | `/api/students/{student_id}/surveys` | 학생의 전공 희망 조사 이력 |
| `POST` | `/api/students` | 신규 학생 등록 |

### GET : /api/students

```json
{
  "count": 150,       // 전체 검색 결과 수 (페이징 계산용)
  "page": 1,          // 현재 페이지
  "per_page": 20,     // 페이지당 표시 개수
  "students": [
    {
      "student_id": "202412001",
      "name": "김철수",
      "email": "chulsoo@univ.ac.kr",
      "phone": "010-1234-5678",
      "department": {
        "id": 101,
        "name": "자율전공학부" // DB Join을 통해 학과명 제공
      },
      "academic_info": {
        "pride": "LIONSE",   // DB 컬럼: pride
        "class": 2,          // DB 컬럼: class (분반)
        "advisor_name": "박교수", // DB Join을 통해 지도교수 이름 제공
        "status": "재학"     // (옵션) 학적 상태
      }
    },
    {
      "student_id": "202412005",
      "name": "이영희",
      "email": "young@univ.ac.kr",
      "phone": "010-9876-5432",
      "department": {
        "id": 101,
        "name": "자율전공학부"
      },
      "academic_info": {
        "pride": "LIONSE",
        "class": 1,
        "advisor_name": "최교수",
        "status": "휴학"
      }
    }
  ]
}
```

### GET : /api/students/{student_id}

```json
{
  "student_id": "2024123112",
  "name": "김철수",
  "email": "chulsoo@hanyang.ac.kr",
  "phone": "010-1234-5678",
  "department": {
    "id": 101,
    "name": "자연계열" // 자연계열, 전계열, 인문사회계열
  },
  "academic_info": {
    "pride": "L",  // LIONSE 중에 하나
    "class": 2,
    "advisor_id": 5,
    "advisor_name": "박교수", 
    "updated_at": "2024-10-20T14:30:00Z"
  }
}
```

### GET : /api/students/{student_id}/courses

```json
{
  "student_id": "2024123123",
  "total_credits": 18,
  "course_history": [
    {
      "course_id": 12334,
      "course_code": "CSE101",
      "course_name": "프로그래밍 기초",
      "credits": 3,
      "year": 2024,
      "semester": 1,
      "completion_type": "전공필수",
      "is_entry_requirement": true,
      "is_retake": false
    },
    {
      "course_id": 15123,
      "course_code": "MATH102",
      "course_name": "미적분학",
      "credits": 3,
      "year": 2024,
      "semester": 1,
      "completion_type": "전공기초",
      "is_entry_requirement": false,
      "is_retake": true
    }
  ]
}
```

### GET : /api/students/{student_id}/surveys

```json
{
  "history": [
    {
      "survey_id": 55,
      "round": 2, // 2차 조사
      "submitted_at": "2024-10-15",
      "first_choice": { "id": 201, "name": "컴퓨터공학과" },
      "second_choice": { "id": 205, "name": "전자공학과" },
      "decision_scale": 4 // 5점 만점 중 4점
    },
    {
      "survey_id": 12,
      "round": 1, // 1차 조사
      "submitted_at": "2024-04-10",
      "first_choice": { "id": 201, "name": "컴퓨터공학과" },
      "second_choice": { "id": 301, "name": "경영학과" },
      "decision_scale": 2
    }
  ]
}
```

### POST : /api/students

```json
// Request Body
{
  "student_id": "20250001",
  "name": "신입생",
  "email": "new@univ.ac.kr",
  "phone": "010-0000-0000",
  "department_id": 100, // 전계열
  "advisor_id": 3,
  "pride": "E",
  "class": 1
}

// Response Body (201 Created)
{
  "message": "학생이 성공적으로 등록되었습니다.",
  "student_id": "20250001"
}
```

## 2. 과목 및 교육과정

| **메서드** | **엔드포인트** | **설명** |
| --- | --- | --- |
| `GET` | `/api/courses` | 전체 과목 목록 (유형별 필터) |
| `GET` | `/api/courses/entry-requirements` | **전공 진입 필수 과목** 목록 |
| `GET` | `/api/departments` | 학과 리스트 및 졸업 학점 확인 |
| `GET` | `/api/departments/{id}/courses` | 특정 학과 관장 과목 조회 |

### GET /api/courses

```json
{
  "count": 120, // 전체 검색 결과 수
  "page": 1, // 현재 페이지 번호
  "per_page": 20, // 페이지당 표시 개수
  "courses": [
    {
      "course_id": 101,
      "course_code": "CSE202",
      "course_name": "알고리즘",
      "credits": 3,
      "course_type": "전공필수", // 전공기초, 전공선택, 교양 등
      "department": {
        "id": 201,
        "name": "컴퓨터공학과" // JOIN을 통해 학과명 제공
      },
      "flags": {
        "is_entry_requirement": true, // 전공 진입 필수 요건 여부
        "is_recommended": true,       // 권장 과목 여부
        "is_retake_only": false       // (옵션) 재수강 전용 반 여부 등
      },
      "description": "알고리즘의 기초 개념과 복잡도 분석을 다룹니다." // (옵션) 강의 설명
    },
    {
      "course_id": 305,
      "course_code": "GEN001",
      "course_name": "글쓰기와 토론",
      "credits": 2,
      "course_type": "교양필수",
      "department": {
        "id": 100,
        "name": "교양대학"
      },
      "flags": {
        "is_entry_requirement": false,
        "is_recommended": false,
        "is_retake_only": false
      }
    }
  ]
}
```

### GET : /api/courses?type=entry

```json
{
  "count": 10, //  조회된 과목 총 개수
  "courses": [
    {
      "course_id": 1,
      "course_code": "CSE101",
      "course_name": "데이터구조",
      "credits": 3,
      "course_type": "전공핵심",
      "department_name": "컴퓨터공학과",
      "is_entry_requirement": true,
      "is_recommended": true
    }
  ]
}
```

### GET : /api/courses/entry-requirements

```json
{
  "count": 3, // 전공진입 요건 수업 총 개수
  "courses": [
    {
      "course_id": 10,
      "course_code": "CSE101",
      "course_name": "프로그래밍 기초",
      "credits": 3,
      "course_type": "전공기초",
      "department_id": 201,
      "department_name": "컴퓨터공학과", // 이 과목이 어느 학과의 진입 요건인지 명시
      "is_recommended": true // 권장 과목 여부
    },
    {
      "course_id": 55,
      "course_code": "MATH101",
      "course_name": "미적분학 1",
      "credits": 3,
      "course_type": "기초과학",
      "department_id": 201,
      "department_name": "컴퓨터공학과",
      "is_recommended": false
    },
    {
      "course_id": 82,
      "course_code": "MGT201",
      "course_name": "경영학원론",
      "credits": 3,
      "course_type": "전공필수",
      "department_id": 205,
      "department_name": "경영학과",
      "is_recommended": true
    }
  ]
}
```

### GET : /api/departments

```json
{
  "count": 4,
  "departments": [
    {
      "id": 201,
      "code": "CSE",
      "name": "컴퓨터공학과",
      "college_name": "공과대학", // departments 테이블의 college_id를 조인해서 가져온 이름
      "min_credits": 130, // 졸업 이수 최소 학점 (DB 컬럼: min_credits)
      "homepage_url": "https://cs.univ.ac.kr" // (옵션) 학과 홈페이지 등
    },
    {
      "id": 205,
      "code": "BIZ",
      "name": "경영학과",
      "college_name": "경영대학",
      "min_credits": 126
    },
    {
      "id": 208,
      "code": "ME",
      "name": "기계공학과",
      "college_name": "공과대학",
      "min_credits": 135
    },
    {
      "id": 100,
      "code": "LIONSE",
      "name": "자율전공학부",
      "college_name": "라이언스 칼리지",
      "min_credits": 130
    }
  ]
}
```

### GET : /api/departments/{id}/curriculum

```json
{
  "department_name": "컴퓨터공학과",
  "graduation_min_credits": 130,
  "tracks": [
    "AI 트랙", "웹개발 트랙", "보안 트랙"
  ],
  "entry_requirements_description": "전공기초 3과목 중 2과목 이상 이수 및 평점 3.0 이상"
}
```

## 3. 전공 희망 조사 및 분석

| **메서드** | **엔드포인트** | **설명** |
| --- | --- | --- |
| `GET` | `/api/surveys/summary` | 회차별 전공 희망 통계 |
| `GET` | `/api/major-surveys/rounds/{round_id}` | 특정 회차(1차, 2차 등) 조사 결과 |
| `POST` | `/api/surveys` | 학생의 전공 희망 설문 제출 |

### GET : /api/surveys/summary

```json
{
  "overview": {
    "total_students": 250,
    "total_departments": 3,
    "entry_requirement_completion_rate": 68.5
  },
  "major_preferences": [
    { "dept_name": "컴퓨터공학과", "count": 150, "avg_decision_scale": 4.2 },
    { "dept_name": "경영학과", "count": 120, "avg_decision_scale": 3.8 },
    { "dept_name": "전자공학과", "count": 95, "avg_decision_scale": 4.5 }
  ],
  "survey_status": {
    "current_round": 2,
    "participation_rate": 85.0
  }
}
```

### POST : /api/surveys

**Request Body**

```json
{
  "student_id": "2024123112",
  "first_choice_dept_id": 201,  // 1지망 학과 ID
  "second_choice_dept_id": 205, // 2지망 학과 ID (선택 사항일 경우 null 가능)
  "survey_round": 2,            // 현재 진행 중인 설문 회차
  "decision_scale": 4           // 학생이 선택한 결정도 (1~5)
}
```

**Response Body (Success 201)**

```json
{
  "success": true,
  "message": "설문이 성공적으로 제출되었습니다.",
  "data": {
    "survey_id": 1055,          // 생성된 설문 데이터의 PK
    "submitted_at": "2024-11-20T15:30:00Z"
  }
}
```

### GET : /api/major-surveys/rounds/{round_id}?page=1&limit=20

```json
{
  "meta": {
    "total_count": 125,       // 전체 설문 제출 학생 수 (100명 이상)
    "current_page": 1,        // 현재 페이지 번호
    "total_pages": 7,         // 전체 페이지 수 (125명 / 20명씩 = 7페이지)
    "per_page": 20            // 한 페이지당 보여줄 데이터 수
  },
  "round_info": {
    "round_id": 2,
    "title": "2024학년도 2차 전공희망조사",
    "status": "CLOSED"
  },
  "submissions": [
    // 1번 학생
    {
      "survey_id": 501,
      "student_id": "202412001",
      "name": "김철수",
      "department_name": "자율전공학부",
      "first_choice": { "id": 201, "name": "컴퓨터공학과" },
      "second_choice": { "id": 205, "name": "경영학과" },
      "decision_scale": 5,
      "submitted_at": "2024-11-20T10:00:00Z"
    },
    // ... (중략) ...
    // 20번 학생 (한 페이지의 마지막 데이터)
    {
      "survey_id": 520,
      "student_id": "202412020",
      "name": "박민수",
      "department_name": "자율전공학부",
      "first_choice": { "id": 208, "name": "기계공학과" },
      "second_choice": { "id": 201, "name": "컴퓨터공학과" },
      "decision_scale": 3,
      "submitted_at": "2024-11-20T11:15:00Z"
    }
  ]
}
```

