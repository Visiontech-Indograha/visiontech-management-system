import { describe, expect, it } from "vitest";
import { ACTION_LABEL, AUDIT_ENTITIES } from "./auditLabels";

describe("ACTION_LABEL", () => {
  it("punya label awam untuk kode audit baru", () => {
    expect(ACTION_LABEL.ACCOUNT_CREATE).toBe("Akun dibuat");
    expect(ACTION_LABEL.ACCOUNT_UNLOCK).toBe("Akun dibuka kuncinya");
    expect(ACTION_LABEL.ADMIN_UPDATE).toBe("Absensi diubah admin");
    expect(ACTION_LABEL.FACE_RESET).toBe("Data wajah direset");
    expect(ACTION_LABEL.FACE_SELF_RESET).toBe("Data wajah direset sendiri");
    expect(ACTION_LABEL.ROLE_CHANGE).toBe("Peran diubah");
    expect(ACTION_LABEL.BACKDATE_CREATED).toBe("Absen susulan diajukan");
    expect(ACTION_LABEL.BACKDATE_APPROVED).toBe("Absen susulan disetujui");
    expect(ACTION_LABEL.LOCATION_CHANGED).toBe("Lokasi diubah");
  });

  it("punya label untuk entitas rencana kerja harian", () => {
    expect(AUDIT_ENTITIES.work_plan_daily).toBe("Rencana kerja harian");
  });
});
