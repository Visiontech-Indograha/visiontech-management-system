import { Suspense, type ReactNode } from "react";
import type { RouteObject } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAccess, RequireAuth } from "@/components/layout/guards";
import { TitleLayout } from "@/components/layout/TitleLayout";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ComingSoonPage, ForbiddenPage, HomePage, NotFoundPage } from "@/pages/Placeholders";
import { NAV_ITEMS } from "./navigation";
import { AssetsPage, AttendancePage, AuditLogPage, DirectoryPage, EmployeeDetailPage, MyDocumentsPage, SitesPage, WorkTypesPage, WorkPlanDetailPage, WorkPlansPage, PlanEditorPage, AttendanceRecapPage, OvertimeRecapPage, PresentationPage, TimelinePage, AccountPage } from "./lazyPages";
import { VerifyPage } from "@/features/verify/VerifyPage";
import { ChangePasswordPage } from "@/pages/auth/ChangePasswordPage";


/** Halaman yang sudah dibangun; sisanya tampil "dibangun pada fase berikutnya". */
const PAGES: Record<string, ReactNode> = {
  "/audit-logs": <AuditLogPage />,
  "/directory": <DirectoryPage />,
  "/my-documents": <MyDocumentsPage />,
  "/sites": <SitesPage />,
  "/work-types": <WorkTypesPage />,
  "/work-plans": <WorkPlansPage />,
  "/assets": <AssetsPage />,
  "/timeline": <TimelinePage />,
  "/attendance": <AttendancePage />,
  "/attendance-recap": <AttendanceRecapPage />,
  "/overtime-recap": <OvertimeRecapPage />,
};

/** Route dibangun dari NAV_ITEMS agar menu dan guard selalu sejalan. */
export const routes: RouteObject[] = [
  {
    element: <TitleLayout />,
    children: [
  { path: "/login", element: <LoginPage /> },
  { path: "/admin-login", element: <LoginPage admin /> }, // sengaja tidak ditautkan dari menu/halaman lain
  // PUBLIK: tujuan pemindaian QR tanda tangan; tanpa login dan di luar AppShell. Token boleh memuat "/".
  { path: "/verify/*", element: <VerifyPage /> },
  {
    element: <RequireAuth />,
    children: [
      { path: "/change-password", element: <ChangePasswordPage /> },
      // Mode presentasi laporan (M5): layar penuh untuk rapat, di luar AppShell.
      {
        path: "/work-plans/:id/presentation",
        element: (
          <Suspense fallback={null}>
            <PresentationPage />
          </Suspense>
        ),
      },
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
          { path: "/work-plans/new", element: <RequireAccess item={NAV_ITEMS.find((i) => i.path === "/work-plans")!}><PlanEditorPage /></RequireAccess> },
          { path: "/work-plans/:id/edit", element: <PlanEditorPage /> },
          { path: "/work-plans/:id/amend/:changeId", element: <PlanEditorPage /> },
          { path: "/work-plans/:id/revise", element: <PlanEditorPage /> },
          { path: "/work-plans/:id", element: <WorkPlanDetailPage /> },
          { path: "/account", element: <AccountPage /> },
          { path: "/forbidden", element: <ForbiddenPage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
    ],
  },
];
