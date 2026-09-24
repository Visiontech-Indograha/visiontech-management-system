import type { ReactNode } from "react";
import type { RouteObject } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAccess, RequireAuth } from "@/components/layout/guards";
import { AuditLogPage } from "@/features/audit/AuditLogPage";
import {
  
  
  SitesPage,
  
  
} from "@/features/master/pages";
import { AttendancePage } from "@/features/attendance/AttendancePage";
import { DirectoryPage } from "@/features/directory/DirectoryPage";
import { DocumentTypesPage } from "@/features/directory/DocumentTypesPage";
import { EmployeeDetailPage } from "@/features/directory/EmployeeDetailPage";
import { IncompletePage } from "@/features/directory/IncompletePage";
import { MyDocumentsPage } from "@/features/directory/MyDocuments";
import { UsersPage } from "@/features/users/UsersPage";
import { ChangePasswordPage } from "@/pages/auth/ChangePasswordPage";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ComingSoonPage, ForbiddenPage, HomePage, NotFoundPage } from "@/pages/Placeholders";
import { NAV_ITEMS } from "./navigation";

/** Halaman yang sudah dibangun; sisanya tampil "dibangun pada fase berikutnya". */
const PAGES: Record<string, ReactNode> = {
  "/users": <UsersPage />,
  "/audit-logs": <AuditLogPage />,
  "/directory": <DirectoryPage />,
  "/attendance": <AttendancePage mode="all" />,
  "/attendance/team": <AttendancePage mode="team" />,
  "/documents/incomplete": <IncompletePage />,
  "/master/document-types": <DocumentTypesPage />,
  "/my-documents": <MyDocumentsPage />,
  "/master/sites": <SitesPage />,
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
          { path: "/forbidden", element: <ForbiddenPage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];

