import { useRef, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { ApiError } from "@/lib/apiClient";
import { Skeleton } from "@/components/atoms/Skeleton";
import { Button } from "@/components/atoms/Button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/atoms/Dialog";
import { Loader2 } from "@/components/atoms/Icon";
import { Image } from "@/components/atoms/Image";
import { PlainButton } from "@/components/atoms/PlainButton";
import { Text } from "@/components/atoms/Text";
import { fetchFileUrl } from "@/services/fileService";

export function FilePreview({ fileId, fileName = "Berkas" }: { fileId: string; fileName?: string }) {
  const [retryCount, setRetryCount] = useState(0);
  const downloadWindow = useRef<Window | null>(null);

  const fetchUrlData = (variant: string) => fetchFileUrl(fileId, variant);

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
      if (downloadWindow.current) {
        downloadWindow.current.location.replace(new URL(data.url, window.location.origin).toString());
        downloadWindow.current = null;
      } else {
        window.location.assign(data.url);
      }
    },
    onError: () => {
      downloadWindow.current?.close();
      downloadWindow.current = null;
    },
  });

  if (thumbQuery.isLoading) {
    return <Skeleton className="h-9 w-24" data-testid="file-preview-skeleton" />;
  }

  if (thumbQuery.isError) {
    if (thumbQuery.error instanceof ApiError && thumbQuery.error.status === 404) {
      return <Text as="span" className="text-sm text-muted-foreground">Berkas tidak tersedia</Text>;
    }
    return (
      <div className="flex items-center gap-2">
        <Text as="span" className="text-sm text-destructive">Gagal memuat</Text>
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
      <PlainButton
        onClick={() => {
          downloadWindow.current = window.open("about:blank", "_blank");
          downloadMutation.mutate();
        }}
        className="flex items-center gap-2 text-sm font-medium text-lens hover:underline focus-visible:outline-none"
        disabled={downloadMutation.isPending}
      >
        Unduh {fileName}
        {downloadMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
      </PlainButton>
    );
  }

  return (
    <Dialog onOpenChange={(open) => { if (open) viewQuery.refetch(); }}>
      <DialogTrigger asChild>
        <PlainButton
          className="overflow-hidden rounded-md border border-line bg-surface hover:ring-2 hover:ring-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <Image
            src={data.url}
            alt={fileName}
            className="h-12 w-20 object-cover"
            onError={() => {
              if (retryCount === 0) setRetryCount((c) => c + 1);
            }}
          />
        </PlainButton>
      </DialogTrigger>
      <DialogContent className="w-[94vw] sm:max-w-5xl border-none bg-transparent p-0 shadow-none">
        {viewQuery.isLoading || viewQuery.isFetching ? (
          <Skeleton className="h-[60vh] w-full rounded-md bg-surface/20" />
        ) : viewQuery.isError ? (
          <div className="flex h-[60vh] flex-col items-center justify-center gap-4 rounded-md bg-surface p-4 text-center">
            <Text className="text-destructive">Gagal memuat gambar resolusi tinggi</Text>
            <Button onClick={() => viewQuery.refetch()}>Coba lagi</Button>
          </div>
        ) : viewQuery.data ? (
          <Image
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
