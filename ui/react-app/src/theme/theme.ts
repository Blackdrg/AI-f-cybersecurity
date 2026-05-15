// src/theme/theme.ts
import { createTheme, ThemeOptions } from '@mui/material/styles';

// Define the color palette based on the recommendations
const palette = {
  mode: 'dark',
  primary: {
    main: '#00bcd4', // electric blue
    light: '#33cfff',
    dark: '#008a9e',
    contrastText: '#ffffff',
  },
  secondary: {
    main: '#ff00ff', // neon violet (approximation, true neon violet might be #8f00ff)
    light: '#ff33ff',
    dark: '#cc00cc',
    contrastText: '#ffffff',
  },
  background: {
    default: '#0a0a0a', // deep obsidian
    paper: '#1a1a1a',
  },
  // Custom colors for AI glow, success, warning, danger, glass
  aiGlow: {
    main: '#00ffff', // cyan
    light: '#33ffff',
    dark: '#00cccc',
    contrastText: '#000000',
  },
  success: {
    main: '#00ff00', // emerald (approximation, true emerald might be #50c878)
    light: '#33ff33',
    dark: '#00cc00',
    contrastText: '#000000',
  },
  warning: {
    main: '#ffbf00', // amber
    light: '#ffff33',
    dark: '#cc9900',
    contrastText: '#000000',
  },
  danger: {
    main: '#ff0000', // crimson
    light: '#ff3333',
    dark: '#cc0000',
    contrastText: '#ffffff',
  },
  glass: {
    // Glass effect will be achieved via backdrop-filter and background-color with opacity
    // We define a translucent white for glass-like elements
    main: 'rgba(255, 255, 255, 0.1)',
    light: 'rgba(255, 255, 255, 0.15)',
    dark: 'rgba(255, 255, 255, 0.05)',
  },
};

// Define the theme options
const themeOptions: ThemeOptions = {
  palette,
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    // We can add more typography settings if needed
  },
  components: {
    // Global component overrides
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
          // Add glass effect to buttons by default
          '&:not(.Mui-disabled)': {
            backgroundImage: 'linear-gradient(to bottom, rgba(255,255,255,0.1), rgba(255,255,255,0))',
            backdropFilter: 'blur(10px)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          // Glass effect for papers
          backgroundImage: 'linear-gradient(to bottom, rgba(255,255,255,0.1), rgba(255,255,255,0))',
          backdropFilter: 'blur(10px)',
          // Add a subtle border for depth
          border: '1px solid rgba(255, 255, 255, 0.1)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          // Glass effect for drawer
          backgroundImage: 'linear-gradient(to bottom, rgba(255,255,255,0.1), rgba(255,255,255,0))',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          // Glass effect for app bar
          backgroundImage: 'linear-gradient(to bottom, rgba(255,255,255,0.1), rgba(255,255,255,0))',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        },
      },
    },
  },
  // Add custom properties for motion, depth, etc. (these are CSS variables or can be used in styles)
  // We'll define them as CSS variables in the theme's components or via createGlobalStyle if needed.
  // For now, we'll just define the theme and let the components use these values.
};

// Create the theme
const theme = createTheme(themeOptions);

export default theme;