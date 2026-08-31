import { useEffect, useCallback, useSyncExternalStore } from 'react';

export interface ChartColors {
  gridColor: string;
  textColor: string;
  bgColor: string;
  hoverBgColor: string;
  hoverBorderColor: string;
  hoverTextColor: string;
  legendBgColor: string;
  legendBorderColor: string;
}

const lightColors: ChartColors = {
  gridColor: 'rgba(128, 128, 128, 0.1)',
  textColor: '#333',
  bgColor: 'rgba(0, 0, 0, 0)',
  hoverBgColor: 'white',
  hoverBorderColor: '#ddd',
  hoverTextColor: 'black',
  legendBgColor: 'rgba(255, 255, 255, 0.9)',
  legendBorderColor: '#ddd',
};

const darkColors: ChartColors = {
  gridColor: 'rgba(255, 255, 255, 0.1)',
  textColor: '#ffffff',
  bgColor: 'rgba(0, 0, 0, 0)',
  hoverBgColor: '#171717',
  hoverBorderColor: '#404040',
  hoverTextColor: '#ffffff',
  legendBgColor: 'rgba(23, 23, 23, 0.95)',
  legendBorderColor: '#404040',
};

type ThemeMode = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'slurm-dashboard-theme';

// Global state for synchronization across components
let globalMode: ThemeMode = 'system';
let globalSystemDark = false;
const listeners: Set<() => void> = new Set();

const getSystemPreference = (): boolean => {
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  return false;
};

const getStoredTheme = (): ThemeMode => {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
  }
  return 'system';
};

// Initialize global state
if (typeof window !== 'undefined') {
  globalMode = getStoredTheme();
  globalSystemDark = getSystemPreference();

  // Listen for system preference changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    globalSystemDark = e.matches;
    applyTheme();
    notifyListeners();
  });
}

const notifyListeners = () => {
  listeners.forEach(listener => listener());
};

const applyTheme = () => {
  const isDark = globalMode === 'system' ? globalSystemDark : globalMode === 'dark';
  if (isDark) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
};

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

const getSnapshot = () => {
  const isDark = globalMode === 'system' ? globalSystemDark : globalMode === 'dark';
  return `${globalMode}-${isDark}`;
};

export const useDarkMode = (): {
  isDark: boolean;
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  toggle: () => void;
  chartColors: ChartColors;
} => {
  // Use useSyncExternalStore for synchronized state across components
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  // Parse snapshot
  const isDark = snapshot.endsWith('-true');

  // Apply theme class on mount and changes
  useEffect(() => {
    applyTheme();
  }, [snapshot]);

  const setMode = useCallback((newMode: ThemeMode) => {
    globalMode = newMode;
    localStorage.setItem(STORAGE_KEY, newMode);
    applyTheme();
    notifyListeners();
  }, []);

  const toggle = useCallback(() => {
    // Cycle through: system -> light -> dark -> system
    const nextMode: ThemeMode = globalMode === 'system' ? 'light' : globalMode === 'light' ? 'dark' : 'system';
    setMode(nextMode);
  }, [setMode]);

  return {
    isDark,
    mode: globalMode,
    setMode,
    toggle,
    chartColors: isDark ? darkColors : lightColors,
  };
};

export default useDarkMode;
