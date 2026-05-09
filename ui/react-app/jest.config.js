module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/public/src/setupTests.tsx'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/public/src/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  collectCoverageFrom: [
    'public/src/**/*.{js,jsx,ts,tsx}',
    '!public/src/**/*.d.ts',
    '!public/src/index.tsx',
    '!public/src/reportWebVitals.ts',
    '!public/src/setupTests.tsx',
  ],
  coverageThreshold: {
    global: {
      branches: 50,
      functions: 50,
      lines: 50,
      statements: 50,
    },
  },
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['ts-jest', {
      tsconfig: {
        jsx: 'react',
        esModuleInterop: true,
      },
    }],
  },
  transformIgnorePatterns: [
    '/node_modules/(?!(@?react-native)/)',
  ],
  testMatch: [
    '<rootDir>/public/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/public/src/**/*.{spec,test}.{js,jsx,ts,tsx}',
  ],
  rootDir: '.',
};
