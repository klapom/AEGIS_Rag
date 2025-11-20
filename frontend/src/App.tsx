/**
 * App Component
 * Sprint 15 Feature 15.4: Main App with React Router
 * Sprint 28 Feature 28.3: Settings page and context provider
 * Sprint 31 Feature 31.10b: Cost Dashboard route registration
 */

import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SettingsProvider } from './contexts/SettingsContext';
import { AppLayout } from './components/layout/AppLayout';
import { HomePage } from './pages/HomePage';
import { SearchResultsPage } from './pages/SearchResultsPage';
import { HealthDashboard } from './pages/HealthDashboard';
import { AdminPage } from './pages/AdminPage';
import { Settings } from './pages/Settings';
import { GraphAnalyticsPage } from './pages/admin/GraphAnalyticsPage';
import { CostDashboardPage } from './pages/admin/CostDashboardPage';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleToggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <SettingsProvider>
      <BrowserRouter>
        <AppLayout
          sidebarOpen={sidebarOpen}
          onToggleSidebar={handleToggleSidebar}
        >
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchResultsPage />} />
            <Route path="/health" element={<HealthDashboard />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
            <Route path="/admin/costs" element={<CostDashboardPage />} />
            <Route path="/dashboard/costs" element={<CostDashboardPage />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </SettingsProvider>
  );
}

export default App;
