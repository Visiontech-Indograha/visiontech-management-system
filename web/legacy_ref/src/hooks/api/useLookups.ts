import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api";

export interface Vehicle {
  id: string;
  name: string;
  license_plate: string;
  type: string | null;
  status: string;
}

export interface Item {
  id: string;
  name: string;
  code: string;
  type: string | null;
  stock: number;
}

export interface Employee {
  id: string;
  full_name: string;
}

export const useVehicles = () => {
  return useQuery({
    queryKey: ["lookup", "vehicles"],
    queryFn: async () => {
      const { data } = await api.get<Vehicle[]>("/api/v1/lookup/vehicles");
      return data;
    },
  });
};

export const useItems = () => {
  return useQuery({
    queryKey: ["lookup", "items"],
    queryFn: async () => {
      const { data } = await api.get<Item[]>("/api/v1/lookup/items");
      return data;
    },
  });
};

export const useEmployees = () => {
  return useQuery({
    queryKey: ["lookup", "employees"],
    queryFn: async () => {
      const { data } = await api.get<Employee[]>("/api/v1/employees/");
      return data;
    },
  });
};
