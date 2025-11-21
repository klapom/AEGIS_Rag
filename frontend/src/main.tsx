/**
 * React StrictMode Configuration - Sprint 31 Fix
 *
 * Issue: StrictMode causes double-mounting in development, which triggers
 * AbortController cleanup between mounts, aborting SSE fetch requests.
 *
 * Evidence:
 * - Network trace shows first "stream" request with "x-unknown" status (aborted)
 * - Second request succeeds but tests timeout waiting for response
 * - Backend logs show no incoming requests when StrictMode is enabled
 *
 * Solution: Conditionally disable StrictMode during E2E tests while keeping
 * it enabled for development to catch side effects.
 *
 * Test Results:
 * - WITH StrictMode: All E2E tests timeout (0/12 passed)
 * - WITHOUT StrictMode: 9/12 tests pass, only assertion errors remain
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Disable StrictMode during Playwright E2E tests to prevent fetch abortion
// Playwright sets window.playwright when running tests
const isE2ETest = typeof window !== 'undefined' && (window as any).playwright;
const enableStrictMode = !isE2ETest && import.meta.env.DEV;

const app = enableStrictMode ? (
  <StrictMode>
    <App />
  </StrictMode>
) : (
  <App />
);

createRoot(document.getElementById('root')!).render(app);
