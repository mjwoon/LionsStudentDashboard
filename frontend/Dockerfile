# ======================
# Stage 1: Build
# ======================
FROM node:20-slim AS builder

WORKDIR /app

# 의존성 설치 (캐싱 활용)
COPY package*.json ./
RUN npm install

# 빌드 시점 환경변수 (Render 대시보드 또는 --build-arg로 주입)
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_LOGIN_PASSWORD=$VITE_LOGIN_PASSWORD
ENV VITE_ADMIN_PASSWORD=$VITE_ADMIN_PASSWORD

# 소스 코드 복사 및 빌드
COPY . .
RUN npm run build

# ======================
# Stage 2: Serve (nginx)
# ======================
FROM nginx:alpine

# 빌드 결과물 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# SPA 라우팅 설정
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
