// Jest setup file for frontend tests
import '@testing-library/jest-dom';

// Mock fetch for API calls
global.fetch = jest.fn();

// Reset mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
});