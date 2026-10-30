import { useState } from "react";
import { toast } from "sonner";
import {
  MessTemplate,
  type MessTab,
} from "@/components/templates/mess/MessTemplate";
import { useListControls } from "@/hooks/useListControls";
import { usePagedList } from "@/hooks/usePagedList";
import { errorMessage } from "@/lib/errors";
import { messActions } from "@/lib/aksiPeran";
import {
  type MessPlace,
  type MessStay,
  useCheckoutMessStay,
} from "@/services/messService";
import { useSession } from "@/stores/sessionStore";

export function MessPage() {
  const { me } = useSession();
  const actions = messActions(me?.permissions ?? []);
  const canManage = actions.includes("manageStays");
  const canReview = actions.includes("reviewRequests");
  const stayControls = useListControls({ prefix: "hunian_" });
  const requestControls = useListControls({ prefix: "req_" });
  const placeControls = useListControls({ prefix: "msp_" });
  const stays = usePagedList<MessStay>(["mess-stays"], "/mess", stayControls, { status: "APPROVED" });
  const requests = usePagedList<MessStay>(["mess-stays"], "/mess", requestControls, { status: "REQUESTED" });
  const places = usePagedList<MessPlace>(["mess-places"], "/mess/places", placeControls);
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
      pendingCount={requests.data?.total ?? 0}
      stays={stays}
      stayControls={stayControls}
      requests={requests}
      requestControls={requestControls}
      places={places}
      placeControls={placeControls}
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
