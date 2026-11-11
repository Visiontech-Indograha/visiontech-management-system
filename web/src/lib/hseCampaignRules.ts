import { htmlToText } from "@/lib/htmlToText";

/** Batas judul kampanye sama dengan API (HseCampaignBase.title max_length=255). */
export const HSE_TITLE_MAX = 255;

/** Alasan tombol Terbitkan belum bisa dipakai; null bila siap. */
export function campaignPublishBlocker(title: string, content: string): string | null {
  const missing: string[] = [];
  if (!title.trim()) missing.push("judul");
  if (!htmlToText(content).trim()) missing.push("isi");
  if (missing.length === 0) return null;
  return `Isi ${missing.join(" dan ")} kampanye dulu agar bisa diterbitkan.`;
}
