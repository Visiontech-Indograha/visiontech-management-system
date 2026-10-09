import type { ReactNode } from "react";
import { Text } from "../atoms/Text";

/** Judul bagian di dalam panel/kartu (h2). Contoh: <SectionTitle>Tindakan PM</SectionTitle> */
export function SectionTitle({ children, className = "mb-3" }: { children: ReactNode; className?: string }) {
  return (
    <Text as="h2" className={`${className} text-base font-semibold`}>
      {children}
    </Text>
  );
}
