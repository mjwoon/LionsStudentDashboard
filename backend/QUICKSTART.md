# 관리자 모듈 빠른 시작 가이드

## 1. 기본 사용법

### 서버 실행 확인

```bash
# 백엔드 디렉토리로 이동
cd backend

# 서버 실행
uv run fastapi dev main.py
```

서버가 http://localhost:8080 에서 실행되는지 확인

## 2. 샘플 데이터로 테스트

### 2.1 과목 데이터 업로드

```bash
python admin_cli.py upload-courses data/sample_courses.json
```

예상 출력:
```
📚 과목 데이터 업로드: data/sample_courses.json
✅ 성공!
   - 새로 추가: 2
   - 업데이트: 0
```

### 2.2 학생 데이터 업로드

```bash
python admin_cli.py upload-students data/sample_students.json
```

예상 출력:
```
👨‍🎓 학생 데이터 업로드: data/sample_students.json
✅ 성공!
   - 새로 추가: 2
   - 업데이트: 0
```

### 2.3 수강 데이터 업로드

```bash
python admin_cli.py upload-enrollments data/sample_enrollments.json
```

예상 출력:
```
📝 수강 데이터 업로드: data/sample_enrollments.json
✅ 성공!
   - 새로 추가: 2
   - 업데이트: 0
```

## 3. 진단 기능 테스트

### 3.1 특정 학생에 대한 진단 실행

```bash
python admin_cli.py evaluate --students 2026999001
```

### 3.2 전체 진단 통계 확인

```bash
python admin_cli.py stats
```

예상 출력:
```
📊 진단 결과 통계 조회...

=== 진단 결과 통계 ===
총 캐시된 진단: 10
마지막 업데이트: 2026-01-28T10:30:00

학과별 캐시:
  - 컴퓨터공학과: 2
  - 기계공학과: 2
  - ...
```

## 4. API로 직접 테스트

### Swagger UI 사용

1. 브라우저에서 http://localhost:8080/docs 접속
2. "admin" 태그 섹션 찾기
3. 원하는 엔드포인트 클릭
4. "Try it out" 버튼 클릭
5. 파라미터 입력 후 "Execute"

### curl로 테스트

#### 과목 데이터 업로드

```bash
curl -X POST http://localhost:8080/api/admin/upload/courses \
  -H "Content-Type: application/json" \
  -d '[
    {
      "course_code": "NEW101",
      "course_name": "신규과목",
      "credits": 3,
      "course_type": "전공필수",
      "department_code": "CSE"
    }
  ]'
```

#### 진단 통계 조회

```bash
curl http://localhost:8080/api/admin/evaluate/stats
```

#### 대량 진단 실행

```bash
curl -X POST http://localhost:8080/api/admin/evaluate/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "force_recalculate": false
  }'
```

## 5. 실전 시나리오

### 신학기 데이터 업데이트

```bash
# 1. 모든 데이터 업로드
python admin_cli.py upload-all data/

# 2. 기존 캐시 삭제
python admin_cli.py clear-cache

# 3. 새로운 진단 실행 (시간이 걸릴 수 있음)
python admin_cli.py evaluate --force

# 4. 결과 확인
python admin_cli.py stats
```

### 특정 학과만 재진단

```bash
# 컴퓨터공학과(ID: 2)만 재진단
python admin_cli.py clear-cache --department 2
python admin_cli.py evaluate --departments 2 --force
```

## 6. 문제 해결

### 서버 연결 실패

```
❌ 서버 연결 실패: http://localhost:8080
```

**해결**: 서버가 실행 중인지 확인
```bash
uv run fastapi dev main.py
```

### 파일을 찾을 수 없음

```
❌ 파일을 찾을 수 없습니다: data/courses.json
```

**해결**: 파일 경로 확인 또는 절대 경로 사용
```bash
python admin_cli.py upload-courses C:/full/path/to/courses.json
```

### 학과 코드를 찾을 수 없음

```
⚠️  오류: 1
   - 학과 코드 XYZ를 찾을 수 없습니다.
```

**해결**: 올바른 학과 코드 확인
- LION: 자율전공학부
- CSE: 컴퓨터공학과
- MECH: 기계공학과
- BIZ: 경영학과
- EE: 전자공학과

## 7. 다음 단계

- 자세한 API 문서: http://localhost:8080/docs
- 전체 관리자 가이드: [ADMIN_GUIDE.md](ADMIN_GUIDE.md)
- API 명세: [api_spec.md](api_spec.md)
