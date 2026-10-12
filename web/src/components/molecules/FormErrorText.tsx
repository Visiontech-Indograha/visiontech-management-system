import { Text } from "../atoms/Text";

/** Galat umum formulir di atas isian (kotak merah, `role="alert"`); tidak tampil bila `message` kosong. */
export function FormErrorText({ message, className = "mb-4" }: { message: string | null | undefined; className?: string }) {
  if (!message) return null;
  return (
    <Text role="alert" className={`${className} rounded-control bg-danger-soft px-3 py-2 text-sm text-danger`}>
      {message}
    </Text>
  );
}
