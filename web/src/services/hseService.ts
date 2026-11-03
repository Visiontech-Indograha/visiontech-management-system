import { api } from "@/lib/apiClient";

export interface HseCampaign {
  id: string;
  title: string;
  content_body: string;
  target_audience: "ALL" | "FIELD" | "OFFICE";
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
  user_role: string;
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
  status: "PASSED" | "NEEDS_ATTENTION" | "FAILED";
  notes?: string | null;
  is_verified_by_hse: boolean;
  verified_at?: string | null;
  verified_by_name?: string | null;
}

export async function fetchActiveHsePopup(): Promise<HseCampaign | null> {
  const res = await api.get<HseCampaign | null>("/hse/campaigns/active-popup");
  return res.data;
}

export async function acknowledgeHseCampaign(
  campaignId: string,
  readDurationSeconds: number,
  deviceInfo?: string
): Promise<void> {
  await api.post(`/hse/campaigns/${campaignId}/acknowledge`, {
    read_duration_seconds: readDurationSeconds,
    device_info: deviceInfo,
  });
}

export async function fetchHseCampaigns(): Promise<HseCampaign[]> {
  const res = await api.get<HseCampaign[]>("/hse/campaigns");
  return res.data;
}

export async function createHseCampaign(payload: {
  title: string;
  content_body: string;
  target_audience: "ALL" | "FIELD" | "OFFICE";
  media_url?: string | null;
  start_date: string;
  end_date: string;
  is_mandatory: boolean;
  cooldown_seconds: number;
}): Promise<HseCampaign> {
  const res = await api.post<HseCampaign>("/hse/campaigns", payload);
  return res.data;
}

export async function fetchCampaignReaders(campaignId: string): Promise<CampaignReader[]> {
  const res = await api.get<CampaignReader[]>(`/hse/campaigns/${campaignId}/readers`);
  return res.data;
}

export async function fetchVehicleInspections(): Promise<VehicleInspection[]> {
  const res = await api.get<VehicleInspection[]>("/hse/inspections");
  return res.data;
}

export async function verifyVehicleInspection(
  inspectionId: string,
  notes?: string
): Promise<void> {
  await api.patch(`/hse/inspections/${inspectionId}/verify`, { notes });
}

