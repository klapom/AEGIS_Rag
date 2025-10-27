/**
 * App Component
 * Sprint 15 Feature 15.2: Main App with Perplexity Layout
 */

import { useState } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { HomePage } from './pages/HomePage';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleToggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <AppLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={handleToggleSidebar}
    >
      <HomePage />
    </AppLayout>
  );
}

export default App;
