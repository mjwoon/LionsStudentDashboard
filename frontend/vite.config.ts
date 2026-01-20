import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,    // 0.0.0.0으로 설정하여 외부 접근 허용
    port: 5173,    // Vite 기본 포트
    watch: {
      usePolling: true, // Docker 환경에서 파일 변경 감지를 위해 필수
    },
    strictPort: false, // 포트가 사용 중이면 다음 포트 사용
  },
})