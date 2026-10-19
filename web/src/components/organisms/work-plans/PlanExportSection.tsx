/**
 * web/src/components/organisms/work-plans/PlanExportSection.tsx
 * Bagian ekspor dokumen multi-format untuk Rencana Kerja (Weekly & Daily Plan).
 * Mendukung 4 format standar: PDF Resmi, Word (DOCX), Excel (XLSX), dan PowerPoint (PPTX).
 */

import React, { useState } from "react";
import { SectionTitle } from "@/components/molecules/SectionTitle";
import { TextBlock } from "@/components/molecules/TextBlock";
import { Button } from "@/components/atoms/Button";
import { UniversalMediaModal } from "@/components/organisms/media";
import {
  FileSpreadsheet,
  FileText,
  Presentation,
  Download,
  Eye,
} from "lucide-react";
import type { WorkPlan } from "@/services/workPlanService";

export interface PlanExportSectionProps {
  plan: WorkPlan;
  className?: string;
}

export const PlanExportSection: React.FC<PlanExportSectionProps> = ({
  plan,
  className = "",
}) => {
  const [selectedPreview, setSelectedPreview] = useState<{
    url: string;
    title: string;
  } | null>(null);

  const planId = plan.id;
  const planNumber = plan.number || "DRAFT-PLAN";

  const handleDownload = (format: "docx" | "xlsx" | "pptx") => {
    const downloadUrl = `/api/v1/work-plans/${planId}/export?format=${format}`;
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `${planNumber.replace(/\//g, "-")}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePreviewPdf = () => {
    setSelectedPreview({
      url: `/api/v1/work-plans/${planId}/pdf`,
      title: `Pratinjau PDF Rencana Kerja: ${planNumber}`,
    });
  };

  return (
    <section aria-label="Ekspor Dokumen" className={`mt-6 ${className}`}>
      <SectionTitle>Ekspor & Cetak Dokumen</SectionTitle>
      <div className="rounded-panel border border-line bg-surface shadow-card p-5">
        <div className="mb-4">
          <TextBlock className="font-medium text-ink">
            Pusat Pembangkitan Dokumen Operasional
          </TextBlock>
          <TextBlock className="text-xs text-mist">
            Unduh atau tinjau langsung Surat Perintah Kerja (SPK) dan Rencana Kerja resmi PT Visiontech Indograha
            dalam 4 format standar industri.
          </TextBlock>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* 1. PDF Preview & Print */}
          <div className="flex flex-col justify-between p-3.5 rounded-lg border border-line bg-surface-muted hover:border-rose-400 transition-colors">
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 rounded-md bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-ink">PDF Resmi</h4>
                <p className="text-[11px] text-mist leading-tight">
                  Pratinjau & cetak dokumen ber-Kop Surat resmi dengan QR Code.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="w-full text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/20 text-xs font-medium"
              onClick={handlePreviewPdf}
            >
              <Eye className="w-3.5 h-3.5 mr-1.5" />
              Pratinjau PDF
            </Button>
          </div>

          {/* 2. Word (DOCX) */}
          <div className="flex flex-col justify-between p-3.5 rounded-lg border border-line bg-surface-muted hover:border-blue-400 transition-colors">
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 rounded-md bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-ink">Word (DOCX)</h4>
                <p className="text-[11px] text-mist leading-tight">
                  Format naskah lengkap SPK untuk pengarsipan dan penyesuaian teks.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="w-full text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950/20 text-xs font-medium"
              onClick={() => handleDownload("docx")}
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Unduh DOCX
            </Button>
          </div>

          {/* 3. Excel (XLSX) */}
          <div className="flex flex-col justify-between p-3.5 rounded-lg border border-line bg-surface-muted hover:border-emerald-400 transition-colors">
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 rounded-md bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-ink">Excel (XLSX)</h4>
                <p className="text-[11px] text-mist leading-tight">
                  Matriks penugasan personel dan rekap volume pekerjaan harian.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="w-full text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/20 text-xs font-medium"
              onClick={() => handleDownload("xlsx")}
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Unduh XLSX
            </Button>
          </div>

          {/* 4. PowerPoint (PPTX) */}
          <div className="flex flex-col justify-between p-3.5 rounded-lg border border-line bg-surface-muted hover:border-orange-400 transition-colors">
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 rounded-md bg-orange-50 text-orange-600 dark:bg-orange-950/40 dark:text-orange-400">
                <Presentation className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-ink">PowerPoint (PPTX)</h4>
                <p className="text-[11px] text-mist leading-tight">
                  Slide presentasi otomatis untuk rapat koordinasi tim & klien.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="w-full text-orange-600 hover:text-orange-700 hover:bg-orange-50 dark:hover:bg-orange-950/20 text-xs font-medium"
              onClick={() => handleDownload("pptx")}
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Unduh PPTX
            </Button>
          </div>
        </div>
      </div>

      {selectedPreview && (
        <UniversalMediaModal
          isOpen={!!selectedPreview}
          onClose={() => setSelectedPreview(null)}
          filePath={selectedPreview.url}
          title={selectedPreview.title}
        />
      )}
    </section>
  );
};
