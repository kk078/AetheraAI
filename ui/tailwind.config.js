/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Aethera brand colors
        aethera: {
          primary: '#06B6D4',    // Teal - healthcare trust
          secondary: '#F59E0B',  // Amber - alerts
          success: '#10B981',    // Emerald
          error: '#F43F5E',      // Rose
          background: '#0D1117', // Deep charcoal (dark mode)
          surface: '#161B22',    // Card background
          foreground: '#E6EDF3', // Text (dark mode)
        },
        // Specialist colors
        specialist: {
          provider: '#06B6D4',
          payer: '#8B5CF6',
          regulatory: '#F43F5E',
          clinical: '#10B981',
          analytics: '#F59E0B',
          it: '#3B82F6',
          pharmacy: '#EC4899',
          behavioral: '#A855F7',
          dental: '#14B8A6',
          workersComp: '#F97316',
          finance: '#22C55E',
          legal: '#EF4444',
          software: '#6366F1',
          marketing: '#F43F5E',
          research: '#14B8A6',
          personal: '#A855F7',
          cloudflare: '#F97316',
          data: '#0EA5E9',
          general: '#6B7280',
        }
      },
      fontFamily: {
        heading: ['Outfit', 'sans-serif'],
        body: ['Source Sans 3', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
