import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // fixtures live in ../fixtures, shared with the backend tests
  server: { fs: { allow: ['..'] } },
})
