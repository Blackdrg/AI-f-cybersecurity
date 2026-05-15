/**
 * Enhanced MUI Theme — Enterprise AI Platform
 *
 * Token-driven theme configuration with glassmorphism,
 * custom color scales, and component-level overrides.
 */
import { createTheme, type ThemeOptions } from '@mui/material/styles';
import { colors, typography, glass, radii, spacing } from './tokens';

declare module '@mui/material/styles' {
  interface Palette {
    glass: { main: string; light: string; dark: string };
    glow: typeof colors.glow;
    tier: typeof colors.tier;
  }
  interface PaletteOptions {
    glass?: { main: string; light: string; dark: string };
    glow?: typeof colors.glow;
    tier?: typeof colors.tier;
  }
}

const themeOptions: ThemeOptions = {
  palette: {
    mode: 'dark',
    primary: {
      main: colors.brand.primary,
      light: colors.brand.primaryLight,
      dark: colors.brand.primaryDark,
      contrastText: '#ffffff',
    },
    secondary: {
      main: colors.brand.secondary,
      light: colors.brand.secondaryLight,
      dark: colors.brand.secondaryDark,
      contrastText: '#ffffff',
    },
    background: {
      default: colors.surface.base,
      paper: colors.surface.raised,
    },
    success: {
      main: colors.semantic.success,
      light: colors.semantic.successLight,
      dark: colors.semantic.successDark,
    },
    warning: {
      main: colors.semantic.warning,
      light: colors.semantic.warningLight,
      dark: colors.semantic.warningDark,
    },
    error: {
      main: colors.semantic.error,
      light: colors.semantic.errorLight,
      dark: colors.semantic.errorDark,
    },
    info: {
      main: colors.semantic.info,
      light: colors.semantic.infoLight,
      dark: colors.semantic.infoDark,
    },
    text: {
      primary: colors.text.primary,
      secondary: colors.text.secondary,
      disabled: colors.text.disabled,
    },
    divider: colors.surface.border,
    glass: {
      main: glass.light.background,
      light: glass.medium.background,
      dark: glass.thin.background,
    },
    glow: colors.glow,
    tier: colors.tier,
  },

  typography: {
    fontFamily: typography.fontFamily.sans,
    fontSize: 14,
    h1: {
      fontSize: typography.fontSize['4xl'],
      fontWeight: typography.fontWeight.bold,
      lineHeight: typography.lineHeight.tight,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontSize: typography.fontSize['3xl'],
      fontWeight: typography.fontWeight.bold,
      lineHeight: typography.lineHeight.tight,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontSize: typography.fontSize['2xl'],
      fontWeight: typography.fontWeight.semibold,
      lineHeight: typography.lineHeight.tight,
    },
    h4: {
      fontSize: typography.fontSize.xl,
      fontWeight: typography.fontWeight.semibold,
      lineHeight: typography.lineHeight.normal,
    },
    h5: {
      fontSize: typography.fontSize.lg,
      fontWeight: typography.fontWeight.semibold,
      lineHeight: typography.lineHeight.normal,
    },
    h6: {
      fontSize: typography.fontSize.md,
      fontWeight: typography.fontWeight.semibold,
      lineHeight: typography.lineHeight.normal,
    },
    body1: {
      fontSize: typography.fontSize.md,
      lineHeight: typography.lineHeight.normal,
    },
    body2: {
      fontSize: typography.fontSize.base,
      lineHeight: typography.lineHeight.normal,
    },
    caption: {
      fontSize: typography.fontSize.sm,
      color: colors.text.tertiary,
    },
    overline: {
      fontSize: typography.fontSize.xs,
      fontWeight: typography.fontWeight.semibold,
      letterSpacing: '0.08em',
      textTransform: 'uppercase' as const,
    },
  },

  shape: {
    borderRadius: radii.md,
  },

  spacing: spacing.xs, // 4px base unit

  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarWidth: 'thin',
          scrollbarColor: `${colors.surface.elevated} transparent`,
          '&::-webkit-scrollbar': { width: 6 },
          '&::-webkit-scrollbar-track': { background: 'transparent' },
          '&::-webkit-scrollbar-thumb': {
            background: colors.surface.elevated,
            borderRadius: 3,
          },
        },
      },
    },

    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: radii.md,
          textTransform: 'none' as const,
          fontWeight: typography.fontWeight.semibold,
          fontSize: typography.fontSize.base,
          padding: `${spacing.sm}px ${spacing.md}px`,
          transition: 'all 0.2s ease',
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(59, 130, 246, 0.25)',
            transform: 'translateY(-1px)',
          },
        },
        outlined: {
          borderColor: colors.surface.borderLight,
          '&:hover': {
            borderColor: colors.brand.primary,
            background: 'rgba(59, 130, 246, 0.08)',
          },
        },
      },
    },

    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: radii.lg,
          ...glass.light,
          backgroundImage: 'none',
        },
      },
    },

    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: radii.lg,
          ...glass.light,
          backgroundImage: 'none',
          transition: 'all 0.2s ease',
        },
      },
    },

    MuiDrawer: {
      styleOverrides: {
        paper: {
          background: `linear-gradient(180deg, ${colors.surface.raised} 0%, ${colors.surface.overlay} 100%)`,
          borderRight: `1px solid ${colors.surface.border}`,
          backgroundImage: 'none',
        },
      },
    },

    MuiAppBar: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          ...glass.dark,
          backgroundImage: 'none',
          borderBottom: `1px solid ${colors.surface.border}`,
        },
      },
    },

    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: typography.fontWeight.medium,
          fontSize: typography.fontSize.sm,
        },
      },
    },

    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          ...glass.heavy,
          fontSize: typography.fontSize.sm,
          borderRadius: radii.sm,
        },
      },
    },

    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none' as const,
          fontWeight: typography.fontWeight.medium,
          fontSize: typography.fontSize.base,
          minHeight: 40,
        },
      },
    },

    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: radii.full,
          height: 4,
          backgroundColor: colors.surface.border,
        },
      },
    },

    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: radii.md,
          ...glass.light,
        },
      },
    },
  },
};

const theme = createTheme(themeOptions);

export default theme;