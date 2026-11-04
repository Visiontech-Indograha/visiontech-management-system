import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type Schemas = components["schemas"];
type CampaignDto = Schemas["HseCampaignResponse"];
type ActiveCampaignDto = Pick<
  CampaignDto,
  | "campaign_id"
  | "title"
  | "summary"
  | "content_html"
  | "media_path"
  | "media_paths"
  | "media_captions"
  | "target_audience"
  | "is_mandatory"
  | "cooldown_seconds"
  | "start_date"
  | "end_date"
  | "create_at"
>;

export interface HseCampaign {
  id: string;
  title: string;
  content_body: string;
  target_audience: string;
  /** Foto carousel: id berkas (file_object) berurutan. Kosong untuk kampanye tanpa foto. */
  media_ids: string[];
  /** Keterangan teks per foto (sejajar media_ids); kosong bila tidak ada. */
  media_captions: string[];
  /** Gambar tunggal lama (URL), dipakai bila belum ada daftar foto. */
  media_url?: string | null;
  start_date: string;
  end_date: string;
  is_mandatory: boolean;
  cooldown_seconds: number;
  created_at: string;
}

export interface CampaignReader {
  acknowledgment_id: string;
  campaign_id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  platform: string;
  acknowledged_at: string;
  read_duration_seconds: number;
  device_info?: string | null;
}

export interface VehicleInspection {
  id: string;
  asset_id: string;
  asset_name: string;
  plate_number?: string | null;
  inspector_name: string;
  inspection_type: string;
  inspection_date: string;
  odometer_km?: number | null;
  status: string;
  notes?: string | null;
  is_verified_by_hse: boolean;
  verified_at?: string | null;
  verified_by_name?: string | null;
}

function mapCampaign(campaign: CampaignDto | ActiveCampaignDto): HseCampaign {
  return {
    id: campaign.campaign_id,
    title: campaign.title,
    content_body: campaign.content_html,
    target_audience: campaign.target_audience,
    media_ids: (campaign.media_paths ?? []).map(String),
    media_captions: campaign.media_captions ?? [],
    // Kampanye lama memakai media_path sebagai URL; kampanye carousel menyimpan id berkas di media_paths.
    media_url: campaign.media_paths?.length ? null : campaign.media_path,
    start_date: campaign.start_date,
    end_date: campaign.end_date,
    is_mandatory: campaign.is_mandatory,
    cooldown_seconds: campaign.cooldown_seconds,
    created_at: campaign.create_at,
  };
}

function mapVehicleInspection(
  inspection: Schemas["VehicleInspectionResponse"],
): VehicleInspection {
  return {
    id: inspection.inspection_id,
    asset_id: inspection.vehicle_id,
    asset_name: inspection.vehicle_name ?? "-",
    plate_number: inspection.number_plate,
    inspector_name: inspection.inspector_name ?? "-",
    inspection_type: inspection.period_type,
    inspection_date: inspection.inspection_date,
    odometer_km: inspection.odometer_km,
    status: inspection.status,
    notes: inspection.notes,
    is_verified_by_hse: Boolean(inspection.verified_at || inspection.verified_by_id),
    verified_at: inspection.verified_at,
    verified_by_name: inspection.verifier_name,
  };
}

export async function fetchActiveHsePopup(): Promise<HseCampaign | null> {
  const res = await api.get<{ campaign: ActiveCampaignDto | null }>(
    "/hse/campaigns/active-popup",
  );
  return res.data.campaign ? mapCampaign(res.data.campaign) : null;
}

export async function acknowledgeHseCampaign(
  campaignId: string,
  readDurationSeconds: number,
  deviceInfo?: string,
): Promise<void> {
  const payload: Schemas["HseAcknowledgeCreate"] = {
    platform: "web",
    device_info: deviceInfo,
    scroll_completed: true,
    read_duration_seconds: readDurationSeconds,
  };
  await api.post(`/hse/campaigns/${campaignId}/acknowledge`, payload);
}

export async function fetchHseCampaigns(): Promise<HseCampaign[]> {
  const res = await api.get<CampaignDto[]>("/hse/campaigns");
  return res.data.map(mapCampaign);
}

export async function createHseCampaign(payload: {
  title: string;
  content_body: string;
  target_audience: "ALL" | "FIELD" | "OFFICE";
  /** Id berkas foto (file_object) berurutan, maks 8. */
  media_ids?: string[];
  /** Keterangan per foto (sejajar media_ids), maks 300 karakter; kosong bila tidak ada. */
  media_captions?: string[];
  start_date: string;
  end_date: string;
  is_mandatory: boolean;
  cooldown_seconds: number;
}): Promise<HseCampaign> {
  const mediaIds = payload.media_ids ?? [];
  const apiPayload: Schemas["HseCampaignCreate"] = {
    title: payload.title,
    content_html: payload.content_body,
    target_audience: payload.target_audience,
    media_paths: mediaIds,
    media_captions: payload.media_captions ?? [],
    start_date: payload.start_date,
    end_date: payload.end_date,
    is_mandatory: payload.is_mandatory,
    cooldown_seconds: payload.cooldown_seconds,
    is_active: true,
  };
  const res = await api.post<CampaignDto>("/hse/campaigns", apiPayload);
  return mapCampaign(res.data);
}

export async function fetchCampaignReaders(campaignId: string): Promise<CampaignReader[]> {
  const res = await api.get<Schemas["HseCampaignAuditStats"]>(
    `/hse/campaigns/${campaignId}/readers`,
  );
  return res.data.readers.map((reader) => ({
    acknowledgment_id: reader.acknowledgment_id,
    campaign_id: reader.campaign_id,
    user_id: reader.user_id,
    user_email: reader.email,
    user_name: reader.full_name,
    platform: reader.platform,
    acknowledged_at: reader.acknowledged_at,
    read_duration_seconds: reader.read_duration_seconds,
    device_info: reader.device_info,
  }));
}

export async function fetchVehicleInspections(): Promise<VehicleInspection[]> {
  const res = await api.get<Schemas["VehicleInspectionResponse"][]>("/hse/inspections");
  return res.data.map(mapVehicleInspection);
}

export async function verifyVehicleInspection(
  inspectionId: string,
  notes?: string,
): Promise<void> {
  const payload: Schemas["VehicleInspectionVerify"] = { status: "VERIFIED", notes };
  await api.patch(`/hse/inspections/${inspectionId}/verify`, payload);
}
