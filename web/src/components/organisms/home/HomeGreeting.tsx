import { TextBlock } from "@/components/molecules/TextBlock";
function greeting(now = new Date()) {
  const hour = Number(new Intl.DateTimeFormat("id-ID", { hour: "numeric", hourCycle: "h23", timeZone: "Asia/Jakarta" }).format(now));
  if (hour < 11) return "Selamat pagi";
  if (hour < 15) return "Selamat siang";
  if (hour < 18) return "Selamat sore";
  return "Selamat malam";
}

/** Tanggal hari ini + sapaan sesuai jam Asia/Jakarta + nama akun. */
export function HomeGreeting({ today, name }: { today: string; name: string | undefined }) {
  return (
    <>
        <TextBlock className="text-body-sm text-mist">{today}</TextBlock>
        <TextBlock as="h1" className="mt-1 text-title-lg text-ink md:text-display">
          {greeting()}
          <TextBlock as="span" className="text-mist">, {name}</TextBlock>
        </TextBlock>
    </>
  );
}
