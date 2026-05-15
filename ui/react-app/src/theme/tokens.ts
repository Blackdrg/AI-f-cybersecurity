/**
 * Design Token System — Enterprise AI Platform
 *
 * Centralized design tokens for consistent spacing, colors,
 * typography, shadows, glassmorphism, and animation timing.
 */

// ─── Spacing Scale (4px base) ───────────────────────────────────
export const spacing = {
  xxs: 2,
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
} as const;

// ─── Color Palette ──────────────────────────────────────────────
export const colors = {
  // Brand
  brand: {
    primary: '#3b82f6',
    primaryLight: '#60a5fa',
    primaryDark: '#2563eb',
    secondary: '#8b5cf6',
    secondaryLight: '#a78bfa',
    secondaryDark: '#7c3aed',
    accent: '#06b6d4',
  },

  // Semantic
  semantic: {
    success: '#10b981',
    successLight: '#34d399',
    successDark: '#059669',
    warning: '#f59e0b',
    warningLight: '#fbbf24',
    warningDark: '#d97706',
    error: '#ef4444',
    errorLight: '#f87171',
    errorDark: '#dc2626',
    info: '#3b82f6',
    infoLight: '#60a5fa',
    infoDark: '#2563eb',
  },

  // Surfaces (dark theme)
  surface: {
    base: '#0a0a0f',
    raised: '#0f172a',
    overlay: '#1e293b',
    elevated: '#334155',
    border: 'rgba(255, 255, 255, 0.08)',
    borderLight: 'rgba(255, 255, 255, 0.12)',
    borderActive: 'rgba(255, 255, 255, 0.2)',
  },

  // Text
  text: {
    primary: '#f1f5f9',
    secondary: '#94a3b8',
    tertiary: '#64748b',
    disabled: '#475569',
    inverse: '#0f172a',
  },

  // AI / Glow effects
  glow: {
    cyan: '#00ffff',
    blue: '#3b82f6',
    violet: '#8b5cf6',
    emerald: '#10b981',
    amber: '#f59e0b',
    crimson: '#ef4444',
  },

  // Tier colors
  tier: {
    free: '#64748b',
    pro: '#3b82f6',
    enterprise: '#8b5cf6',
    custom: '#f59e0b',
  },
} as const;

// ─── Typography Scale ───────────────────────────────────────────
export const typography = {
  fontFamily: {
    sans: '"Inter", "Roboto", "Helvetica Neue", Arial, sans-serif',
    mono: '"JetBrains Mono", "Fira Code", "Consolas", monospace',
  },
  fontSize: {
    xs: '0.65rem',    // 10.4px — tiny labels
    sm: '0.75rem',    // 12px — captions
    base: '0.8rem',   // 12.8px — body small
    md: '0.875rem',   // 14px — body
    lg: '1rem',       // 16px — body large
    xl: '1.25rem',    // 20px — h4
    '2xl': '1.5rem',  // 24px — h3
    '3xl': '2rem',    // 32px — h2
    '4xl': '2.5rem',  // 40px — h1
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
} as const;

// ─── Glassmorphism Presets ───────────────────────────────────────
export const glass = {
  thin: {
    background: 'rgba(255, 255, 255, 0.04)',
    backdropFilter: 'blur(8px)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
  },
  light: {
    background: 'rgba(255, 255, 255, 0.08)',
    backdropFilter: 'blur(12px)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  },
  medium: {
    background: 'rgba(255, 255, 255, 0.12)',
    backdropFilter: 'blur(16px)',
    border: '1px solid rgba(255, 255, 255, 0.15)',
  },
  heavy: {
    background: 'rgba(255, 255, 255, 0.18)',
    backdropFilter: 'blur(24px)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
  },
  dark: {
    background: 'rgba(0, 0, 0, 0.4)',
    backdropFilter: 'blur(20px)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
  },
} as const;

// ─── Shadow System ──────────────────────────────────────────────
export const shadows = {
  none: 'none',
  sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
  md: '0 4px 6px rgba(0, 0, 0, 0.3)',
  lg: '0 10px 15px rgba(0, 0, 0, 0.3)',
  xl: '0 20px 25px rgba(0, 0, 0, 0.4)',
  glow: {
    blue: '0 0 20px rgba(59, 130, 246, 0.3)',
    cyan: '0 0 20px rgba(6, 182, 212, 0.3)',
    violet: '0 0 20px rgba(139, 92, 246, 0.3)',
    emerald: '0 0 20px rgba(16, 185, 129, 0.3)',
    error: '0 0 20px rgba(239, 68, 68, 0.3)',
    amber: '0 0 20px rgba(245, 158, 11, 0.3)',
  },
  inset: '0 2px 4px rgba(0, 0, 0, 0.3) inset',
} as const;

// ─── Border Radius ──────────────────────────────────────────────
export const radii = {
  none: 0,
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
} as const;

// ─── Animation Timing ───────────────────────────────────────────
export const animation = {
  duration: {
    instant: 0.1,
    fast: 0.15,
    normal: 0.3,
    slow: 0.5,
    glacial: 0.8,
  },
  easing: {
    default: [0.4, 0, 0.2, 1],
    easeIn: [0.4, 0, 1, 1],
    easeOut: [0, 0, 0.2, 1],
    easeInOut: [0.4, 0, 0.2, 1],
    spring: [0.175, 0.885, 0.32, 1.275],
  },
} as const;

// ─── Z-Index Scale ──────────────────────────────────────────────
export const zIndex = {
  base: 0,
  dropdown: 100,
  sticky: 200,
  overlay: 300,
  modal: 400,
  popover: 500,
  toast: 600,
  tooltip: 700,
  top: 999,
} as const;

// ─── Breakpoints ────────────────────────────────────────────────
export const breakpoints = {
  xs: 0,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;
