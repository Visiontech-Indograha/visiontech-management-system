import type { UseQueryResult } from "@tanstack/react-query";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { RetryNotice } from "@/components/molecules/RetryNotice";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { TextField } from "@/components/molecules/Field";
import { Briefcase, Building2, Phone, MapPin } from "@/components/molecules/Glyphs";
import { ClientAddButton } from "./ClientAddButton";
import type { Client } from "@/services/clientService";

export function ClientList({
  clients,
  canManage,
  onAdd,
  onEdit,
  onDeactivate,
  search,
  onSearchChange,
}: {
  clients: UseQueryResult<Client[]>;
  canManage: boolean;
  onAdd: () => void;
  onEdit: (client: Client) => void;
  onDeactivate: (client: Client) => void;
  search: string;
  onSearchChange: (value: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="w-full sm:w-72">
          <TextField
            label=""
            placeholder="Cari kode atau nama klien..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      {clients.isPending && (
        <div aria-hidden className="grid gap-3 md:grid-cols-2">
          <LoadingBar className="h-28" />
          <LoadingBar className="h-28" />
        </div>
      )}

      {clients.isError && (
        <RetryNotice
          message="Daftar klien tidak dapat dimuat."
          onRetry={() => clients.refetch()}
        />
      )}

      {clients.data?.length === 0 && (
        <div className="rounded-panel border border-line bg-surface p-8 text-center shadow-card">
          <Building2 className="mx-auto mb-3 text-mist" size={36} />
          <TextBlock className="mb-2 font-medium">Belum ada klien terdaftar</TextBlock>
          <TextBlock className="mb-4 text-sm text-mist">
            {search
              ? "Tidak ada klien yang cocok dengan kata kunci pencarian Anda."
              : "Daftarkan perusahaan mitra atau klien untuk memulai penugasan proyek."}
          </TextBlock>
          {canManage && !search && <ClientAddButton onAdd={onAdd} />}
        </div>
      )}

      {clients.data && clients.data.length > 0 && (
        <ListBlock className="grid gap-3 md:grid-cols-2">
          {clients.data.map((c) => (
            <ListEntry
              key={c.client_id}
              className="flex flex-col justify-between rounded-panel border border-line bg-surface p-4 shadow-card hover:border-mist transition-colors"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <TextBlock as="span" className="rounded-control bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
                        {c.client_code}
                      </TextBlock>
                      <TextBlock className="font-semibold text-foreground">{c.name}</TextBlock>
                    </div>
                  </div>
                  {!c.status && (
                    <TextBlock as="span" className="rounded-control bg-hover px-2 py-0.5 text-xs text-mist">
                      Nonaktif
                    </TextBlock>
                  )}
                </div>

                <div className="space-y-1 my-2 text-sm text-mist">
                  {c.pic_name && (
                    <div className="flex items-center gap-2 text-xs">
                      <Briefcase size={14} className="text-mist shrink-0" />
                      <TextBlock as="span">
                        PIC: <TextBlock as="strong" className="text-foreground">{c.pic_name}</TextBlock>
                      </TextBlock>
                    </div>
                  )}
                  {c.pic_phone && (
                    <div className="flex items-center gap-2 text-xs">
                      <Phone size={14} className="text-mist shrink-0" />
                      <TextBlock as="span">{c.pic_phone}</TextBlock>
                    </div>
                  )}
                  {c.address && (
                    <div className="flex items-start gap-2 text-xs">
                      <MapPin size={14} className="text-mist shrink-0 mt-0.5" />
                      <TextBlock as="span" className="line-clamp-2">{c.address}</TextBlock>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-line flex items-center justify-between">
                <TextBlock as="span" className="text-xs text-mist">
                  <TextBlock as="strong" className="text-foreground font-medium">{c.project_count ?? 0}</TextBlock> proyek terdaftar
                </TextBlock>
                {canManage && (
                  <div className="flex items-center gap-2">
                    <ActionButton
                      variant="ghost"
                      size="sm"
                      onClick={() => onEdit(c)}
                      aria-label={`Ubah ${c.name}`}
                    >
                      Ubah
                    </ActionButton>
                    <ActionButton
                      variant="ghost"
                      size="sm"
                      className="text-danger hover:text-danger"
                      onClick={() => onDeactivate(c)}
                      aria-label={`Hapus ${c.name}`}
                    >
                      Hapus
                    </ActionButton>
                  </div>
                )}
              </div>
            </ListEntry>
          ))}
        </ListBlock>
      )}
    </div>
  );
}
