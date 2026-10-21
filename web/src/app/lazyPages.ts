import { lazy } from "react";

/** Halaman dimuat saat dibuka (code-splitting) — muatan awal kecil (R-12, performa). */
export const AssetsPage = lazy(() => import("@/pages/assets/AssetsPage").then((m) => ({ default: m.AssetsPage })));
export const AttendancePage = lazy(() => import("@/pages/attendance/AttendancePage").then((m) => ({ default: m.AttendancePage })));
export const AuditLogPage = lazy(() => import("@/pages/audit/AuditLogPage").then((m) => ({ default: m.AuditLogPage })));
export const DirectoryPage = lazy(() => import("@/pages/directory/DirectoryPage").then((m) => ({ default: m.DirectoryPage })));
export const EmployeeDetailPage = lazy(() => import("@/pages/directory/EmployeeDetailPage").then((m) => ({ default: m.EmployeeDetailPage })));
export const MyDocumentsPage = lazy(() => import("@/pages/directory/MyDocumentsPage").then((m) => ({ default: m.MyDocumentsPage })));
export const WorkTypesPage = lazy(() => import("@/pages/work-types/WorkTypesPage").then((m) => ({ default: m.WorkTypesPage })));
export const SitesPage = lazy(() => import("@/pages/sites/SitesPage").then((m) => ({ default: m.SitesPage })));
export const DailyPlansPage = lazy(() => import("@/pages/work-plans/DailyPlansPage").then((m) => ({ default: m.DailyPlansPage })));
export const AttendanceRecapPage = lazy(() => import("@/pages/monitoring/AttendanceRecapPage").then((m) => ({ default: m.AttendanceRecapPage })));
export const OvertimeRecapPage = lazy(() => import("@/pages/monitoring/OvertimeRecapPage").then((m) => ({ default: m.OvertimeRecapPage })));
export const AccountPage = lazy(() => import("@/pages/account/AccountPage").then((m) => ({ default: m.AccountPage })));

// Halaman Baru Master Schema V2
export const TeamsPage = lazy(() => import("@/pages/teams/TeamsPage").then((m) => ({ default: m.TeamsPage })));
export const MessPage = lazy(() => import("@/pages/mess/MessPage").then((m) => ({ default: m.MessPage })));
export const OffboardingPage = lazy(() => import("@/pages/offboarding/OffboardingPage").then((m) => ({ default: m.OffboardingPage })));
export const WorkCompletionsPage = lazy(() => import("@/pages/work-completions/WorkCompletionsPage").then((m) => ({ default: m.WorkCompletionsPage })));
export const SurveysPage = lazy(() => import("@/pages/surveys/SurveysPage").then((m) => ({ default: m.SurveysPage })));
export const SurveyDetailPage = lazy(() => import("@/pages/surveys/SurveyDetailPage").then((m) => ({ default: m.SurveyDetailPage })));
