import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import UploadPage from './pages/Upload';
import Results from './pages/Results';
import HistoryPage from './pages/History';
import ComparePage from './pages/Compare';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Layout>
        <Routes>
          <Route path="/" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
          <Route path="/upload" element={<ErrorBoundary><UploadPage /></ErrorBoundary>} />
          <Route path="/results" element={<ErrorBoundary><Results /></ErrorBoundary>} />
          <Route path="/history" element={<ErrorBoundary><HistoryPage /></ErrorBoundary>} />
          <Route path="/compare" element={<ErrorBoundary><ComparePage /></ErrorBoundary>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </Layout>
      </ToastProvider>
    </BrowserRouter>
  );
}
