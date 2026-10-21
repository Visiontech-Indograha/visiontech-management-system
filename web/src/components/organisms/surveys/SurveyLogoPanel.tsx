import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { DisclosureBlock, DisclosureTitle } from "@/components/molecules/DisclosureBlock";
import { StyledInput } from "@/components/molecules/InputControls";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { fetchSurveyLogo, useSetSurveyLogo, useSurveyLogos, type SurveyLogo } from "@/services/surveyService";

function LogoRow({ logo }: { logo: SurveyLogo }) {
  const set = useSetSurveyLogo();
  const img = useQuery({
    queryKey: ["survey-logos", "image", logo.role, logo.custom],
    enabled: logo.custom,
    queryFn: () => fetchSurveyLogo(logo.role),
  });
  const url = useMemo(() => (img.data ? URL.createObjectURL(img.data) : null), [img.data]);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  const run = (file: File | null) =>
    set.mutate({ role: logo.role, file }, {
      onSuccess: () => toast.success(file ? "Logo diganti." : "Kembali ke logo bawaan."),
      onError: (e) => toast.error(errorMessage(e)),
    });
  const [w, h] = logo.recommended_px;
  return (
    <div className="flex flex-wrap items-center gap-4 border-b border-line py-3 last:border-0">
      <div className="flex h-16 w-48 items-center justify-center rounded-control border border-dashed border-line bg-white p-1">
        {url ? <ImageView src={url} alt={logo.label} className="max-h-full max-w-full object-contain" />
          : <TextBlock className="text-xs text-mist">Logo bawaan template</TextBlock>}
      </div>
      <div className="min-w-0 flex-1">
        <TextBlock className="text-sm font-medium">{logo.label}</TextBlock>
        <TextBlock className="text-xs text-mist">
          {`Ukuran baku ${logo.width_cm} × ${logo.height_cm} cm · disarankan PNG transparan ${w} × ${h} px (300 dpi). `}
          Gambar dengan rasio lain dipasang utuh di tengah kotak, tidak ditarik.
        </TextBlock>
      </div>
      <StyledInput type="file" accept="image/png,image/jpeg,image/webp" className="w-56" disabled={set.isPending}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) run(f); e.target.value = ""; }} />
      {logo.custom && (
        <ActionButton size="sm" variant="outline" disabled={set.isPending} onClick={() => run(null)}>
          Pakai bawaan
        </ActionButton>
      )}
    </div>
  );
}

/** Logo kop laporan survei (Visiontech & klien) yang bisa diganti; ukuran baku = ukuran di template. */
export function SurveyLogoPanel() {
  const logos = useSurveyLogos();
  return (
    <DisclosureBlock className="rounded-panel border border-line p-3">
      <DisclosureTitle className="cursor-pointer text-sm font-medium">Logo kop laporan survei</DisclosureTitle>
      {logos.isError && <TextBlock className="text-sm text-danger">{errorMessage(logos.error)}</TextBlock>}
      {(logos.data ?? []).map((l) => <LogoRow key={l.role} logo={l} />)}
    </DisclosureBlock>
  );
}
