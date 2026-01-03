/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['var(--font-display)', 'serif'],
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },
      fontSize: {
        'display-xl': ['72px', { lineHeight: '1.1', fontWeight: '900', letterSpacing: '-0.02em' }],
        'display-lg': ['56px', { lineHeight: '1.1', fontWeight: '900', letterSpacing: '-0.02em' }],
        'display': ['48px', { lineHeight: '1.2', fontWeight: '700', letterSpacing: '-0.01em' }],
        'heading-xl': ['36px', { lineHeight: '1.2', fontWeight: '600' }],
        'heading-lg': ['30px', { lineHeight: '1.3', fontWeight: '600' }],
        'number-xl': ['48px', { lineHeight: '1.2', fontWeight: '700' }],
        'number-lg': ['32px', { lineHeight: '1.3', fontWeight: '700' }],
        'number-md': ['18px', { lineHeight: '1.4', fontWeight: '600' }],
        'number-sm': ['14px', { lineHeight: '1.5', fontWeight: '500' }],
        'caption': ['11px', { lineHeight: '1.5', fontWeight: '400', letterSpacing: '0.5px' }],
      },
      colors: {
        // Navy - Dominant Trust & Depth
        navy: {
          950: '#0a1628',
          900: '#0f2744',
          800: '#1a3a5c',
          700: '#234d7b',
          600: '#2e5f9a',
        },
        // Emerald - Growth & Success (sophisticated green)
        emerald: {
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
        },
        // Rose - Alert & Risk (sophisticated red)
        rose: {
          400: '#fb7185',
          500: '#f43f5e',
          600: '#e11d48',
        },
        // Amber/Gold - Premium & Warning
        amber: {
          400: '#fbbf24',
          500: '#f59e0b',
        },
        gold: {
          400: '#fbbf24',
          500: '#f59e0b',
        },
        // Slate - Sophisticated Neutrals
        slate: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        // Legacy aliases for backwards compatibility
        success: {
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
        },
        danger: {
          400: '#fb7185',
          500: '#f43f5e',
          600: '#e11d48',
        },
        warning: {
          400: '#fbbf24',
          500: '#f59e0b',
        },
        info: {
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
      boxShadow: {
        'minimal': '0 1px 3px rgba(0, 0, 0, 0.08)',
        'card': '0 1px 3px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 4px 6px rgba(0, 0, 0, 0.1)',
        'modal': '0 10px 25px rgba(0, 0, 0, 0.15)',
        'dropdown': '0 4px 12px rgba(0, 0, 0, 0.12)',
      },
      borderColor: {
        'subtle': '#E5E7EB', // gray-200
      },
      backgroundColor: {
        'subtle': '#F9FAFB', // gray-50
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.15s ease-in-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'scaleY(0)', opacity: '0' },
          '100%': { transform: 'scaleY(1)', opacity: '1' },
        },
      },
      transitionDuration: {
        '150': '150ms',
      },
    },
  },
  plugins: [
    // Add tabular numbers utility
    function({ addUtilities }) {
      addUtilities({
        '.tabular-nums': {
          'font-variant-numeric': 'tabular-nums',
        },
      })
    },
  ],
}
