/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 主色
        primary: {
          DEFAULT: '#2DD4BF',
          light: '#5EEAD4',
          dark: '#14B8A6',
        },
        // 强调色
        accent: {
          pink: '#F472B6',
          coral: '#FB7185',
          blue: '#38BDF8',
          orange: '#FB923C',
        },
        // 背景色
        surface: {
          DEFAULT: '#FFFFFF',
          secondary: '#F8F8F8',
          background: '#F5F5F5',
        },
        // 文字颜色
        text: {
          primary: '#1F2937',
          secondary: '#6B7280',
          tertiary: '#9CA3AF',
          muted: '#D1D5DB',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['SF Pro Display', 'Inter', 'sans-serif'],
      },
      fontSize: {
        'xs': '11px',
        'sm': '13px',
        'base': '15px',
        'lg': '18px',
        'xl': '20px',
        '2xl': '24px',
        '3xl': '32px',
        '4xl': '48px',
      },
      spacing: {
        '4.5': '18px',
        '5.5': '22px',
      },
      borderRadius: {
        'xl': '16px',
        '2xl': '20px',
        '3xl': '24px',
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.04)',
        'nav': '0 -4px 12px rgba(0, 0, 0, 0.05)',
      },
    },
  },
  plugins: [],
}
