import type { UseQueryResult } from "@tanstack/react-query";
import { MessAddButton } from "@/components/organisms/mess/MessAddButton";
import { MessFormDialog } from "@/components/organisms/mess/MessFormDialog";
import { MessList } from "@/components/organisms/mess/MessList";
import { MessPlaceList } from "@/components/organisms/mess/MessPlaceList";
import { MessRequestList } from "@/components/organisms/mess/MessRequestList";
import { MessTabs, type MessTab } from "@/components/organisms/mess/MessTabs";
import type { MessPlace, MessStay } from "@/services/messService";
import { PageTemplate } from "../PageTemplate";

export type { MessTab };

export function MessTemplate({
  tab,
  tabs,
  onTabChange,
  pendingCount,
  stays,
  requests,
  places,
  canManage,
  adding,
  addingPlace,
  onAdd,
  onCheckout,
  onCloseAdd,
  onAddPlace,
  onCloseAddPlace,
}: {
  tab: MessTab;
  tabs: [MessTab, string][];
  onTabChange: (tab: MessTab) => void;
  pendingCount: number;
  stays: UseQueryResult<MessStay[]>;
  requests: UseQueryResult<MessStay[]>;
  places: UseQueryResult<MessPlace[]>;
  canManage: boolean;
  adding: boolean;
  addingPlace: boolean;
  onAdd: () => void;
  onCheckout: (stay: MessStay) => void;
  onCloseAdd: () => void;
  onAddPlace: () => void;
  onCloseAddPlace: () => void;
}) {
  const action =
    canManage && tab === "stays" ? (
      <MessAddButton onAdd={onAdd} />
    ) : canManage && tab === "places" ? (
      <MessAddButton onAdd={onAddPlace} label="Tambah Mess" />
    ) : undefined;
  return (
    <PageTemplate title="Mess Karyawan" action={action}>
      <MessTabs
        tab={tab}
        tabs={tabs}
        pendingCount={pendingCount}
        onTabChange={onTabChange}
      />
      {tab === "stays" && (
        <MessList
          stays={stays}
          canAdd={canManage}
          onAdd={onAdd}
          onCheckout={onCheckout}
        />
      )}
      {tab === "requests" && <MessRequestList requests={requests} />}
      {tab === "places" && (
        <MessPlaceList
          places={places}
          canManage={canManage}
          adding={addingPlace}
          onCloseAdd={onCloseAddPlace}
        />
      )}
      {adding && <MessFormDialog onClose={onCloseAdd} />}
    </PageTemplate>
  );
}
