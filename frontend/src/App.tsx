import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import { AdminLogin } from './pages/AdminLogin';
import { AdminClusters } from './pages/AdminClusters';
import { ClusterPage } from './pages/cluster/ClusterPage';
import { AdminUsers } from './pages/AdminUsers';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false, // Don't retry on 401 errors
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin/clusters" element={<AdminClusters />} />
          <Route path="/admin/clusters/:clusterName" element={<ClusterPage />} />
          <Route path="/admin/config" element={<Navigate to="/admin/clusters" replace />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
