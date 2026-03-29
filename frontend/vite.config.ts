import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/tutoring': 'http://localhost:8000',
      '/kg': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
  },
});
