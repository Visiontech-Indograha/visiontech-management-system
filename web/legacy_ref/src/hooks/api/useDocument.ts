import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../../lib/api";
import {
  InternalDocument,
  InternalDocumentCreate,
  OutpostLetter,
  OutpostLetterCreate,
} from "../../types/document";

export function useInternalDocuments() {
  return useQuery({
    queryKey: ["internal_documents"],
    queryFn: async () => {
      const res = await api.get<InternalDocument[]>("/api/v1/documents/internal");
      return res.data;
    },
  });
}

export function useInternalDocument(id: string | undefined) {
  return useQuery({
    queryKey: ["internal_documents", id],
    queryFn: async () => {
      const res = await api.get<InternalDocument>(`/api/v1/documents/internal/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateInternalDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: InternalDocumentCreate) => {
      const res = await api.post<InternalDocument>("/api/v1/documents/internal", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["internal_documents"] });
    },
  });
}

export function useUpdateInternalDocument(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<InternalDocumentCreate>) => {
      const res = await api.put<InternalDocument>(`/api/v1/documents/internal/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["internal_documents"] });
    },
  });
}

export function useDeleteInternalDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/documents/internal/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["internal_documents"] });
    },
  });
}

export function useOutpostLetters() {
  return useQuery({
    queryKey: ["outpost_letters"],
    queryFn: async () => {
      const res = await api.get<OutpostLetter[]>("/api/v1/documents/outpost");
      return res.data;
    },
  });
}

export function useOutpostLetter(id: string | undefined) {
  return useQuery({
    queryKey: ["outpost_letters", id],
    queryFn: async () => {
      const res = await api.get<OutpostLetter>(`/api/v1/documents/outpost/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateOutpostLetter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: OutpostLetterCreate) => {
      const res = await api.post<OutpostLetter>("/api/v1/documents/outpost", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outpost_letters"] });
    },
  });
}

export function useUpdateOutpostLetter(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<OutpostLetterCreate>) => {
      const res = await api.put<OutpostLetter>(`/api/v1/documents/outpost/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outpost_letters"] });
    },
  });
}

export function useDeleteOutpostLetter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/documents/outpost/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outpost_letters"] });
    },
  });
}
