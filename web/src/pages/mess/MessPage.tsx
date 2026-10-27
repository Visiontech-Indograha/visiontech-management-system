import { useState } from "react";
import { toast } from "sonner";
import {
  MessTemplate,
  type MessTab,
} from "@/components/templates/mess/MessTemplate";
import { errorMessage } from "@/lib/errors";
import {
  type MessStay,
  useCheckoutMessStay,
  useMessPlaces,
  useMessStays,
} from "@/services/messService";
import { useSession } from "@/stores/sessionStore";

export function MessPage() {
  const { me } = useSession();
  const canManage = Boolean(me?.permissions.includes("manage:mess"));
  const canReview = Boolean(me?.permissions.includes("review:mess"));
  const stays = useMessStays({ status: "APPROVED" });
  const requests = useMessStays({ status: "REQUESTED" });
  const places = useMessPlaces();
  const checkout = useCheckoutMessStay();
  const [tab, setTab] = useState<MessTab>("stays");
  const [adding, setAdding] = useState(false);
  const [addingPlace, setAddingPlace] = useState(false);

  const tabs: [MessTab, string][] = [["stays", "Hunian"]];
  if (canReview) tabs.push(["requests", "Permintaan"]);
  tabs.push(["places", "Daftar Mess"]);

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
      tab={tab}
      tabs={tabs}
      onTabChange={setTab}
      pendingCount={requests.data?.length ?? 0}
      stays={stays}
      requests={requests}
      places={places}
      canManage={canManage}
      adding={adding}
      addingPlace={addingPlace}
      onAdd={() => setAdding(true)}
      onCheckout={handleCheckout}
      onCloseAdd={() => setAdding(false)}
      onAddPlace={() => setAddingPlace(true)}
      onCloseAddPlace={() => setAddingPlace(false)}
    />
  );
}
