/**
 * E2E Test Suite Entry Point
 * Sprint 15: Centralized exports for all E2E test utilities
 */

// Export all fixtures
export * from './fixtures';

// Export all helpers
export * from './helpers';

// Re-export commonly used testing utilities
export { render, screen, fireEvent, waitFor } from '@testing-library/react';
export { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
export { MemoryRouter, BrowserRouter } from 'react-router-dom';
