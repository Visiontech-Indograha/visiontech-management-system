import { MessageCircle, Phone } from "../atoms/Icon";
import { Anchor } from "../atoms/RouterLink";
import { Text } from "../atoms/Text";

/** 0812-3456-7890 → 6281234567890 (format wa.me). */
function waNumber(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  return digits.startsWith("0") ? `62${digits.slice(1)}` : digits;
}

/** Nomor HP + tombol Telepon & WhatsApp (kontak PM ↔ ketua/anggota tim). Tanpa nomor → teks "belum ada nomor HP". */
export function ContactLinks({ phone, name, compact = false }: { phone?: string | null; name?: string | null; compact?: boolean }) {
  if (!phone) return <Text as="span" className="text-xs text-mist">belum ada nomor HP</Text>;
  const btn =
    "inline-flex items-center gap-1 rounded-control border border-line px-2 py-0.5 text-xs font-medium text-ink hover:bg-hover";
  return (
    <div className="inline-flex flex-wrap items-center gap-2">
      {!compact && <Text as="span" className="text-xs text-mist">{phone}</Text>}
      <Anchor href={`tel:${phone.replace(/[^\d+]/g, "")}`} className={btn} aria-label={`Telepon ${name ?? phone}`}>
        <Phone size={14} aria-hidden /> Telepon
      </Anchor>
      <Anchor
        href={`https://wa.me/${waNumber(phone)}`}
        target="_blank"
        rel="noopener"
        className={btn}
        aria-label={`WhatsApp ${name ?? phone}`}
      >
        <MessageCircle size={14} aria-hidden /> WhatsApp
      </Anchor>
    </div>
  );
}
