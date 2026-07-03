import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 백엔드 API 포트: 38090
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:38090',
        changeOrigin: true,
      },
      // STORAGE_MODE=local 개발용 미디어 서빙 (프로덕션은 R2/Cloudflare)
      '/media': {
        target: 'http://localhost:38090',
        changeOrigin: true,
      },
    },
  },
});
