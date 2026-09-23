import React, { useState } from "react";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";
import { NotificationBell } from "./NotificationBell";

export const AppLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  // Navigasi dinamis berdasarkan role — sesuai matriks RBAC di AGENTS.md
  const getNavItems = () => {
    if (!user) return [];

    const role = user.role;
    const isAdmin = role === UserRole.ADMIN;
    const isHR = role === UserRole.HR_HES;
    const isFinance = role === UserRole.FINANCE;
    const isPM = role === UserRole.PM;
    const isOM = role === UserRole.OM;

    const items: { label: string; path: string; icon?: string }[] = [
      { label: "Dashboard", path: "/dashboard" },
    ];

    if (isPM) {
      items.push({ label: "PM Overview", path: "/pm" });
    }
    if (isOM) {
      items.push({ label: "OM Overview", path: "/om" });
    }

    // --- Manajemen Karyawan (Admin, HR_HES, OM) ---
    if (isAdmin || isHR || isOM) {
      items.push({ label: "Data Karyawan", path: "/hr/employees" });
    }

    // --- Absensi & Cuti (Admin, HR_HES, PM, OM) ---
    if (isAdmin || isHR || isPM || isOM) {
      items.push({ label: "Riwayat Absensi", path: "/attendance/history" });
      items.push({ label: "Approval Cuti", path: "/hr/leave" });
    }

    // --- Work Plan & Lapangan (Admin, PM, OM) ---
    if (isAdmin || isPM || isOM) {
      items.push({ label: "Work Plan", path: "/pm/work-plan" });
      items.push({ label: "Laporan Lapangan", path: "/pm/progress" });
    }

    // --- Logbook (Admin, HR_HES, PM, OM) ---
    if (isAdmin || isHR || isPM || isOM) {
      items.push({ label: "Logbook", path: "/om/logbook" });
    }

    // --- HES & Portofolio (Admin, HR_HES, OM) ---
    if (isAdmin || isHR || isOM) {
      items.push({ label: "HES Overview", path: "/hes/overview" });
      items.push({ label: "HES Plan", path: "/hes/plan" });
      items.push({ label: "Dokumen Internal", path: "/hes/documents" });
      items.push({ label: "Portofolio", path: "/hes/portofolio" });
    }

    // --- Timesheet Export (Admin, Finance, OM) ---
    if (isAdmin || isFinance || isOM) {
      if (isFinance) {
        items.push({ label: "Finance Overview", path: "/finance/overview" });
      }
      items.push({ label: "Timesheet Export", path: "/finance/timesheet" });
    }

    // --- Inventory (Admin, OM, HR_HES) ---
    if (isAdmin || isOM || isHR) {
      items.push({ label: "Inventory", path: "/inventory" });
    }

    // --- System Setup (Admin, HR_HES) ---
    if (isAdmin || isHR) {
      items.push({ label: "System Setup", path: "/settings" });
    }

    return items;
  };

  const navItems = getNavItems();

  return (
    <div className="flex h-screen bg-gray-100 font-sans">
      {/* Sidebar untuk Desktop */}
      <aside className={`fixed inset-y-0 left-0 bg-blue-900 text-white w-64 flex flex-col transform ${sidebarOpen ? "translate-x-0" : "-translate-x-full"} md:translate-x-0 transition-transform duration-200 ease-in-out z-20`}>
        <div className="flex items-center justify-between p-4 border-b border-blue-800 shrink-0">
          <h1 className="text-xl font-bold">VMS</h1>
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden text-white focus:outline-none"
            aria-label="Tutup menu navigasi"
          >
            ×
          </button>
        </div>
        <div className="p-4 shrink-0">
          <p className="text-sm text-blue-300">Selamat datang,</p>
          <p className="font-semibold">{user?.username}</p>
          <p className="text-xs bg-blue-800 px-2 py-1 rounded inline-block mt-1 uppercase">
            {user?.role.replace("_", " ")}
          </p>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname.startsWith(item.path);
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`block px-4 py-3 text-sm transition-colors ${
                      isActive ? "bg-blue-800 border-l-4 border-blue-400" : "hover:bg-blue-800"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="p-4 border-t border-blue-800 shrink-0">
          <button
            onClick={handleLogout}
            className="w-full text-left px-4 py-2 text-sm hover:bg-blue-800 rounded transition-colors text-red-300 hover:text-red-200"
          >
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col md:ml-64 min-w-0">
        {/* Header (mobile: judul + hamburger; desktop: hanya bel notifikasi) */}
        <header className="bg-white shadow-sm border-b p-4 flex justify-between items-center z-10">
          <h2 className="text-lg font-semibold text-gray-800 md:hidden">Visiontech VMS</h2>
          <div className="hidden md:block" />
          <div className="flex items-center gap-2">
            <NotificationBell />
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-gray-600 focus:outline-none p-1 md:hidden"
              aria-label="Buka menu navigasi"
            >
              ☰
            </button>
          </div>
        </header>

        {/* Dynamic Outlet */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-50 p-4 md:p-8">
          <Outlet />
        </main>
      </div>

      {/* Overlay mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-10 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};
