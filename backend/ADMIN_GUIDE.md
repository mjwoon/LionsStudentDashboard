# 관리자용 모듈 가이드

## 개요

관리자용 모듈은 데이터 업로드 및 진단 결과 관리를 위한 API를 제공합니다.

## 주요 기능

### 1. 데이터 업로드

새로운 데이터를 업로드하거나 기존 데이터를 업데이트할 수 있습니다.

#### 1.1 과목 데이터 업로드

```bash
# JSON 파일로 업로드
curl -X POST http://localhost:8080/api/admin/upload/courses/file \
  -F "file=@courses.json"

# 직접 데이터 전송
curl -X POST http://localhost:8080/api/admin/upload/courses \
  -H "Content-Type: application/json" \
  -d '[
    {
      "course_code": "CSE101",
      "course_name": "컴퓨터공학개론",
      "credits": 3,
      "course_type": "전공필수",
      "department_code": "CSE",
      "course_year": 1,
      "semester": 1,
      "is_retake_only": false,
      "description": "컴퓨터공학의 기초"
    }
  ]'
```

**courses.json 예시:**
```json
[
  {
    "course_code": "CSE101",
    "course_name": "컴퓨터공학개론",
    "credits": 3,
    "course_type": "전공필수",
    "department_code": "CSE",
    "course_year": 1,
    "semester": 1,
    "is_retake_only": false,
    "description": "컴퓨터공학의 기초"
  },
  {
    "course_code": "MAT101",
    "course_name": "미적분학",
    "credits": 3,
    "course_type": "전공기초",
    "department_code": "MATH",
    "course_year": 1,
    "semester": 1
  }
]
```

#### 1.2 학생 데이터 업로드

```bash
# JSON 파일로 업로드
curl -X POST http://localhost:8080/api/admin/upload/students/file \
  -F "file=@students.json"
```

**students.json 예시:**
```json
[
  {
    "student_id": "2024123456",
    "name": "홍길동",
    "email": "hong@hanyang.ac.kr",
    "phone": "010-1234-5678",
    "department_code": "LION",
    "pride": "L",
    "class_number": 1,
    "track": "자연계열"
  },
  {
    "student_id": "2024123457",
    "name": "김영희",
    "email": "kim@hanyang.ac.kr",
    "department_code": "LION",
    "pride": "I",
    "class_number": 2,
    "track": "인문사회계열"
  }
]
```

#### 1.3 수강 데이터 업로드

```bash
# JSON 파일로 업로드
curl -X POST http://localhost:8080/api/admin/upload/enrollments/file \
  -F "file=@enrollments.json"
```

**enrollments.json 예시:**
```json
[
  {
    "student_id": "2024123456",
    "course_code": "CSE101",
    "year": 2024,
    "semester": 1,
    "completion_type": "전공필수",
    "is_retake": false,
    "grade": "A+",
    "numeric_grade": 4.5
  },
  {
    "student_id": "2024123456",
    "course_code": "MAT101",
    "year": 2024,
    "semester": 1,
    "completion_type": "전공기초",
    "is_retake": false,
    "grade": "A0",
    "numeric_grade": 4.0
  }
]
```

### 2. 진단 결과 관리

#### 2.1 대량 진단 실행

모든 학생의 모든 학과에 대한 진단을 미리 계산하여 저장합니다.

```bash
# 전체 학생, 전체 학과 진단
curl -X POST http://localhost:8080/api/admin/evaluate/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "force_recalculate": false
  }'

# 특정 학생들만 진단
curl -X POST http://localhost:8080/api/admin/evaluate/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "student_ids": ["2024123456", "2024123457"],
    "force_recalculate": true
  }'

# 특정 학과들만 진단
curl -X POST http://localhost:8080/api/admin/evaluate/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "department_ids": [1, 2, 3],
    "force_recalculate": false
  }'
```

**응답 예시:**
```json
{
  "success": true,
  "message": "대량 진단 완료",
  "total_students": 100,
  "total_departments": 5,
  "total_evaluations": 500,
  "success_count": 498,
  "error_count": 2,
  "errors": [
    "학생 2024123456 - 학과 컴퓨터공학과: ..."
  ]
}
```

#### 2.2 진단 결과 통계 조회

```bash
curl -X GET http://localhost:8080/api/admin/evaluate/stats
```

**응답 예시:**
```json
{
  "total_cached": 500,
  "cached_by_department": {
    "컴퓨터공학과": 100,
    "기계공학과": 100,
    "전자공학과": 100,
    "건축학과": 100,
    "디자인학과": 100
  },
  "last_update": "2026-01-28T10:30:00"
}
```

#### 2.3 캐시 삭제

```bash
# 전체 캐시 삭제
curl -X DELETE http://localhost:8080/api/admin/evaluate/cache

# 특정 학과의 캐시만 삭제
curl -X DELETE http://localhost:8080/api/admin/evaluate/cache?department_id=1
```

## Python 스크립트 예제

### 데이터 업로드 스크립트

```python
import requests
import json

# API 엔드포인트
BASE_URL = "http://localhost:8080/api/admin"

def upload_courses(file_path):
    """과목 데이터 업로드"""
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/upload/courses/file",
            files={'file': f}
        )
    return response.json()

def upload_students(file_path):
    """학생 데이터 업로드"""
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/upload/students/file",
            files={'file': f}
        )
    return response.json()

def upload_enrollments(file_path):
    """수강 데이터 업로드"""
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/upload/enrollments/file",
            files={'file': f}
        )
    return response.json()

# 사용 예시
if __name__ == "__main__":
    # 1. 과목 데이터 업로드
    print("과목 데이터 업로드 중...")
    result = upload_courses("data/courses.json")
    print(f"✓ 업로드: {result['uploaded_count']}, 업데이트: {result['updated_count']}")
    
    # 2. 학생 데이터 업로드
    print("학생 데이터 업로드 중...")
    result = upload_students("data/students.json")
    print(f"✓ 업로드: {result['uploaded_count']}, 업데이트: {result['updated_count']}")
    
    # 3. 수강 데이터 업로드
    print("수강 데이터 업로드 중...")
    result = upload_enrollments("data/enrollments.json")
    print(f"✓ 업로드: {result['uploaded_count']}, 업데이트: {result['updated_count']}")
```

### 대량 진단 실행 스크립트

```python
import requests
import time

BASE_URL = "http://localhost:8080/api/admin"

def bulk_evaluate(student_ids=None, department_ids=None, force_recalculate=False):
    """대량 진단 실행"""
    payload = {
        "force_recalculate": force_recalculate
    }
    if student_ids:
        payload["student_ids"] = student_ids
    if department_ids:
        payload["department_ids"] = department_ids
    
    print("진단 시작...")
    start_time = time.time()
    
    response = requests.post(
        f"{BASE_URL}/evaluate/bulk",
        json=payload
    )
    
    elapsed_time = time.time() - start_time
    result = response.json()
    
    print(f"✓ 완료 시간: {elapsed_time:.2f}초")
    print(f"✓ 총 학생: {result['total_students']}")
    print(f"✓ 총 학과: {result['total_departments']}")
    print(f"✓ 총 진단: {result['total_evaluations']}")
    print(f"✓ 성공: {result['success_count']}")
    print(f"✓ 실패: {result['error_count']}")
    
    return result

def get_stats():
    """통계 조회"""
    response = requests.get(f"{BASE_URL}/evaluate/stats")
    return response.json()

# 사용 예시
if __name__ == "__main__":
    # 전체 진단 실행
    result = bulk_evaluate(force_recalculate=False)
    
    # 통계 확인
    print("\n=== 진단 결과 통계 ===")
    stats = get_stats()
    print(f"총 캐시: {stats['total_cached']}")
    print(f"마지막 업데이트: {stats['last_update']}")
    print("\n학과별 캐시:")
    for dept, count in stats['cached_by_department'].items():
        print(f"  - {dept}: {count}")
```

## 워크플로우 예시

### 신학기 데이터 업데이트 시나리오

```python
import requests
import json

BASE_URL = "http://localhost:8080/api/admin"

def new_semester_update():
    """신학기 데이터 업데이트 및 진단 실행"""
    
    # 1. 새로운 과목 데이터 업로드
    print("1. 과목 데이터 업로드...")
    with open("data/2026_spring_courses.json", "rb") as f:
        response = requests.post(f"{BASE_URL}/upload/courses/file", files={"file": f})
        print(f"   결과: {response.json()}")
    
    # 2. 학생 정보 업데이트
    print("2. 학생 데이터 업데이트...")
    with open("data/2026_students.json", "rb") as f:
        response = requests.post(f"{BASE_URL}/upload/students/file", files={"file": f})
        print(f"   결과: {response.json()}")
    
    # 3. 수강 데이터 업로드
    print("3. 수강 데이터 업로드...")
    with open("data/2026_spring_enrollments.json", "rb") as f:
        response = requests.post(f"{BASE_URL}/upload/enrollments/file", files={"file": f})
        print(f"   결과: {response.json()}")
    
    # 4. 기존 캐시 삭제
    print("4. 기존 진단 캐시 삭제...")
    response = requests.delete(f"{BASE_URL}/evaluate/cache")
    print(f"   결과: {response.json()}")
    
    # 5. 새로운 진단 실행
    print("5. 대량 진단 실행 (시간이 걸릴 수 있습니다)...")
    response = requests.post(
        f"{BASE_URL}/evaluate/bulk",
        json={"force_recalculate": True}
    )
    print(f"   결과: {response.json()}")
    
    # 6. 최종 통계 확인
    print("6. 최종 통계 확인...")
    response = requests.get(f"{BASE_URL}/evaluate/stats")
    print(f"   결과: {response.json()}")

if __name__ == "__main__":
    new_semester_update()
```

## API 엔드포인트 목록

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/admin/upload/courses` | 과목 데이터 업로드 (JSON) |
| POST | `/api/admin/upload/courses/file` | 과목 데이터 업로드 (파일) |
| POST | `/api/admin/upload/students` | 학생 데이터 업로드 (JSON) |
| POST | `/api/admin/upload/students/file` | 학생 데이터 업로드 (파일) |
| POST | `/api/admin/upload/enrollments` | 수강 데이터 업로드 (JSON) |
| POST | `/api/admin/upload/enrollments/file` | 수강 데이터 업로드 (파일) |
| POST | `/api/admin/evaluate/bulk` | 대량 진단 실행 |
| GET | `/api/admin/evaluate/stats` | 진단 결과 통계 조회 |
| DELETE | `/api/admin/evaluate/cache` | 캐시된 진단 결과 삭제 |
| GET | `/api/admin/health` | 관리자 API 상태 확인 |

## 주의사항

1. **대량 진단 실행 시간**: 학생 수와 학과 수에 따라 시간이 오래 걸릴 수 있습니다.
   - 100명 학생 × 5개 학과 = 500개 진단
   - 각 진단당 약 0.5초 소요 시 총 약 4-5분

2. **메모리 사용**: 대량의 데이터를 처리할 때 메모리 사용량이 증가할 수 있습니다.

3. **트랜잭션**: 모든 업로드는 트랜잭션으로 처리되므로, 오류 발생 시 롤백됩니다.

4. **중복 처리**: 
   - 과목: `course_code`로 중복 체크
   - 학생: `student_id`로 중복 체크
   - 수강: `(student_id, course_id, year, semester)` 조합으로 중복 체크

## 성능 최적화 팁

1. **배치 크기**: 한 번에 너무 많은 데이터를 업로드하지 않고, 1000개 단위로 나눠서 업로드
2. **캐시 활용**: `force_recalculate=False`로 기존 캐시를 재사용
3. **선택적 진단**: 필요한 학생/학과만 선택하여 진단 실행
