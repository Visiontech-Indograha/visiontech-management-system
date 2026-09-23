import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "../../lib/api";
import { VehicleBookingLogResponse, LogbookToolResponse, VehicleServiceResponse } from "../../types/logbook";

export const useVehicleBookings = () => {
  return useQuery({
    queryKey: ["logbook", "vehicles"],
    queryFn: async () => {
      const { data } = await api.get<VehicleBookingLogResponse[]>("/api/v1/logbook/vehicles/book");
      return data;
    },
  });
};

export const useToolBorrows = () => {
  return useQuery({
    queryKey: ["logbook", "tools"],
    queryFn: async () => {
      const { data } = await api.get<LogbookToolResponse[]>("/api/v1/logbook/tools/borrow");
      return data;
    },
  });
};

export const useCreateVehicleBooking = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: unknown) => {
      const { data } = await api.post("/api/v1/logbook/vehicles/book", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Peminjaman kendaraan berhasil dicatat");
      queryClient.invalidateQueries({ queryKey: ["logbook", "vehicles"] });
    },
  });
};

export const useApproveVehicleBooking = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: "APPROVED" | "REJECTED" }) => {
      const { data } = await api.put(`/api/v1/logbook/vehicles/book/${id}/approve`, null, { params: { status_in: status } });
      return data;
    },
    onSuccess: (_data, vars) => {
      toast.success(vars.status === "APPROVED" ? "Booking disetujui" : "Booking ditolak");
      queryClient.invalidateQueries({ queryKey: ["logbook", "vehicles"] });
    },
  });
};

export const useDeleteVehicleBooking = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/logbook/vehicles/book/${id}`);
    },
    onSuccess: () => {
      toast.success("Booking berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["logbook", "vehicles"] });
    },
  });
};

export const useCreateToolBorrow = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: unknown) => {
      const { data } = await api.post("/api/v1/logbook/tools/borrow", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Peminjaman alat kerja berhasil dicatat");
      queryClient.invalidateQueries({ queryKey: ["logbook", "tools"] });
    },
  });
};

export const useApproveToolBorrow = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: "APPROVED" | "REJECTED" }) => {
      const { data } = await api.put(`/api/v1/logbook/tools/borrow/${id}/approve`, null, { params: { status_in: status } });
      return data;
    },
    onSuccess: (_data, vars) => {
      toast.success(vars.status === "APPROVED" ? "Peminjaman disetujui" : "Peminjaman ditolak");
      queryClient.invalidateQueries({ queryKey: ["logbook", "tools"] });
    },
  });
};

export const useDeleteToolBorrow = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/logbook/tools/borrow/${id}`);
    },
    onSuccess: () => {
      toast.success("Peminjaman berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["logbook", "tools"] });
    },
  });
};

export const useVehicleServices = () => {
  return useQuery({
    queryKey: ["logbook", "services"],
    queryFn: async () => {
      const { data } = await api.get<VehicleServiceResponse[]>("/api/v1/logbook/vehicles/service");
      return data;
    },
  });
};

export const useCreateVehicleService = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: unknown) => {
      const { data } = await api.post("/api/v1/logbook/vehicles/service", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Servis kendaraan berhasil dicatat");
      queryClient.invalidateQueries({ queryKey: ["logbook", "services"] });
    },
  });
};

export const useUpdateVehicleService = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Record<string, unknown> }) => {
      const { data } = await api.put(`/api/v1/logbook/vehicles/service/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Servis kendaraan berhasil diperbarui");
      queryClient.invalidateQueries({ queryKey: ["logbook", "services"] });
    },
  });
};

export const useDeleteVehicleService = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/logbook/vehicles/service/${id}`);
    },
    onSuccess: () => {
      toast.success("Servis kendaraan berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["logbook", "services"] });
    },
  });
};
