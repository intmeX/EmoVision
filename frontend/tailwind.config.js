/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 背景色
        'bg-primary': '#0f0f0f',
        'bg-secondary': '#1a1a1a',
        'bg-tertiary': '#262626',
        'bg-elevated': '#2d2d2d',
        // 边框色
        'border-primary': '#3d3d3d',
        'border-secondary': '#525252',
        // 强调色
        'accent': {
          'primary': '#3b82f6',
          'success': '#22c55e',
          'warning': '#f59e0b',
          'danger': '#ef4444',
        },
        // 情绪色
        'emotion': {
          'happy': '#22c55e',
          'sad': '#3b82f6',
          'angry': '#ef4444',
          'fear': '#a855f7',
          'surprise': '#f59e0b',
          'disgust': '#84cc16',
          'neutral': '#6b7280',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
