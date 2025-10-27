/**
 * App Component
 * Sprint 15 Feature 15.4: Main App with React Router
 */

import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { HomePage } from './pages/HomePage';
import { SearchResultsPage } from './pages/SearchResultsPage';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleToggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <BrowserRouter>
      <AppLayout
        sidebarOpen={sidebarOpen}
        onToggleSidebar={handleToggleSidebar}
      >
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchResultsPage />} />
          {/* Feature 15.6: Health Dashboard */}
          {/* <Route path="/health" element={<HealthDashboard />} /> */}
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}

export default App;
