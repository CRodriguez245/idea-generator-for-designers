/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'futura': ['Futura', 'Futura PT', 'Century Gothic', 'Trebuchet MS', 'Helvetica', 'Arial', 'sans-serif'],
        'helvetica': ['Helvetica', 'Helvetica Neue', '-apple-system', 'BlinkMacSystemFont', 'Arial', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#1976d2',
          dark: '#1565c0',
        },
      },
    },
  },
  plugins: [],
}

