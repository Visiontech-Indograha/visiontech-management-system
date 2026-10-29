import type { ReactNode } from "react";
import type { RouteObject } from "react-router-dom";
import { AppShell } from "@/components/templates/AppShell";
import { RequireAuth } from "@/app/RequireAuth";
import { RequireAccess } from "@/app/RequireAccess";
import { TitleLayout } from "@/components/templates/TitleLayout";
import { LoginPage } from "@/pages/auth/LoginPage";
import { HomePage } from "@/pages/home/HomePage";
import { ComingSoonPage } from "@/pages/system/ComingSoonPage";
import { ForbiddenPage } from "@/pages/system/ForbiddenPage";
import { NotFoundPage } from "@/pages/system/NotFoundPage";
import { UuidParamGuard } from "@/app/UuidParamGuard";
import { NAV_ITEMS } from "./navigation";
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
  OvertimeRecapPage,
  ProjectsPage,
  SitesPage,
  TeamsPage,
  DailyPlansPage,
  WorkTypesPage,
  WorkCompletionsPage,
  SurveyDetailPage,
  SurveysPage,
} from "./lazyPages";
import { ChangePasswordPage } from "@/pages/auth/ChangePasswordPage";
import { VerifyCompletionPage } from "@/pages/verify/VerifyCompletionPage";

/** Halaman yang sudah dibangun; sisanya tampil "dibangun pada fase berikutnya". */
const PAGES: Record<string, ReactNode> = {
  "/audit-logs": <AuditLogPage />,
  "/directory": <DirectoryPage />,
  "/my-documents": <MyDocumentsPage />,
  "/sites": <SitesPage />,
  "/work-types": <WorkTypesPage />,
  "/work-plans": <DailyPlansPage />,
  "/work-completions": <WorkCompletionsPage />,
  "/clients": <ClientsPage />,
  "/projects": <ProjectsPage />,
  "/surveys": <SurveysPage />,
  "/teams": <TeamsPage />,
  "/mess": <MessPage />,
  "/offboarding": <OffboardingPage />,
  "/assets": <AssetsPage />,
  "/attendance": <AttendancePage />,
  "/leaves": <LeavesPage />,
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
              {
                path: "/surveys/:id",
                element: (
                  <RequireAccess item={NAV_ITEMS.find((i) => i.path === "/surveys")!}>
                    <UuidParamGuard>
                      <SurveyDetailPage />
                    </UuidParamGuard>
                  </RequireAccess>
                ),
              },
              {
                path: "/directory/:id",
                element: (
                  <RequireAccess item={NAV_ITEMS.find((i) => i.path === "/directory")!}>
                    <UuidParamGuard>
                      <EmployeeDetailPage />
                    </UuidParamGuard>
                  </RequireAccess>
                ),
              },
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
