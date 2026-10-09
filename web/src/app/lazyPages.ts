import { lazy } from "react";

/** Halaman dimuat saat dibuka (code-splitting) — muatan awal kecil (R-12, performa). */
export const AssetsPage = lazy(() => import("@/features/assets/pages/AssetsPage").then((m) => ({ default: m.AssetsPage })));
export const AttendancePage = lazy(() => import("@/features/attendance/pages/AttendancePage").then((m) => ({ default: m.AttendancePage })));
export const AuditLogPage = lazy(() => import("@/features/audit/pages/AuditLogPage").then((m) => ({ default: m.AuditLogPage })));
export const DirectoryPage = lazy(() => import("@/features/directory/pages/DirectoryPage").then((m) => ({ default: m.DirectoryPage })));
export const EmployeeDetailPage = lazy(() => import("@/features/directory/pages/EmployeeDetailPage").then((m) => ({ default: m.EmployeeDetailPage })));
export const MyDocumentsPage = lazy(() => import("@/features/directory/pages/MyDocumentsPage").then((m) => ({ default: m.MyDocumentsPage })));
export const WorkTypesPage = lazy(() => import("@/features/work-types/pages/WorkTypesPage").then((m) => ({ default: m.WorkTypesPage })));
export const SitesPage = lazy(() => import("@/features/sites/pages/SitesPage").then((m) => ({ default: m.SitesPage })));
export const WorkPlanDetailPage = lazy(() => import("@/features/work-plans/pages/WorkPlanDetailPage").then((m) => ({ default: m.WorkPlanDetailPage })));
export const PlanEditorPage = lazy(() => import("@/features/work-plans/pages/PlanEditorPage").then((m) => ({ default: m.PlanEditorPage })));
export const WorkPlansPage = lazy(() => import("@/features/work-plans/pages/WorkPlansPage").then((m) => ({ default: m.WorkPlansPage })));
export const AttendanceRecapPage = lazy(() => import("@/features/monitoring/pages/AttendanceRecapPage").then((m) => ({ default: m.AttendanceRecapPage })));
export const OvertimeRecapPage = lazy(() => import("@/features/monitoring/pages/OvertimeRecapPage").then((m) => ({ default: m.OvertimeRecapPage })));
export const TimelinePage = lazy(() => import("@/features/monitoring/pages/TimelinePage").then((m) => ({ default: m.TimelinePage })));
export const AccountPage = lazy(() => import("@/features/account/pages/AccountPage").then((m) => ({ default: m.AccountPage })));
export const PresentationPage = lazy(() => import("@/features/work-plans/pages/PresentationPage").then((m) => ({ default: m.PresentationPage })));
