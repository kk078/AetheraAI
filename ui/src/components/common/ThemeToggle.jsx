import React, { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'aethera-theme';

export default function ThemeToggle({ size = 'md' }) {
  const [isDark, setIsDark] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored === 'dark';
    return !document.documentElement.classList.contains('light');
  });

  const applyTheme = useCallback((dark) => {
    const root = document.documentElement;
    if (dark) {
      root.classList.remove('light');
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
      root.classList.add('light');
    }
  }, []);

  useEffect(() => {
    applyTheme(isDark);
    localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light');
    // Persist to API (fire-and-forget)
    try {
      fetch('/api/settings/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: isDark ? 'dark' : 'light' }),
      }).catch(() => {});
    } catch {}
  }, [isDark, applyTheme]);

  const toggle = () => setIsDark((prev) => !prev);

  const sizeClasses = {
    sm: { button: 'w-8 h-4', dot: 'w-3 h-3', icon: 'w-2.5 h-2.5', translate: 'translate-x-4' },
    md: { button: 'w-11 h-6', dot: 'w-4 h-4', icon: 'w-3 h-3', translate: 'translate-x-5' },
    lg: { button: 'w-14 h-7', dot: 'w-5 h-5', icon: 'w-4 h-4', translate: 'translate-x-7' },
  };

  const s = sizeClasses[size];

  return (
    <button
      onClick={toggle}
      className={`relative inline-flex ${s.button} items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-aethera-primary focus:ring-offset-2 focus:ring-offset-aethera-surface ${
        isDark ? 'bg-aethera-tertiary' : 'bg-amber-400'
      }`}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      <span
        className={`inline-block ${s.dot} transform rounded-full bg-white transition-transform ${
          isDark ? 'translate-x-1' : s.translate
        }`}
      >
        {isDark ? (
          <svg className={`${s.icon} text-aethera-primary m-[2px]`} fill="currentColor" viewBox="0 0 20 20">
            <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
          </svg>
        ) : (
          <svg className={`${s.icon} text-amber-500 m-[2px]`} fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
          </svg>
        )}
      </span>
    </button>
  );
}