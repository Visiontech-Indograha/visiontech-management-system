import { useState } from "react";
import { MessTemplate } from "@/components/templates/mess/MessTemplate";
import { type MessStay, useMessStays, useCheckoutMessStay } from "@/services/messService";

export function MessPage() {
  const stays = useMessStays();
  const checkout = useCheckoutMessStay();
  const [adding, setAdding] = useState(false);

  const handleCheckout = async (stay: MessStay) => {
    await checkout.mutateAsync({ id: stay.mess_stay_id });
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
