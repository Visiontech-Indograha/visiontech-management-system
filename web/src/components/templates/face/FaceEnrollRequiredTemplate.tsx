import { FaceEnrollCapture } from "@/components/organisms/face/FaceEnrollCapture";
import { FaceEnrollIntro } from "@/components/organisms/face/FaceEnrollIntro";
import { FaceGateLogoutButton } from "@/components/organisms/face/FaceGateLogoutButton";

/** Kerangka layar penuh wajib daftar wajah: pendaftaran → tombol keluar. */
export function FaceEnrollRequiredTemplate({ onEnrolled, onLogout }: {
  onEnrolled: () => void;
  onLogout: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-4 px-4 py-8" data-testid="face-gate">
      <header className="text-center">
        <FaceEnrollIntro />
      </header>
      <section className="rounded-panel border border-line bg-surface p-4 shadow-card">
        <FaceEnrollCapture onEnrolled={onEnrolled} />
      </section>
      <div className="text-center">
        <FaceGateLogoutButton onLogout={onLogout} />
      </div>
    </main>
  );
}
