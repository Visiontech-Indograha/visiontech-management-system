import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "../../lib/api";

export interface NamedLookup {
  id: string;
  name: string;
  description: string | null;
}

export interface MasterVehicle {
  id: string;
  name: string;
  license_plate: string;
  type: string | null;
  status: string;
}

export interface MasterItem {
  id: string;
  name: string;
  code: string;
  type: string | null;
  stock: number;
}

/** Factory hook generik untuk lookup bernama (Title, WorkCategory, ProductCategory, CategoryCE). */
function makeNamedLookupHooks(path: string, queryKey: string, label: string) {
  const useList = (q?: string) =>
    useQuery({
      queryKey: ["master", queryKey, q],
      queryFn: async () => {
        const { data } = await api.get<NamedLookup[]>(`/api/v1/master/${path}`, { params: { q } });
        return data;
      },
    });

  const useCreate = () => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: async (payload: { name: string; description?: string }) => {
        const { data } = await api.post<NamedLookup>(`/api/v1/master/${path}`, payload);
        return data;
      },
      onSuccess: () => {
        toast.success(`${label} berhasil ditambahkan`);
        queryClient.invalidateQueries({ queryKey: ["master", queryKey] });
      },
    });
  };

  const useUpdate = () => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: async ({ id, payload }: { id: string; payload: { name?: string; description?: string } }) => {
        const { data } = await api.put<NamedLookup>(`/api/v1/master/${path}/${id}`, payload);
        return data;
      },
      onSuccess: () => {
        toast.success(`${label} berhasil diperbarui`);
        queryClient.invalidateQueries({ queryKey: ["master", queryKey] });
      },
    });
  };

  const useDelete = () => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: async (id: string) => {
        await api.delete(`/api/v1/master/${path}/${id}`);
      },
      onSuccess: () => {
        toast.success(`${label} berhasil dihapus`);
        queryClient.invalidateQueries({ queryKey: ["master", queryKey] });
      },
    });
  };

  return { useList, useCreate, useUpdate, useDelete };
}

export const titleHooks = makeNamedLookupHooks("titles", "titles", "Jabatan");
export const workCategoryHooks = makeNamedLookupHooks("work-categories", "work-categories", "Kategori pekerjaan");
export const productCategoryHooks = makeNamedLookupHooks("product-categories", "product-categories", "Kategori produk");
export const ceCategoryHooks = makeNamedLookupHooks("ce-categories", "ce-categories", "Kategori pengalaman");

export const useTitles = titleHooks.useList;

// ==================== Vehicle ====================
export const useMasterVehicles = (params: { q?: string; status?: string } = {}) =>
  useQuery({
    queryKey: ["master", "vehicles", params],
    queryFn: async () => {
      const { data } = await api.get<MasterVehicle[]>("/api/v1/master/vehicles", { params });
      return data;
    },
  });

export const useCreateVehicle = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<MasterVehicle>) => {
      const { data } = await api.post<MasterVehicle>("/api/v1/master/vehicles", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Kendaraan berhasil ditambahkan");
      queryClient.invalidateQueries({ queryKey: ["master", "vehicles"] });
      queryClient.invalidateQueries({ queryKey: ["lookup", "vehicles"] });
    },
  });
};

export const useUpdateVehicle = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<MasterVehicle> }) => {
      const { data } = await api.put<MasterVehicle>(`/api/v1/master/vehicles/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Kendaraan berhasil diperbarui");
      queryClient.invalidateQueries({ queryKey: ["master", "vehicles"] });
      queryClient.invalidateQueries({ queryKey: ["lookup", "vehicles"] });
    },
  });
};

export const useDeleteVehicle = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/master/vehicles/${id}`);
    },
    onSuccess: () => {
      toast.success("Kendaraan berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["master", "vehicles"] });
      queryClient.invalidateQueries({ queryKey: ["lookup", "vehicles"] });
    },
  });
};

// ==================== Item ====================
export const useMasterItems = (params: { q?: string } = {}) =>
  useQuery({
    queryKey: ["master", "items", params],
    queryFn: async () => {
      const { data } = await api.get<MasterItem[]>("/api/v1/master/items", { params });
      return data;
    },
  });

export const useCreateItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<MasterItem>) => {
      const { data } = await api.post<MasterItem>("/api/v1/master/items", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Alat berhasil ditambahkan");
      queryClient.invalidateQueries({ queryKey: ["master", "items"] });
      queryClient.invalidateQueries({ queryKey: ["lookup", "items"] });
    },
  });
};

export const useUpdateItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<MasterItem> }) => {
      const { data } = await api.put<MasterItem>(`/api/v1/master/items/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Alat berhasil diperbarui");
      queryClient.invalidateQueries({ queryKey: ["master", "items"] });
      queryClient.invalidateQueries({ queryKey: ["lookup", "items"] });
    },
  });
};

export const useDeleteItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/master/items/${id}`);
    },
    onSuccess: () => {
      toast.success("Alat berhasil dihapus");
      queryClient.invalidateQueries({ queryKey: ["master", "items"] });
      queryClient.invalidateQueries({ queryKey: ["lookup", "items"] });
    },
  });
};
