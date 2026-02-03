/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Pretendard Variable', 'Hakgyoansim Bareondotum', 'Malgun Gothic', 'sans-serif'],
        serif: ['Hakgyoansim Bareonbatang', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
