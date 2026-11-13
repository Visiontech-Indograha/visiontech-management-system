import type { ComponentProps } from "react";
import { SetupForm } from "@/components/organisms/auth/SetupForm";

/** Kerangka penyiapan awal: kartu di tengah layar. */
export function SetupTemplate(props: ComponentProps<typeof SetupForm>) {
  return (
    <main className="no-reveal flex min-h-screen items-center justify-center bg-background px-4 py-10">
      <SetupForm {...props} />
    </main>
  );
}
