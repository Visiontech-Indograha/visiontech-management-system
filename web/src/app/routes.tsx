import type { ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import { AppShell } from "@/components/templates/AppShell";
import { RequireAuth } from "@/app/RequireAuth";
import { RequireAccess } from "@/app/RequireAccess";
import { TitleLayout } from "@/components/templates/TitleLayout";
import { SetupPage } from "@/pages/auth/SetupPage";
import { LoginPage } from "@/pages/auth/LoginPage";
import { HomePage } from "@/pages/home/HomePage";
import { ComingSoonPage } from "@/pages/system/ComingSoonPage";
import { ForbiddenPage } from "@/pages/system/ForbiddenPage";
import { NotFoundPage } from "@/pages/system/NotFoundPage";
import { UuidParamGuard } from "@/app/UuidParamGuard";
import { NAV_ITEMS, type NavItem } from "./navigation";
import {
  AccountPage,
  AssetsPage,
  AttendancePage,
  AttendanceRecapPage,
  AuditLogPage,
  ClientsPage,
  DirectoryPage,
  EmployeeDetailPage,
  LeavesPage,
  MessPage,
  MyDocumentsPage,
  OffboardingPage,
  OvertimePage,
  OvertimeRecapPage,
  HikvisionDevicesPage,
  SitesPage,
  TeamsPage,
  DailyPlansPage,
  AllocationPage,
  WorkTypesPage,
  DivisionsPage,
  SurveyDetailPage,
  SystemSettingsPage,
  WorkOrdersPage,
  VehicleDocsPage,
  MyVehicleDocsPage,
  HseCampaignsPage,
  VehicleInspectionsPage,
  ArchivePage,
} from "./lazyPages";
import { ChangePasswordPage } from "@/pages/auth/ChangePasswordPage";
import { VerifyCompletionPage } from "@/pages/verify/VerifyCompletionPage";
import { RouteErrorPage } from "@/pages/system/RouteErrorPage";

/** Halaman yang sudah dibangun; sisanya tampil "dibangun pada fase berikutnya". */
const PAGES: Record<string, ReactNode> = {
  "/audit-logs": <AuditLogPage />,
  "/vehicle-documents": <VehicleDocsPage />,
  "/dokumen-saya": <MyVehicleDocsPage />,
  "/system-settings": <SystemSettingsPage />,
  "/directory": <DirectoryPage />,
  "/my-documents": <MyDocumentsPage />,
  "/sites": <SitesPage />,
  "/hikvision": <HikvisionDevicesPage />,
  "/work-types": <WorkTypesPage />,
  "/divisions": <DivisionsPage />,
  "/work-orders": <WorkOrdersPage />,
  "/work-plans": <DailyPlansPage />,
  "/alokasi-mingguan": <AllocationPage />,
  "/clients": <ClientsPage />,
  "/teams": <TeamsPage />,
  "/mess": <MessPage />,
  "/offboarding": <OffboardingPage />,
  "/assets": <AssetsPage />,
  "/attendance": <AttendancePage />,
  "/leaves": <LeavesPage />,
  "/attendance-recap": <AttendanceRecapPage />,
  "/overtime": <OvertimePage />,
  "/overtime-recap": <OvertimeRecapPage />,
  "/safety-campaigns": <HseCampaignsPage />,
  "/vehicle-inspections": <VehicleInspectionsPage />,
  "/archive": <ArchivePage />,
};

/** Route dibangun dari NAV_ITEMS agar menu dan guard selalu sejalan. */
export const routes: RouteObject[] = [
  {
    element: <TitleLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/setup", element: <SetupPage /> }, // publik; isinya menyesuaikan GET /setup/status
      { path: "/admin-login", element: <LoginPage admin /> }, // sengaja tidak ditautkan dari menu/halaman lain
      // QR BAST resmi, publik
      {
        path: "/verify/work-completion/:id",
        element: (
          <UuidParamGuard>
            <VerifyCompletionPage />
          </UuidParamGuard>
        ),
      },
      // Alias URL QR dokumen resmi, publik
      {
        path: "/work-completion/:id",
        element: (
          <UuidParamGuard>
            <VerifyCompletionPage />
          </UuidParamGuard>
        ),
      },
      {
        element: <RequireAuth />,
        children: [
          { path: "/change-password", element: <ChangePasswordPage /> },
          {
            element: <AppShell />,
            children: [
              { path: "/", element: <HomePage /> },
              ...NAV_ITEMS.filter((i) => i.path !== "/").map((item) => ({
                path: item.path,
                element: (
                  <RequireAccess item={item}>{PAGES[item.path] ?? <ComingSoonPage title={item.label} />}</RequireAccess>
                ),
              })),
              { path: "/surveys/:surveyId",
                element: (
                  <UuidParamGuard param="surveyId">
                    <RequireAccess item={{ path: "/surveys", label: "Survei", requires: ["create:plan"] } as NavItem}>
                      <SurveyDetailPage />
                    </RequireAccess>
                  </UuidParamGuard>
                ),
              },
              // Redireksi URL lama ke alur terpadu Work Orders
              { path: "/surveys", element: <Navigate to="/work-orders" replace /> },
              { path: "/projects", element: <Navigate to="/work-orders" replace /> },
              { path: "/work-completions", element: <Navigate to="/work-orders" replace /> },
              // Alias bahasa Indonesia
              { path: "/inventory", element: <Navigate to="/assets" replace /> },
              { path: "/presensi", element: <Navigate to="/attendance" replace /> },
              { path: "/hse", element: <Navigate to="/safety-campaigns" replace /> },
              { path: "/finances", element: <Navigate to="/alokasi-mingguan" replace /> },
              {
                path: "/directory/:id",
                element: (
                  <UuidParamGuard>
                    <RequireAccess item={{ path: "/directory", label: "Direktori", requires: ["view:users"] } as NavItem}>
                      <EmployeeDetailPage />
                    </RequireAccess>
                  </UuidParamGuard>
                ),
              },
              { path: "/account", element: <AccountPage /> },
            ],
          },
        ],
      },
      { path: "/403", element: <ForbiddenPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
