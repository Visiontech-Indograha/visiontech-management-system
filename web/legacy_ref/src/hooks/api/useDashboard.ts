import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api";
import {
  CalendarEventItem,
  DailyReportRateResponse,
  DashboardSummaryResponse,
  EmployeeStatusResponse,
  ExpiringDocumentItem,
  FieldPerformancePoint,
  RecentActivityItem,
} from "../../types/dashboard";

export const useDashboardSummary = () => {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: async () => {
      const { data } = await api.get<DashboardSummaryResponse>("/api/v1/dashboard/summary");
      return data;
    },
  });
};

export const useExpiringDocuments = (withinDays = 90) => {
  return useQuery({
    queryKey: ["dashboard", "expiring-documents", withinDays],
    queryFn: async () => {
      const { data } = await api.get<ExpiringDocumentItem[]>("/api/v1/dashboard/expiring-documents", {
        params: { within_days: withinDays },
      });
      return data;
    },
  });
};

export const useEmployeeStatus = () => {
  return useQuery({
    queryKey: ["dashboard", "employee-status"],
    queryFn: async () => {
      const { data } = await api.get<EmployeeStatusResponse>("/api/v1/dashboard/employee-status");
      return data;
    },
  });
};

export const useDailyReportRate = () => {
  return useQuery({
    queryKey: ["dashboard", "daily-report-rate"],
    queryFn: async () => {
      const { data } = await api.get<DailyReportRateResponse>("/api/v1/dashboard/daily-report-rate");
      return data;
    },
  });
};

export const useFieldPerformance = () => {
  return useQuery({
    queryKey: ["dashboard", "field-performance"],
    queryFn: async () => {
      const { data } = await api.get<FieldPerformancePoint[]>("/api/v1/dashboard/field-performance");
      return data;
    },
  });
};

export const useRecentActivity = (limit = 15) => {
  return useQuery({
    queryKey: ["dashboard", "recent-activity", limit],
    queryFn: async () => {
      const { data } = await api.get<RecentActivityItem[]>("/api/v1/dashboard/recent-activity", {
        params: { limit },
      });
      return data;
    },
  });
};

export const useCalendarEvents = (start: string, end: string) => {
  return useQuery({
    queryKey: ["dashboard", "calendar", start, end],
    queryFn: async () => {
      const { data } = await api.get<CalendarEventItem[]>("/api/v1/dashboard/calendar", {
        params: { start, end },
      });
      return data;
    },
  });
};
