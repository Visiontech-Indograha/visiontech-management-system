import { SystemSettingsList } from "@/components/organisms/system/SystemSettingsList";
import { PageTemplate } from "../PageTemplate";

/** Kerangka "Setelan sistem": daftar sakelar yang hanya bisa diubah Super Admin. */
export function SystemSettingsTemplate() {
  return (
    <PageTemplate title="Setelan sistem" description="Sakelar yang berlaku untuk seluruh sistem. Ubah dengan hati-hati.">
      <SystemSettingsList />
    </PageTemplate>
  );
}
