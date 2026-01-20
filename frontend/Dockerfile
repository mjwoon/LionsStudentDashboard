# 1. Node.js 가벼운 버전을 베이스 이미지로 사용
FROM node:20-slim

# 2. 컨테이너 내부 작업 디렉토리 설정
WORKDIR /app

# 3. 의존성 설치 (package.json만 먼저 복사하여 캐싱 활용)
COPY package*.json ./
RUN npm install

# 4. 나머지 소스 코드 복사
COPY . .

# 5. Vite 기본 포트 개방
EXPOSE 5173

# 6. 개발 서버 실행 (vite.config.ts의 host 설정이 적용됨)
CMD ["npm", "run", "dev"]