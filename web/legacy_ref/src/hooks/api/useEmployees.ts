import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "../../lib/api";
import {
  EmployeeResponse,
  IDCardResponse,
  BPJSResponse,
  DrivingCardResponse,
  CertificateEmpResponse,
} from "../../types/hr";

export interface EmployeeListParams {
  q?: string;
  is_active?: boolean;
  employment_status?: string;
  skip?: number;
  limit?: number;
}

export const useEmployees = (params: EmployeeListParams = {}) => {
  return useQuery({
    queryKey: ["employees", params],
    queryFn: async () => {
      const { data } = await api.get<EmployeeResponse[]>("/api/v1/employees/", { params });
      return data;
    },
    placeholderData: (prev) => prev,
  });
};

export const useEmployee = (id: string | undefined) => {
  return useQuery({
    queryKey: ["employees", "detail", id],
    queryFn: async () => {
      const { data } = await api.get<EmployeeResponse>(`/api/v1/employees/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

export const useCreateEmployee = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post<EmployeeResponse>("/api/v1/employees/", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Karyawan berhasil ditambahkan");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });
};

export const useUpdateEmployee = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.put<EmployeeResponse>(`/api/v1/employees/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Data karyawan berhasil diperbarui");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });
};

export const useDeleteEmployee = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/employees/${id}`);
    },
    onSuccess: () => {
      toast.success("Karyawan berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });
};

export const useCreateUserAccount = () => {
  return useMutation({
    mutationFn: async (payload: unknown) => {
      const { data } = await api.post("/api/v1/auth/register", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Akun login berhasil dibuat");
    },
  });
};

// ==================== SUB-DOKUMEN ====================

function invalidateEmployee(queryClient: ReturnType<typeof useQueryClient>, employeeId: string) {
  queryClient.invalidateQueries({ queryKey: ["employees", "detail", employeeId] });
  queryClient.invalidateQueries({ queryKey: ["employees"] });
}

// ---- ID Card (1:1) ----
export const useSaveIdCard = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ payload, exists }: { payload: Record<string, unknown>; exists: boolean }) => {
      const { data } = exists
        ? await api.put<IDCardResponse>(`/api/v1/employees/${employeeId}/id-card`, payload)
        : await api.post<IDCardResponse>(`/api/v1/employees/${employeeId}/id-card`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("KTP berhasil disimpan");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};

export const useDeleteIdCard = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.delete(`/api/v1/employees/${employeeId}/id-card`);
    },
    onSuccess: () => {
      toast.success("KTP berhasil dihapus");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};

// ---- BPJS (1:1) ----
export const useSaveBpjs = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ payload, exists }: { payload: Record<string, unknown>; exists: boolean }) => {
      const { data } = exists
        ? await api.put<BPJSResponse>(`/api/v1/employees/${employeeId}/bpjs`, payload)
        : await api.post<BPJSResponse>(`/api/v1/employees/${employeeId}/bpjs`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("BPJS berhasil disimpan");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};

export const useDeleteBpjs = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.delete(`/api/v1/employees/${employeeId}/bpjs`);
    },
    onSuccess: () => {
      toast.success("BPJS berhasil dihapus");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};

// ---- Driving Card (1:banyak) ----
export const useAddDrivingCard = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post<DrivingCardResponse>(`/api/v1/employees/${employeeId}/driving-card`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("SIM/SIO berhasil ditambahkan");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};

export const useUpdateDrivingCard = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ cardId, payload }: { cardId: string; payload: Record<string, unknown> }) => {
      const { data } = await api.put<DrivingCardResponse>(
        `/api/v1/employees/${employeeId}/driving-card/${cardId}`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      toast.success("SIM/SIO berhasil diperbarui");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};

export const useDeleteDrivingCard = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (cardId: string) => {
      await api.delete(`/api/v1/employees/${employeeId}/driving-card/${cardId}`);
    },
    onSuccess: () => {
      toast.success("SIM/SIO berhasil dihapus");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};

// ---- Certificate (1:banyak) ----
export const useAddCertificate = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post<CertificateEmpResponse>(`/api/v1/employees/${employeeId}/certificate`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Sertifikat berhasil ditambahkan");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};

export const useUpdateCertificate = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ cardId, payload }: { cardId: string; payload: Record<string, unknown> }) => {
      const { data } = await api.put<CertificateEmpResponse>(
        `/api/v1/employees/${employeeId}/certificate/${cardId}`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      toast.success("Sertifikat berhasil diperbarui");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};

export const useDeleteCertificate = (employeeId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (cardId: string) => {
      await api.delete(`/api/v1/employees/${employeeId}/certificate/${cardId}`);
    },
    onSuccess: () => {
      toast.success("Sertifikat berhasil dihapus");
      invalidateEmployee(queryClient, employeeId);
    },
  });
};
