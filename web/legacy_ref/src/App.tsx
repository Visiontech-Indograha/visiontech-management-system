import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { queryClient } from "./lib/queryClient";
import { AuthProvider } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { RoleRoute } from "./components/layout/RoleRoute";
import { AppLayout } from "./components/layout/AppLayout";
import { LoginPage } from "./pages/auth/LoginPage";
import DashboardPage from "./pages/dashboard/DashboardPage";
import EmployeeListPage from "./pages/hr/EmployeeListPage";
import EmployeeDetailPage from "./pages/hr/EmployeeDetailPage";
import AttendanceHistoryPage from "./pages/attendance/AttendanceHistoryPage";
import LeaveApprovalPage from "./pages/attendance/LeaveApprovalPage";
import LogbookPage from "./pages/om/LogbookPage";
import WorkPlanPage from "./pages/pm/WorkPlanPage";
import ProgressReportPage from "./pages/pm/ProgressReportPage";
import TimesheetExportPage from "./pages/export/TimesheetExportPage";
import PMPage from "./pages/pm/PMPage";
import OMPage from "./pages/om/OMPage";
import HESPage from "./pages/hes/HESPage";
import HESPlanPage from "./pages/hes/HESPlanPage";
import PortofolioPage from "./pages/hes/PortofolioPage";
import InternalDocumentPage from "./pages/hes/InternalDocumentPage";
import FinancePage from "./pages/finance/FinancePage";
import SystemSetupPage from "./pages/settings/SystemSetupPage";
import InventoryPage from "./pages/inventory/InventoryPage";
import { UserRole } from "./types/auth";

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Toaster position="top-right" />
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            
            {/* Base Redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            {/* Protected Routes dengan Layout Utama */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                
                {/* Semua role bisa akses Dashboard */}
                <Route path="/dashboard" element={<DashboardPage />} />
                
                {/* Role Spesifik */}
                <Route path="/attendance/history" element={<AttendanceHistoryPage />} />
                
                <Route
                  path="/hr/employees"
                  element={<RoleRoute allowedRoles={[UserRole.ADMIN, UserRole.HR_HES, UserRole.OM]}><EmployeeListPage /></RoleRoute>}
                />
                <Route
                  path="/hr/employees/:id"
                  element={<RoleRoute allowedRoles={[UserRole.ADMIN, UserRole.HR_HES, UserRole.OM]}><EmployeeDetailPage /></RoleRoute>}
                />
                <Route
                  path="/hr/leave" 
                  element={<RoleRoute allowedRoles={[UserRole.ADMIN, UserRole.HR_HES, UserRole.PM, UserRole.OM]}><LeaveApprovalPage /></RoleRoute>} 
                />
                
                <Route 
                  path="/pm" 
                  element={<RoleRoute allowedRoles={[UserRole.PM, UserRole.ADMIN]}><PMPage /></RoleRoute>} 
                />
                <Route 
                  path="/pm/work-plan" 
                  element={<RoleRoute allowedRoles={[UserRole.PM, UserRole.OM, UserRole.ADMIN]}><WorkPlanPage /></RoleRoute>} 
                />
                <Route 
                  path="/pm/progress" 
                  element={<RoleRoute allowedRoles={[UserRole.PM, UserRole.OM, UserRole.ADMIN]}><ProgressReportPage /></RoleRoute>} 
                />
                
                <Route 
                  path="/om" 
                  element={<RoleRoute allowedRoles={[UserRole.OM, UserRole.ADMIN]}><OMPage /></RoleRoute>} 
                />
                <Route 
                  path="/om/logbook" 
                  element={<RoleRoute allowedRoles={[UserRole.OM, UserRole.PM, UserRole.HR_HES, UserRole.ADMIN]}><LogbookPage /></RoleRoute>} 
                />
                
                <Route 
                  path="/hes/overview" 
                  element={<RoleRoute allowedRoles={[UserRole.HR_HES, UserRole.ADMIN, UserRole.OM]}><HESPage /></RoleRoute>} 
                />
                <Route
                  path="/hes/plan"
                  element={<RoleRoute allowedRoles={[UserRole.HR_HES, UserRole.ADMIN, UserRole.OM]}><HESPlanPage /></RoleRoute>}
                />
                <Route
                  path="/hes/documents"
                  element={<RoleRoute allowedRoles={[UserRole.HR_HES, UserRole.ADMIN, UserRole.OM]}><InternalDocumentPage /></RoleRoute>}
                />
                <Route 
                  path="/hes/portofolio" 
                  element={<RoleRoute allowedRoles={[UserRole.HR_HES, UserRole.ADMIN, UserRole.OM]}><PortofolioPage /></RoleRoute>} 
                />
                
                <Route 
                  path="/finance/overview" 
                  element={<RoleRoute allowedRoles={[UserRole.FINANCE, UserRole.ADMIN]}><FinancePage /></RoleRoute>} 
                />
                <Route
                  path="/finance/timesheet"
                  element={<RoleRoute allowedRoles={[UserRole.FINANCE, UserRole.OM, UserRole.ADMIN]}><TimesheetExportPage /></RoleRoute>}
                />

                <Route
                  path="/settings"
                  element={<RoleRoute allowedRoles={[UserRole.ADMIN, UserRole.HR_HES]}><SystemSetupPage /></RoleRoute>}
                />
                <Route
                  path="/inventory"
                  element={<RoleRoute allowedRoles={[UserRole.ADMIN, UserRole.OM, UserRole.HR_HES]}><InventoryPage /></RoleRoute>}
                />

              </Route>
            </Route>
            
            {/* 404 Fallback */}
            <Route path="*" element={
              <div className="flex h-screen items-center justify-center">
                <div className="text-center">
                  <h1 className="text-4xl font-bold">404</h1>
                  <p className="mt-2">Halaman tidak ditemukan.</p>
                  <a href="/dashboard" className="text-blue-600 hover:underline mt-4 inline-block">Kembali ke Beranda</a>
                </div>
              </div>
            } />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;