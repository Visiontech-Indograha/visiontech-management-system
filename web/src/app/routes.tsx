import type { ReactNode } from "react";
import type { RouteObject } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAccess, RequireAuth } from "@/components/layout/guards";
import { AssetsPage } from "@/features/assets/AssetsPage";
import { AttendancePage } from "@/features/attendance/AttendancePage";
import { AuditLogPage } from "@/features/audit/AuditLogPage";
import { DirectoryPage } from "@/features/directory/DirectoryPage";
import { EmployeeDetailPage } from "@/features/directory/EmployeeDetailPage";
import { SitesPage } from "@/features/sites/SitesPage";
import { WorkPlanDetailPage } from "@/features/work-plans/WorkPlanDetailPage";
import { WorkPlansPage } from "@/features/work-plans/WorkPlansPage";
import { AttendanceRecapPage } from "@/features/monitoring/AttendanceRecapPage";
import { OvertimeRecapPage } from "@/features/monitoring/OvertimeRecapPage";
import { TimelinePage } from "@/features/monitoring/TimelinePage";
import { ChangePasswordPage } from "@/pages/auth/ChangePasswordPage";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ComingSoonPage, ForbiddenPage, HomePage, NotFoundPage } from "@/pages/Placeholders";
import { NAV_ITEMS } from "./navigation";

/** Halaman yang sudah dibangun; sisanya tampil "dibangun pada fase berikutnya". */
const PAGES: Record<string, ReactNode> = {
  "/audit-logs": <AuditLogPage />,
  "/directory": <DirectoryPage />,
  "/sites": <SitesPage />,
  "/work-plans": <WorkPlansPage />,
  "/assets": <AssetsPage />,
  "/timeline": <TimelinePage />,
  "/attendance": <AttendancePage />,
  "/attendance-recap": <AttendanceRecapPage />,
  "/overtime-recap": <OvertimeRecapPage />,
};

/** Route dibangun dari NAV_ITEMS agar menu dan guard selalu sejalan. */
export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  { path: "/admin-login", element: <LoginPage admin /> }, // sengaja tidak ditautkan dari menu/halaman lain
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
          {
            path: "/directory/:id",
            element: (
              <RequireAccess item={NAV_ITEMS.find((i) => i.path === "/directory")!}>
                <EmployeeDetailPage />
              </RequireAccess>
            ),
          },
          { path: "/work-plans/:id", element: <WorkPlanDetailPage /> },
          { path: "/forbidden", element: <ForbiddenPage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];

