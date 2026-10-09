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
export const WorkPlanDetailPage = lazy(() => import("@/pages/work-plans/WorkPlanDetailPage").then((m) => ({ default: m.WorkPlanDetailPage })));
export const PlanEditorPage = lazy(() => import("@/pages/work-plans/PlanEditorPage").then((m) => ({ default: m.PlanEditorPage })));
export const WorkPlansPage = lazy(() => import("@/pages/work-plans/WorkPlansPage").then((m) => ({ default: m.WorkPlansPage })));
export const AttendanceRecapPage = lazy(() => import("@/pages/monitoring/AttendanceRecapPage").then((m) => ({ default: m.AttendanceRecapPage })));
export const OvertimeRecapPage = lazy(() => import("@/pages/monitoring/OvertimeRecapPage").then((m) => ({ default: m.OvertimeRecapPage })));
export const TimelinePage = lazy(() => import("@/pages/monitoring/TimelinePage").then((m) => ({ default: m.TimelinePage })));
export const AccountPage = lazy(() => import("@/pages/account/AccountPage").then((m) => ({ default: m.AccountPage })));
export const PresentationPage = lazy(() => import("@/pages/work-plans/PresentationPage").then((m) => ({ default: m.PresentationPage })));
