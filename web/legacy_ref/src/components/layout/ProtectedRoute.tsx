import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

/**
 * Gerbang autentikasi murni (sudah login / belum). Pembatasan per-role
 * dilakukan oleh RoleRoute, dipasang di masing-masing <Route> di App.tsx.
 */
export const ProtectedRoute: React.FC = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    // Tampilkan skeleton atau spinner loading
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-gray-500 text-lg">Memuat Profil...</div>
      </div>
    );
  }

  if (!user) {
    // Belum login, tendang ke login
    return <Navigate to="/login" replace />;
  }

  // Render child routes
  return <Outlet />;
};
