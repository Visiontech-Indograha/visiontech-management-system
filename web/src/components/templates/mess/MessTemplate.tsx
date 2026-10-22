import type { UseQueryResult } from "@tanstack/react-query";
import { MessAddButton } from "@/components/organisms/mess/MessAddButton";
import { MessFormDialog } from "@/components/organisms/mess/MessFormDialog";
import { MessList } from "@/components/organisms/mess/MessList";
import type { MessStay } from "@/services/messService";
import { PageTemplate } from "../PageTemplate";

export function MessTemplate({
  stays,
  adding,
  onAdd,
  onCheckout,
  onCloseAdd,
}: {
  stays: UseQueryResult<MessStay[]>;
  adding: boolean;
  onAdd: () => void;
  onCheckout: (stay: MessStay) => void;
  onCloseAdd: () => void;
}) {
  return (
    <PageTemplate title="Mess Karyawan" action={<MessAddButton onAdd={onAdd} />}>
      <MessList stays={stays} onAdd={onAdd} onCheckout={onCheckout} />
      {adding && <MessFormDialog onClose={onCloseAdd} />}
    </PageTemplate>
  );
}
