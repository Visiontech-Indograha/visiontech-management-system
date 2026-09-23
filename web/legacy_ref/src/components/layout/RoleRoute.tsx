import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";

interface RoleRouteProps {
  allowedRoles: UserRole[];
  children?: React.ReactNode;
}

export const RoleRoute: React.FC<RoleRouteProps> = ({ allowedRoles, children }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-gray-500">Memeriksa otorisasi...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    // Pengguna login tapi tidak memiliki peran yang sesuai
    return (
      <div className="flex flex-col h-full items-center justify-center mt-20">
        <h1 className="text-3xl font-bold text-red-600 mb-4">Akses Ditolak</h1>
        <p className="text-gray-700">Anda tidak memiliki izin untuk mengakses halaman ini.</p>
      </div>
    );
  }

  return <>{children ? children : <Outlet />}</>;
};
