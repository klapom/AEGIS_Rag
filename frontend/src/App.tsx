/**
 * App Component
 * Sprint 15 Feature 15.4: Main App with React Router
 * Sprint 28 Feature 28.3: Settings page and context provider
 * Sprint 31 Feature 31.10b: Cost Dashboard route registration
 * Sprint 38 Feature 38.1b: JWT Authentication Frontend
 * Sprint 38 Feature 38.3: Share Conversation Links (public route)
 */

import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SettingsProvider } from './contexts/SettingsContext';
import { AuthProvider } from './contexts/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { SearchResultsPage } from './pages/SearchResultsPage';
import { HealthDashboard } from './pages/HealthDashboard';
import { AdminPage } from './pages/AdminPage';
import { Settings } from './pages/Settings';
import { GraphAnalyticsPage } from './pages/admin/GraphAnalyticsPage';
import { CostDashboardPage } from './pages/admin/CostDashboardPage';
import { AdminIndexingPage } from './pages/admin/AdminIndexingPage';
import { AdminLLMConfigPage } from './pages/admin/AdminLLMConfigPage';
import { SharedConversationPage } from './pages/SharedConversationPage';
import { DomainTrainingPage } from './pages/admin/DomainTrainingPage';
import { UploadPage } from './pages/admin/UploadPage';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleToggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <AuthProvider>
      <SettingsProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes - no layout, no auth */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/share/:shareToken" element={<SharedConversationPage />} />

            {/* Protected routes - with layout */}
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AppLayout
                    sidebarOpen={sidebarOpen}
                    onToggleSidebar={handleToggleSidebar}
                  >
                    <Routes>
                      <Route path="/" element={<HomePage />} />
                      <Route path="/search" element={<SearchResultsPage />} />
                      <Route path="/health" element={<HealthDashboard />} />
                      <Route path="/admin" element={<AdminPage />} />
                      <Route path="/admin/indexing" element={<AdminIndexingPage />} />
                      <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
                      <Route path="/admin/costs" element={<CostDashboardPage />} />
                      <Route path="/admin/llm-config" element={<AdminLLMConfigPage />} />
                      <Route path="/admin/domain-training" element={<DomainTrainingPage />} />
                      <Route path="/admin/upload" element={<UploadPage />} />
                      <Route path="/dashboard/costs" element={<CostDashboardPage />} />
                      <Route path="/settings" element={<Settings />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </SettingsProvider>
    </AuthProvider>
  );
}

export default App;
