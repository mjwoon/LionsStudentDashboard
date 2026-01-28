# Lions Student Dashboard - Frontend

한양대학교 LIONS 학생 관리 대시보드 프론트엔드 애플리케이션입니다.

## 기술 스택

- **React** - UI 라이브러리
- **TypeScript** - 타입 안전성
- **Vite** - 빌드 도구
- **Tailwind CSS** - 스타일링
- **Recharts** - 차트 라이브러리
- **Lucide React** - 아이콘

## 프로젝트 구조

```
frontend/src/
├── components/
│   ├── DashboardView.tsx       # 전체 현황 대시보드
│   ├── StudentDetailView.tsx   # 학생 상세 정보
│   ├── AdminView.tsx           # 관리자 페이지 ⭐ NEW
│   └── DataUploadTab.tsx       # 데이터 업로드 탭 ⭐ NEW
├── api.ts                      # API 호출 함수
├── App.tsx                     # 메인 앱
└── main.tsx                    # 엔트리 포인트
```

## 설치 및 실행

### 개발 서버 실행

```bash
npm install
npm run dev
```

서버가 `http://localhost:5173`에서 실행됩니다.

### 프로덕션 빌드

```bash
npm run build
npm run preview
```

## 주요 기능

### 1. 전체 현황 대시보드
- 학과별 희망 학생 통계
- 트렌드 차트
- 단과대학별 필터링
- CSV 다운로드

### 2. 학생 관리
- 학생 목록 조회
- 필터링 (학과, PRIDE, 분반)
- 페이징
- 학생 상세 정보

### 3. 관리자 기능 ⭐ NEW

#### 데이터 업로드
- 과목, 학생, 수강 데이터 JSON 파일 업로드
- 샘플 JSON 다운로드
- 업로드 진행 상황 표시
- 성공/실패 결과 및 오류 목록 표시

상세 가이드: [ADMIN_PHASE1.md](ADMIN_PHASE1.md)

## 환경 변수

`.env` 파일을 생성하여 백엔드 API URL을 설정할 수 있습니다:

```env
VITE_API_URL=http://localhost:8080
```

기본값은 `http://localhost:8080` (Docker 환경)입니다.

## 백엔드 연동

백엔드 서버가 실행 중이어야 합니다:

```bash
cd ../backend
uv run fastapi dev main.py
```

## 개발 가이드

### 새로운 컴포넌트 추가

1. `src/components/` 디렉토리에 `.tsx` 파일 생성
2. 필요한 경우 `api.ts`에 API 함수 추가
3. `App.tsx`에서 라우팅 설정

### API 함수 사용

```typescript
import { api } from './api';

// 학생 목록 조회
const students = await api.students.list(1, 10);

// 관리자: 과목 데이터 업로드
const result = await api.admin.uploadCoursesFile(file);
```

## 빠른 테스트

관리자 기능 테스트: [QUICK_TEST.md](QUICK_TEST.md)

## 스크립트

- `npm run dev` - 개발 서버 실행
- `npm run build` - 프로덕션 빌드
- `npm run preview` - 빌드 결과 미리보기
- `npm run lint` - ESLint 실행

## React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
