import { SystemSettingsTemplate } from "@/components/templates/system/SystemSettingsTemplate";

/** Setelan sistem (GET/PUT /system/settings, izin manage:system_settings, hanya Super Admin). */
export function SystemSettingsPage() {
  return <SystemSettingsTemplate />;
}
