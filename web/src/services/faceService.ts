import { api } from "@/lib/apiClient";

/** Jawaban pemeriksaan satu gerakan liveness. `proof` hanya ada bila `status` = "sukses". */
export interface ChallengeResponse {
  status: "sukses" | "menunggu";
  detail: string;
  proof?: string | null;
}

/** POST /face/challenge-check — periksa satu bingkai kamera terhadap gerakan yang diminta. */
export async function checkFaceChallenge(form: FormData): Promise<ChallengeResponse> {
  return (await api.post<ChallengeResponse>("/face/challenge-check", form)).data;
}

/** POST /face/enroll — daftarkan wajah (beberapa pose + bukti liveness). */
export async function enrollFace(form: FormData): Promise<void> {
  await api.post("/face/enroll", form);
}

/** POST /face/probe — simpan gambar wajah sementara untuk absen; kembalikan `probe_id`. */
export async function probeFace(form: FormData): Promise<string> {
  return (await api.post<{ probe_id: string }>("/face/probe", form)).data.probe_id;
}
