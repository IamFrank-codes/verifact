import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
const apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'
export default defineConfig({plugins: [react(), tailwindcss()], server: {host: '0.0.0.0', proxy: {'/api': apiTarget, '/health': apiTarget}}})
