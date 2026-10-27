import { InlineLink } from "@/components/molecules/Links";

export function WorkCompletionNavTabs({
  activeTab,
}: {
  activeTab: "completions" | "projects" | "clients";
}) {
  return (
    <div className="flex items-center gap-2 mb-4 border-b border-line pb-2 flex-wrap">
      <InlineLink
        to="/work-completions"
        className={`px-3 py-1.5 rounded-control text-xs font-medium transition-colors ${
          activeTab === "completions"
            ? "bg-primary text-white font-semibold"
            : "bg-hover text-foreground hover:bg-hover/80"
        }`}
      >
        Pekerjaan Klien & BAST
      </InlineLink>
      <InlineLink
        to="/projects"
        className={`px-3 py-1.5 rounded-control text-xs font-medium transition-colors ${
          activeTab === "projects"
            ? "bg-primary text-white font-semibold"
            : "bg-hover text-foreground hover:bg-hover/80"
        }`}
      >
        Master Proyek (SPK)
      </InlineLink>
      <InlineLink
        to="/clients"
        className={`px-3 py-1.5 rounded-control text-xs font-medium transition-colors ${
          activeTab === "clients"
            ? "bg-primary text-white font-semibold"
            : "bg-hover text-foreground hover:bg-hover/80"
        }`}
      >
        Master Klien
      </InlineLink>
    </div>
  );
}
