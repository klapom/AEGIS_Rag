/**
 * App Component
 * Sprint 15 Feature 15.4: Main App with React Router
 * Sprint 28 Feature 28.3: Settings page and context provider
 * Sprint 31 Feature 31.10b: Cost Dashboard route registration
 * Sprint 38 Feature 38.1b: JWT Authentication Frontend
 * Sprint 38 Feature 38.3: Share Conversation Links (public route)
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 * Sprint 79 Feature 79.7: Admin Graph Operations UI
 * Sprint 98 Feature 98.1: Agent Communication Dashboard
 * Sprint 98 Feature 98.2: Agent Hierarchy Visualizer
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 * Sprint 98 Feature 98.4: Audit Trail Viewer
 * Sprint 116 Feature 116.2: API Error Handling
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SettingsProvider } from './contexts/SettingsContext';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { ErrorBoundary } from './components/error/ErrorBoundary';
import { ToastContainer } from './components/error/ToastContainer';
import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { SearchResultsPage } from './pages/SearchResultsPage';
import { HealthDashboard } from './pages/HealthDashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { AdminPage } from './pages/AdminPage';
import { Settings } from './pages/Settings';
import { GraphAnalyticsPage } from './pages/admin/GraphAnalyticsPage';
import { CostDashboardPage } from './pages/admin/CostDashboardPage';
import { AdminIndexingPage } from './pages/admin/AdminIndexingPage';
import { AdminLLMConfigPage } from './pages/admin/AdminLLMConfigPage';
import { SharedConversationPage } from './pages/SharedConversationPage';
import { DomainTrainingPage } from './pages/admin/DomainTrainingPage';
import { UploadPage } from './pages/admin/UploadPage';
import { IngestionJobsPage } from './pages/admin/IngestionJobsPage';
import { MCPToolsPage } from './pages/admin/MCPToolsPage';
import { MemoryManagementPage } from './pages/admin/MemoryManagementPage';
import { AdminGraphOperationsPage } from './pages/admin/AdminGraphOperationsPage';
import { ExplainabilityPage } from './pages/admin/ExplainabilityPage';
import { SkillCertificationPage } from './pages/admin/SkillCertificationPage';
import { SkillRegistry } from './pages/admin/SkillRegistry';
import { SkillConfigEditor } from './pages/admin/SkillConfigEditor';
import { ToolAuthorizationPage } from './pages/admin/ToolAuthorization';
import { SkillLifecycleDashboard } from './pages/admin/SkillLifecycle';
import { SkillMdEditor } from './pages/admin/SkillMdEditor';
import { AgentCommunicationPage } from './pages/admin/AgentCommunicationPage';
import { AgentHierarchyPage } from './pages/admin/AgentHierarchyPage';
import { GDPRConsentPage } from './pages/admin/GDPRConsent';
import { AuditTrailPage } from './pages/admin/AuditTrail';
import { BrowserToolsPage } from './pages/admin/BrowserToolsPage';
import { DomainDiscoveryPage } from './pages/admin/DomainDiscoveryPage';
import { MCPMarketplace } from './pages/admin/MCPMarketplace';
import { LongContextPage } from './pages/admin/LongContextPage';
import { BashToolPage } from './pages/admin/BashToolPage';

function App() {
  // Sprint 46: Sidebar state moved to individual pages (HomePage, etc.)
  // Sprint 116 Feature 116.2: Add ErrorBoundary, ToastProvider, and ToastContainer
  return (
    <ErrorBoundary>
      <AuthProvider>
        <SettingsProvider>
          <ToastProvider>
            <BrowserRouter>
              <ToastContainer />
              <Routes>
                {/* Public routes - no layout, no auth */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/share/:shareToken" element={<SharedConversationPage />} />

                {/* Protected routes - with layout */}
                <Route
                  path="/*"
                  element={
                    <ProtectedRoute>
                      <AppLayout>
                        <Routes>
                      <Route path="/" element={<HomePage />} />
                      <Route path="/search" element={<SearchResultsPage />} />
                      <Route path="/admin" element={<AdminDashboard />} />
                      <Route path="/admin/health" element={<HealthDashboard />} />
                      <Route path="/admin/legacy" element={<AdminPage />} />
                      <Route path="/admin/indexing" element={<AdminIndexingPage />} />
                      <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
                      <Route path="/admin/costs" element={<CostDashboardPage />} />
                      <Route path="/admin/llm-config" element={<AdminLLMConfigPage />} />
                      <Route path="/admin/domain-training" element={<DomainTrainingPage />} />
                      <Route path="/admin/domain-discovery" element={<DomainDiscoveryPage />} />
                      <Route path="/admin/upload" element={<UploadPage />} />
                      <Route path="/admin/jobs" element={<IngestionJobsPage />} />
                      <Route path="/admin/tools" element={<MCPToolsPage />} />
                      <Route path="/admin/memory" element={<MemoryManagementPage />} />
                      <Route path="/admin/graph-operations" element={<AdminGraphOperationsPage />} />
                      <Route path="/admin/explainability" element={<ExplainabilityPage />} />
                      <Route path="/admin/certification" element={<SkillCertificationPage />} />
                      <Route path="/admin/skills/registry" element={<SkillRegistry />} />
                      <Route path="/admin/skills/:skillName/config" element={<SkillConfigEditor />} />
                      <Route path="/admin/skills/:skillName/tools" element={<ToolAuthorizationPage />} />
                      <Route path="/admin/skills/lifecycle" element={<SkillLifecycleDashboard />} />
                      <Route path="/admin/skills/:skillName/skill-md" element={<SkillMdEditor />} />
                      <Route path="/admin/agent-communication" element={<AgentCommunicationPage />} />
                      <Route path="/admin/agent-hierarchy" element={<AgentHierarchyPage />} />
                      <Route path="/admin/gdpr" element={<GDPRConsentPage />} />
                      <Route path="/admin/audit" element={<AuditTrailPage />} />
                      <Route path="/admin/browser-tools" element={<BrowserToolsPage />} />
                      <Route path="/admin/bash-tool" element={<BashToolPage />} />
                      <Route path="/admin/mcp-marketplace" element={<MCPMarketplace />} />
                      <Route path="/admin/long-context" element={<LongContextPage />} />
                      <Route path="/dashboard/costs" element={<CostDashboardPage />} />
                      <Route path="/settings" element={<Settings />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              }
            />
              </Routes>
            </BrowserRouter>
          </ToastProvider>
        </SettingsProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
