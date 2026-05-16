import { useState, useCallback, useEffect } from 'react';

const STORAGE_KEY = 'aethera-theme';
const VALID_MODES = ['dark', 'light', 'system'];
const DARK_CLASS = 'dark';
const LIGHT_CLASS = 'light';

/**
 * Theme management hook.
 *
 * Supports 'dark', 'light', and 'system' (follows OS preference).
 * Persists choice to localStorage and applies the corresponding CSS class
 * to the document root element.
 *
 * @returns {{ theme, setTheme, toggleTheme, resolvedTheme }}
 */
export function useTheme() {
  const [theme, setThemeState] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && VALID_MODES.includes(stored)) return stored;
    } catch {
      // localStorage unavailable (SSR, privacy mode)
    }
    return 'system';
  });

  /**
   * Determine the effective theme value based on the current mode and OS preference.
   */
  const getResolvedTheme = useCallback((mode) => {
    if (mode !== 'system') return mode;
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'dark'; // sensible default for a healthcare app (reduces eye strain)
  }, []);

  const [resolvedTheme, setResolvedTheme] = useState(() => getResolvedTheme(theme));

  /**
   * Apply the resolved theme class to the <html> element.
   */
  const applyThemeClass = useCallback((resolved) => {
    const root = document.documentElement;
    root.classList.remove(DARK_CLASS, LIGHT_CLASS);
    root.classList.add(resolved);
    root.setAttribute('data-theme', resolved);

    // Also update the meta theme-color for mobile browsers
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', resolved === 'dark' ? '#0D1117' : '#FFFFFF');
    }
  }, []);

  /**
   * Persist the selected mode and apply the resolved class.
   */
  const setTheme = useCallback((newTheme) => {
    if (!VALID_MODES.includes(newTheme)) {
      console.warn(`useTheme: invalid theme "${newTheme}". Must be one of: ${VALID_MODES.join(', ')}`);
      return;
    }

    setThemeState(newTheme);

    try {
      localStorage.setItem(STORAGE_KEY, newTheme);
    } catch {
      // Ignore storage errors
    }

    const resolved = getResolvedTheme(newTheme);
    setResolvedTheme(resolved);
    applyThemeClass(resolved);
  }, [getResolvedTheme, applyThemeClass]);

  /**
   * Cycle through dark -> light -> system -> dark.
   */
  const toggleTheme = useCallback(() => {
    const order = ['dark', 'light', 'system'];
    const currentIndex = order.indexOf(theme);
    const nextIndex = (currentIndex + 1) % order.length;
    setTheme(order[nextIndex]);
  }, [theme, setTheme]);

  // Apply the theme on mount and whenever theme changes
  useEffect(() => {
    const resolved = getResolvedTheme(theme);
    setResolvedTheme(resolved);
    applyThemeClass(resolved);
  }, [theme, getResolvedTheme, applyThemeClass]);

  // Listen for OS preference changes when in 'system' mode
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (event) => {
      const resolved = event.matches ? 'dark' : 'light';
      setResolvedTheme(resolved);
      applyThemeClass(resolved);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme, applyThemeClass]);

  return {
    theme,
    setTheme,
    toggleTheme,
    resolvedTheme,
  };
}

export default useTheme;