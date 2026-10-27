import { useState } from "react";
import { toast } from "sonner";
import { MessTemplate } from "@/components/templates/mess/MessTemplate";
import { errorMessage } from "@/lib/errors";
import { type MessStay, useMessStays, useCheckoutMessStay } from "@/services/messService";

export function MessPage() {
  const stays = useMessStays();
  const checkout = useCheckoutMessStay();
  const [adding, setAdding] = useState(false);

  const handleCheckout = async (stay: MessStay) => {
    try {
      await checkout.mutateAsync({ id: stay.mess_stay_id });
      toast.success(`Inap ${stay.employee_name} ditandai selesai.`);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <MessTemplate
      stays={stays}
      adding={adding}
      onAdd={() => setAdding(true)}
      onCheckout={handleCheckout}
      onCloseAdd={() => setAdding(false)}
    />
  );
}
