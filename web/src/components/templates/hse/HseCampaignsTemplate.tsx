import { HseCampaignsPanel } from "@/components/organisms/hse/HseCampaignsPanel";
import { PageTemplate } from "@/components/templates/PageTemplate";

export function HseCampaignsTemplate() {
  return (
    <HseCampaignsPanel
      renderPage={({ action, body }) => (
        <PageTemplate
          title="Keselamatan Kerja (HSE / K3)"
          description="Kelola pengumuman keselamatan kerja, kampanye wajib baca, audit pembaca, dan inspeksi armada lapangan."
          action={action}
        >
          {body}
        </PageTemplate>
      )}
    />
  );
}
