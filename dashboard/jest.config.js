/** @type {import('jest').Config} */
module.exports = {
  transform: {
    '^.+\\.(ts|tsx)$': ['@swc/jest', {
      jsc: {
        transform: {
          react: { runtime: 'automatic' },
        },
      },
    }],
  },
  transformIgnorePatterns: [
    '/node_modules/(?!(lucide-react|recharts)/)',
  ],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '^next/link$': '<rootDir>/__mocks__/next-link.tsx',
    '^next/head$': '<rootDir>/__mocks__/next-head.tsx',
  },
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testMatch: ['<rootDir>/__tests__/**/*.test.{ts,tsx}'],
};
