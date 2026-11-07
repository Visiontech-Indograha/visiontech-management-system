import { useState, useMemo } from "react";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import {
  Briefcase,
  AlertCircle,
  MapPin,
  Calendar,
  CheckCircle2,
  FileCheck2,
  Users,
  Eye,
  Download,
} from "@/components/molecules/Glyphs";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TextField, SelectField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { downloadWorkOrderExport, type WorkOrder, type WorkOrderStatus } from "@/services/workOrderService";

type TabKey = "intake" | "survey_review" | "execution" | "completed";

interface WorkOrderListProps {
  workOrders: WorkOrder[];
  isLoading: boolean;
  isError?: boolean;
  onRetry?: () => void;
  divisions: Array<{ id: string; name: string }>;
  selectedDivisionId: string;
  onDivisionChange: (id: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onAssignSurvey: (wo: WorkOrder) => void;
  onReviewSurvey: (woId: string) => void;
  onSignBast: (wo: WorkOrder) => void;
}

export function WorkOrderList({
  workOrders,
  isLoading,
  isError = false,
  onRetry,
  divisions,
  selectedDivisionId,
  onDivisionChange,
  searchQuery,
  onSearchChange,
  onAssignSurvey,
  onReviewSurvey,
  onSignBast,
}: WorkOrderListProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("intake");

  const categorized = useMemo(() => {
    const intake: WorkOrder[] = [];
    const surveyReview: WorkOrder[] = [];
    const execution: WorkOrder[] = [];
    const completed: WorkOrder[] = [];

    workOrders.forEach((wo) => {
      switch (wo.status) {
        case "WAITING_SURVEY":
        case "SURVEY_IN_PROGRESS":
          intake.push(wo);
          break;
        case "SURVEY_SUBMITTED":
          surveyReview.push(wo);
          break;
        case "READY_TO_EXECUTE":
        case "IN_PROGRESS":
          execution.push(wo);
          break;
        case "COMPLETED":
        case "BAST_SIGNED":
        case "CANCELLED":
          completed.push(wo);
          break;
        default:
          intake.push(wo);
      }
    });

    return { intake, surveyReview, execution, completed };
  }, [workOrders]);

  const currentList = useMemo(() => {
    switch (activeTab) {
      case "intake":
        return categorized.intake;
      case "survey_review":
        return categorized.surveyReview;
      case "execution":
        return categorized.execution;
      case "completed":
        return categorized.completed;
    }
  }, [activeTab, categorized]);

  const renderStatusBadge = (status: WorkOrderStatus) => {
    switch (status) {
      case "WAITING_SURVEY":
        return (
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-info-bg text-info border border-info-border">
            <TextBlock as="span">Butuh Survei</TextBlock>
          </div>
        );
      case "SURVEY_IN_PROGRESS":
        return (
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-info-bg text-info border border-info-border">
            <TextBlock as="span">Survei Berjalan</TextBlock>
          </div>
        );
      case "SURVEY_SUBMITTED":
        return (
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-warning-bg text-warning border border-warning-border animate-pulse">
            <TextBlock as="span">Menunggu pengecekan</TextBlock>
          </div>
        );
      case "READY_TO_EXECUTE":
        return (
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-success-bg text-success border border-success-border">
            <TextBlock as="span">Siap dikerjakan</TextBlock>
          </div>
        );
      case "IN_PROGRESS":
        return (
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-info-bg text-info border border-info-border">
            <TextBlock as="span">Sedang Dikerjakan</TextBlock>
          </div>
        );
      case "COMPLETED":
        return (
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-success-bg text-success border border-success-border">
            <TextBlock as="span">Selesai (siap surat serah terima)</TextBlock>
          </div>
        );
      case "BAST_SIGNED":
        return (
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-success-bg text-success border border-success-border">
            <TextBlock as="span">Surat serah terima terbit</TextBlock>
          </div>
        );
      case "CANCELLED":
        return (
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground border border-border">
            <TextBlock as="span">Dibatalkan</TextBlock>
          </div>
        );
      default:
        return (
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground">
            <TextBlock as="span">{status}</TextBlock>
          </div>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <TextField
            label=""
            placeholder="Cari awal nomor WO, nama klien, lokasi, atau judul tugas..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <SelectField
            label=""
            value={selectedDivisionId}
            onChange={(e) => onDivisionChange(e.target.value)}
            className="w-full sm:w-56"
          >
            <ControlOption value="">Semua Divisi</ControlOption>
            {divisions.map((d) => (
              <ControlOption key={d.id} value={d.id}>
                {d.name}
              </ControlOption>
            ))}
          </SelectField>
        </div>
      </div>

      {/* 4 Pipeline Tabs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 border-b border-border pb-px">
        <ActionButton
          type="button"
          variant="ghost"
          onClick={() => setActiveTab("intake")}
          className={`flex items-center justify-between p-3 rounded-t-lg border-b-2 text-sm font-medium transition-colors h-auto ${
            activeTab === "intake"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-ink hover:bg-muted/30"
          }`}
        >
          <TextBlock as="span">1. Tugas Masuk dan Survei</TextBlock>
          <div className="ml-2 px-2 py-0.5 text-xs rounded-full bg-muted font-bold">
            <TextBlock as="span">{categorized.intake.length}</TextBlock>
          </div>
        </ActionButton>

        <ActionButton
          type="button"
          variant="ghost"
          onClick={() => setActiveTab("survey_review")}
          className={`flex items-center justify-between p-3 rounded-t-lg border-b-2 text-sm font-medium transition-colors h-auto ${
            activeTab === "survey_review"
              ? "border-warning text-warning bg-warning-bg"
              : "border-transparent text-muted-foreground hover:text-ink hover:bg-muted/30"
          }`}
        >
          <div className="flex items-center gap-1.5">
            <TextBlock as="span">2. Cek hasil survei</TextBlock>
            {categorized.surveyReview.length > 0 && (
              <div className="h-2 w-2 rounded-full bg-warning animate-ping" />
            )}
          </div>
          <div
            className={`ml-2 px-2 py-0.5 text-xs rounded-full font-bold ${
              categorized.surveyReview.length > 0
                ? "bg-warning text-white shadow-sm"
                : "bg-muted text-muted-foreground"
            }`}
          >
            <TextBlock as="span">{categorized.surveyReview.length}</TextBlock>
          </div>
        </ActionButton>

        <ActionButton
          type="button"
          variant="ghost"
          onClick={() => setActiveTab("execution")}
          className={`flex items-center justify-between p-3 rounded-t-lg border-b-2 text-sm font-medium transition-colors h-auto ${
            activeTab === "execution"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-ink hover:bg-muted/30"
          }`}
        >
          <TextBlock as="span">3. Siap / Sedang Dikerjakan</TextBlock>
          <div className="ml-2 px-2 py-0.5 text-xs rounded-full bg-muted font-bold">
            <TextBlock as="span">{categorized.execution.length}</TextBlock>
          </div>
        </ActionButton>

        <ActionButton
          type="button"
          variant="ghost"
          onClick={() => setActiveTab("completed")}
          className={`flex items-center justify-between p-3 rounded-t-lg border-b-2 text-sm font-medium transition-colors h-auto ${
            activeTab === "completed"
              ? "border-success text-success bg-success-bg"
              : "border-transparent text-muted-foreground hover:text-ink hover:bg-muted/30"
          }`}
        >
          <TextBlock as="span">4. Selesai dan serah terima</TextBlock>
          <div className="ml-2 px-2 py-0.5 text-xs rounded-full bg-muted font-bold">
            <TextBlock as="span">{categorized.completed.length}</TextBlock>
          </div>
        </ActionButton>
      </div>

      {/* Content List */}
      {isError ? (
        <div className="py-12 text-center border border-dashed rounded-xl border-danger-border bg-danger-bg/20">
          <AlertCircle className="h-10 w-10 text-danger mx-auto mb-2" />
          <TextBlock className="font-semibold text-danger text-base">Daftar tugas klien belum bisa dimuat</TextBlock>
          <div className="text-xs text-muted-foreground mt-1 mb-3"><TextBlock as="span">Terjadi gangguan koneksi ke server.</TextBlock></div>
          {onRetry && (
            <ActionButton type="button" variant="outline" size="sm" onClick={onRetry}>
              Coba Lagi
            </ActionButton>
          )}
        </div>
      ) : isLoading ? (
        <div className="grid gap-3 py-6 md:grid-cols-2" role="status" aria-live="polite">
          <TextBlock className="sr-only">Sedang memuat daftar tugas klien</TextBlock>
          <LoadingBar className="h-28" />
          <LoadingBar className="h-28" />
          <LoadingBar className="h-28" />
        </div>
      ) : currentList.length === 0 ? (
        <div className="py-16 text-center border border-dashed rounded-xl border-border bg-card/30">
          <Briefcase className="h-10 w-10 text-muted-foreground mx-auto mb-3 opacity-40" />
          <TextBlock className="font-semibold text-ink text-base">Tidak ada tugas pada tahap ini</TextBlock>
          <div className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            <TextBlock as="span">
              {activeTab === "intake" && "Semua permintaan tugas klien telah memiliki jadwal survei atau sudah diproses."}
              {activeTab === "survey_review" && "Belum ada survei yang menunggu review dari Project Manager."}
              {activeTab === "execution" && "Belum ada tugas yang siap atau sedang dikerjakan tim teknisi."}
              {activeTab === "completed" && "Belum ada tugas yang selesai atau surat serah terimanya terbit."}
            </TextBlock>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {currentList.map((wo) => {
            const hasItems = wo.total_items > 0;
            const progressPercent = hasItems
              ? Math.round((wo.completed_items / wo.total_items) * 100)
              : 0;

            return (
              <div
                key={wo.work_order_id}
                className="bg-card rounded-xl border border-border p-4 flex flex-col justify-between hover:shadow-md transition-shadow group"
              >
                <div className="space-y-3">
                  {/* Card Header */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-mono text-xs font-bold text-primary px-2 py-0.5 rounded bg-primary/10">
                      <TextBlock as="span">{wo.wo_number}</TextBlock>
                    </div>
                    {renderStatusBadge(wo.status)}
                  </div>

                  {/* Title & Client */}
                  <div>
                    <TextBlock className="font-semibold text-ink text-base line-clamp-2 group-hover:text-primary transition-colors">
                      {wo.title}
                    </TextBlock>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-1">
                      <MapPin className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <div className="truncate">
                        <TextBlock as="span" className="text-ink font-semibold">{wo.client_name}</TextBlock>
                        <TextBlock as="span">{wo.site_name ? ` • ${wo.site_name}` : ""}</TextBlock>
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar (if items exist or in execution) */}
                  {hasItems && (
                    <div className="space-y-1 bg-surface-elevated/40 p-2 rounded-lg border border-border/50">
                      <div className="flex items-center justify-between text-xs">
                        <TextBlock className="text-muted-foreground">Progres Tugas:</TextBlock>
                        <TextBlock className="font-semibold text-ink">
                          {wo.completed_items} / {wo.total_items} Item ({progressPercent}%)
                        </TextBlock>
                      </div>
                      <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${
                            progressPercent === 100 ? "bg-emerald-500" : "bg-primary"
                          }`}
                          style={{ width: `${progressPercent}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Team & PM Info */}
                  <div className="text-xs text-muted-foreground space-y-1 pt-1 border-t border-border/50">
                    <div className="flex items-center justify-between">
                      <TextBlock as="span">Divisi:</TextBlock>
                      <TextBlock as="span" className="font-medium text-ink">{wo.division_name || "-"}</TextBlock>
                    </div>
                    <div className="flex items-center justify-between">
                      <TextBlock as="span">PM Bertanggung Jawab:</TextBlock>
                      <TextBlock as="span" className="font-medium text-ink">{wo.pm_name || "-"}</TextBlock>
                    </div>
                    {wo.team_name && (
                      <div className="flex items-center justify-between">
                        <TextBlock as="span">Tim Lapangan:</TextBlock>
                        <div className="font-medium text-ink flex items-center gap-1">
                          <Users className="h-3 w-3 text-primary" />
                          <TextBlock as="span">{wo.team_name}</TextBlock>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Card Actions Footer */}
                <div className="pt-4 mt-3 border-t border-border flex items-center justify-between gap-2">
                  <ActionButton
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => onReviewSurvey(wo.work_order_id)}
                    className="text-xs font-medium text-muted-foreground hover:text-ink flex items-center gap-1 py-1 px-2 rounded h-auto"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    <TextBlock as="span">Rincian</TextBlock>
                  </ActionButton>

                  {/* Contextual Action Button based on state */}
                  {wo.status === "WAITING_SURVEY" && (
                    <ActionButton
                      type="button"
                      variant="default"
                      size="sm"
                      onClick={() => onAssignSurvey(wo)}
                      className="text-xs py-1"
                    >
                      <Calendar className="h-3.5 w-3.5 mr-1" />
                      <TextBlock as="span">Tugaskan Survei</TextBlock>
                    </ActionButton>
                  )}

                  {wo.status === "SURVEY_SUBMITTED" && (
                    <ActionButton
                      type="button"
                      variant="default"
                      size="sm"
                      onClick={() => onReviewSurvey(wo.work_order_id)}
                      className="text-xs py-1 bg-warning text-white hover:bg-warning/90"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                      <TextBlock as="span">Cek hasil survei</TextBlock>
                    </ActionButton>
                  )}

                  {wo.status === "COMPLETED" && (
                    <ActionButton
                      type="button"
                      variant="default"
                      size="sm"
                      onClick={() => onSignBast(wo)}
                      className="text-xs py-1 bg-success text-white hover:bg-success/90"
                    >
                      <FileCheck2 className="h-3.5 w-3.5 mr-1" />
                      <TextBlock as="span">Tandatangani serah terima</TextBlock>
                    </ActionButton>
                  )}

                  {wo.status === "BAST_SIGNED" && (
                    <ActionButton
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => downloadWorkOrderExport(wo.work_order_id, "pdf", `BAST_${wo.wo_number}.pdf`)}
                      className="text-xs py-1 text-emerald-600 border-emerald-500/30 hover:bg-emerald-500/10 flex items-center gap-1.5"
                    >
                      <Download className="h-3.5 w-3.5" />
                      <TextBlock as="span">Unduh surat serah terima (.pdf)</TextBlock>
                    </ActionButton>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
