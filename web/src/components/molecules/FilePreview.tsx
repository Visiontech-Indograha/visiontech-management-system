import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { Skeleton } from "@/components/atoms/Skeleton";
import { Button } from "@/components/atoms/Button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/atoms/Dialog";
import { Loader2 } from "lucide-react";

interface FileUrlResponse {
  url: string;
  mime_type: string;
}

export function FilePreview({ fileId, fileName = "Berkas" }: { fileId: string; fileName?: string }) {
  const [retryCount, setRetryCount] = useState(0);

  const fetchUrlData = async (variant: string) => {
    const res = await api.get<FileUrlResponse>(`/files/${fileId}/url?variant=${variant}`);
    return res.data;
  };

  const thumbQuery = useQuery({
    queryKey: ["file-url", fileId, "thumb", retryCount],
    queryFn: () => fetchUrlData("thumb"),
    staleTime: 4 * 60 * 1000, // 4 menit
    retry: false,
  });

  const viewQuery = useQuery({
    queryKey: ["file-url", fileId, "view", retryCount],
    queryFn: () => fetchUrlData("view"),
    staleTime: 4 * 60 * 1000,
    enabled: false,
  });

  const downloadMutation = useMutation({
    mutationFn: () => fetchUrlData("full"),
    onSuccess: (data) => {
      window.open(data.url, "_blank");
    },
  });

  if (thumbQuery.isLoading) {
    return <Skeleton className="h-9 w-24" data-testid="file-preview-skeleton" />;
  }

  if (thumbQuery.isError) {
    if (thumbQuery.error instanceof ApiError && thumbQuery.error.status === 404) {
      return <span className="text-sm text-muted-foreground">Berkas tidak tersedia</span>;
    }
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-destructive">Gagal memuat</span>
        <Button variant="outline" size="sm" onClick={() => thumbQuery.refetch()}>
          Coba lagi
        </Button>
      </div>
    );
  }

  const data = thumbQuery.data;
  if (!data) return null;

  const isImage = data.mime_type.startsWith("image/");

  if (!isImage) {
    return (
      <button 
        type="button" 
        onClick={() => downloadMutation.mutate()} 
        className="flex items-center gap-2 text-sm font-medium text-lens hover:underline focus-visible:outline-none"
        disabled={downloadMutation.isPending}
      >
        Unduh {fileName}
        {downloadMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
      </button>
    );
  }

  return (
    <Dialog onOpenChange={(open) => { if (open) viewQuery.refetch(); }}>
      <DialogTrigger asChild>
        <button
          type="button"
          className="overflow-hidden rounded-md border border-line bg-surface hover:ring-2 hover:ring-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <img
            src={data.url}
            alt={fileName}
            className="h-12 w-20 object-cover"
            onError={() => {
              if (retryCount === 0) setRetryCount((c) => c + 1);
            }}
          />
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl border-none bg-transparent p-0 shadow-none">
        {viewQuery.isLoading || viewQuery.isFetching ? (
          <Skeleton className="h-[60vh] w-full rounded-md bg-surface/20" />
        ) : viewQuery.isError ? (
          <div className="flex h-[60vh] flex-col items-center justify-center gap-4 rounded-md bg-surface p-4 text-center">
            <p className="text-destructive">Gagal memuat gambar resolusi tinggi</p>
            <Button onClick={() => viewQuery.refetch()}>Coba lagi</Button>
          </div>
        ) : viewQuery.data ? (
          <img
            src={viewQuery.data.url}
            alt={fileName}
            className="max-h-[85vh] w-full rounded-md object-contain"
            onError={() => {
              if (retryCount === 0) setRetryCount((c) => c + 1);
            }}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
