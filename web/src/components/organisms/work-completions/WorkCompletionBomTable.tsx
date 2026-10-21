import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Package, Plus, RefreshCw, Trash2, Edit2 } from "@/components/molecules/Glyphs";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import {
  TableBlock,
  TableBlockHead,
  TableBlockBody,
  TableBlockRow,
  TableBlockHeaderCell,
  TableBlockCell,
} from "@/components/molecules/TableBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { TextField, TextAreaField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import {
  useWorkCompletionBom,
  useCreateWorkCompletionBom,
  useUpdateWorkCompletionBom,
  useDeleteWorkCompletionBom,
  useSyncBomFromWorkTypes,
  type WorkCompletionBom,
} from "@/services/workCompletionService";

interface WorkCompletionBomTableProps {
  completionId: string;
  canManage: boolean;
}

interface AddMaterialFormValues {
  material_code?: string;
  material_name: string;
  estimated_qty: number;
  actual_qty?: number;
  unit: string;
  category?: string;
  notes?: string;
}

interface EditMaterialFormValues {
  actual_qty: number;
  estimated_qty: number;
  notes?: string;
}

export function WorkCompletionBomTable({
  completionId,
  canManage,
}: WorkCompletionBomTableProps) {
  const { data: bomItems = [], isPending, isError, refetch } = useWorkCompletionBom(completionId);
  const createBom = useCreateWorkCompletionBom();
  const updateBom = useUpdateWorkCompletionBom();
  const deleteBom = useDeleteWorkCompletionBom();
  const syncBom = useSyncBomFromWorkTypes();

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<WorkCompletionBom | null>(null);

  const addForm = useForm<AddMaterialFormValues>({
    defaultValues: {
      material_code: "",
      material_name: "",
      estimated_qty: 1,
      actual_qty: 0,
      unit: "Unit",
      category: "Material Utama",
      notes: "",
    },
  });

  const editForm = useForm<EditMaterialFormValues>({
    defaultValues: {
      actual_qty: 0,
      estimated_qty: 0,
      notes: "",
    },
  });

  const handleOpenEdit = (item: WorkCompletionBom) => {
    setEditingItem(item);
    editForm.reset({
      actual_qty: item.actual_qty,
      estimated_qty: item.estimated_qty,
      notes: item.notes || "",
    });
  };

  const onAddSubmit = async (values: AddMaterialFormValues) => {
    try {
      await createBom.mutateAsync({
        completionId,
        payload: {
          material_name: values.material_name,
          material_code: values.material_code || undefined,
          estimated_qty: Number(values.estimated_qty),
          actual_qty: Number(values.actual_qty || 0),
          unit: values.unit,
          category: values.category || undefined,
          notes: values.notes || undefined,
        },
      });
      toast.success("Material ditambahkan.");
      setIsAddOpen(false);
      addForm.reset();
    } catch {
      toast.error("Gagal menambahkan material.");
    }
  };

  const onEditSubmit = async (values: EditMaterialFormValues) => {
    if (!editingItem) return;
    try {
      await updateBom.mutateAsync({
        bomId: editingItem.bom_id,
        completionId,
        payload: {
          actual_qty: Number(values.actual_qty),
          estimated_qty: Number(values.estimated_qty),
          notes: values.notes || undefined,
        },
      });
      toast.success("Jumlah terpakai disimpan.");
      setEditingItem(null);
    } catch {
      toast.error("Jumlah terpakai gagal disimpan.");
    }
  };

  const handleDelete = async (item: WorkCompletionBom) => {
    try {
      await deleteBom.mutateAsync({
        bomId: item.bom_id,
        completionId,
      });
      toast.success(`Material '${item.material_name}' berhasil dihapus.`);
    } catch {
      toast.error("Gagal menghapus material.");
    }
  };

  const handleSyncFromWorkTypes = async () => {
    try {
      const res = await syncBom.mutateAsync({
        completionId,
        overwrite_existing: false,
      });
      toast.success(res.message || `${res.synced_count} material default berhasil disinkronkan.`);
    } catch {
      toast.error("Gagal menarik material default jenis pekerjaan.");
    }
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Package className="h-5 w-5 text-primary" />
          <TextBlock className="font-semibold text-ink">
            Daftar material
          </TextBlock>
          <TextBlock as="span" className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
            {bomItems.length} Item
          </TextBlock>
        </div>

        {canManage && (
          <div className="flex items-center gap-2">
            <ActionButton
              variant="outline"
              size="sm"
              onClick={handleSyncFromWorkTypes}
              disabled={syncBom.isPending}
            >
              <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${syncBom.isPending ? "animate-spin" : ""}`} />
              Tarik dari Master
            </ActionButton>
            <ActionButton
              variant="default"
              size="sm"
              onClick={() => setIsAddOpen(true)}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Tambah Material
            </ActionButton>
          </div>
        )}
      </div>

      {/* 4 States Handling */}
      {isPending && (
        <div className="space-y-2">
          <LoadingBar className="h-10" />
          <LoadingBar className="h-10" />
          <LoadingBar className="h-10" />
        </div>
      )}

      {isError && (
        <div className="rounded-panel border border-danger/30 bg-danger/5 p-4 text-center">
          <TextBlock className="mb-2 text-sm text-danger">
            Gagal memuat rincian material order.
          </TextBlock>
          <ActionButton variant="outline" size="sm" onClick={() => refetch()}>
            Coba Lagi
          </ActionButton>
        </div>
      )}

      {!isPending && !isError && bomItems.length === 0 && (
        <div className="rounded-panel border border-dashed border-line p-8 text-center">
          <Package className="mx-auto mb-2 h-8 w-8 text-mist" />
          <TextBlock className="mb-1 text-sm font-medium text-ink">
            Belum ada daftar material
          </TextBlock>
          <TextBlock className="mb-4 text-xs text-mist">
            Tarik material default dari jenis pekerjaan atau tambahkan manual.
          </TextBlock>
          {canManage && (
            <div className="flex justify-center gap-2">
              <ActionButton
                variant="outline"
                size="sm"
                onClick={handleSyncFromWorkTypes}
                disabled={syncBom.isPending}
              >
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                Tarik dari Master
              </ActionButton>
              <ActionButton
                variant="default"
                size="sm"
                onClick={() => setIsAddOpen(true)}
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                Tambah Material
              </ActionButton>
            </div>
          )}
        </div>
      )}

      {!isPending && !isError && bomItems.length > 0 && (
        <div className="overflow-x-auto rounded-control border border-line">
          <TableBlock>
            <TableBlockHead>
              <TableBlockRow>
                <TableBlockHeaderCell className="w-12 text-center">No</TableBlockHeaderCell>
                <TableBlockHeaderCell>Kode</TableBlockHeaderCell>
                <TableBlockHeaderCell>Nama Material</TableBlockHeaderCell>
                <TableBlockHeaderCell>Kategori</TableBlockHeaderCell>
                <TableBlockHeaderCell className="text-right">Estimasi</TableBlockHeaderCell>
                <TableBlockHeaderCell className="text-right">Terpakai</TableBlockHeaderCell>
                <TableBlockHeaderCell className="text-center">Satuan</TableBlockHeaderCell>
                <TableBlockHeaderCell className="text-right">Selisih</TableBlockHeaderCell>
                <TableBlockHeaderCell>Catatan Lapangan</TableBlockHeaderCell>
                {canManage && <TableBlockHeaderCell className="text-center">Aksi</TableBlockHeaderCell>}
              </TableBlockRow>
            </TableBlockHead>
            <TableBlockBody>
              {bomItems.map((item, index) => {
                const diff = item.actual_qty - item.estimated_qty;
                return (
                  <TableBlockRow key={item.bom_id}>
                    <TableBlockCell className="text-center text-xs text-mist">
                      {index + 1}
                    </TableBlockCell>
                    <TableBlockCell className="font-mono text-xs text-mist">
                      {item.material_code || "-"}
                    </TableBlockCell>
                    <TableBlockCell className="font-medium text-ink">
                      {item.material_name}
                    </TableBlockCell>
                    <TableBlockCell className="text-xs text-mist">
                      {item.category || "-"}
                    </TableBlockCell>
                    <TableBlockCell className="text-right font-medium">
                      {item.estimated_qty}
                    </TableBlockCell>
                    <TableBlockCell className="text-right font-bold text-primary">
                      {item.actual_qty}
                    </TableBlockCell>
                    <TableBlockCell className="text-center text-xs text-mist">
                      {item.unit}
                    </TableBlockCell>
                    <TableBlockCell className="text-right text-xs">
                      {diff === 0 ? (
                        <TextBlock as="span" className="font-medium text-emerald-600">Sesuai (0)</TextBlock>
                      ) : diff > 0 ? (
                        <TextBlock as="span" className="font-semibold text-rose-600">+{diff}</TextBlock>
                      ) : (
                        <TextBlock as="span" className="font-medium text-blue-600">{diff}</TextBlock>
                      )}
                    </TableBlockCell>
                    <TableBlockCell className="text-xs text-mist max-w-[200px] truncate" title={item.notes || ""}>
                      {item.notes || "-"}
                    </TableBlockCell>
                    {canManage && (
                      <TableBlockCell className="text-center">
                        <div className="flex items-center justify-center gap-1">
                          <ActionButton
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenEdit(item)}
                            aria-label="Ubah jumlah terpakai & catatan"
                          >
                            <Edit2 className="h-4 w-4" />
                          </ActionButton>
                          <ActionButton
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(item)}
                            aria-label="Hapus Material"
                          >
                            <Trash2 className="h-4 w-4 text-danger" />
                          </ActionButton>
                        </div>
                      </TableBlockCell>
                    )}
                  </TableBlockRow>
                );
              })}
            </TableBlockBody>
          </TableBlock>
        </div>
      )}

      {/* Dialog Tambah Material */}
      {isAddOpen && (
        <VmsDialog
          open
          title="Tambah material"
          onClose={() => setIsAddOpen(false)}
        >
            <FormBlock id="add-bom-material-form" onSubmit={addForm.handleSubmit(onAddSubmit)}>
            <TextField
              label="Nama Material"
              placeholder="misal: Kabel Fiber Optic Drop Core"
              {...addForm.register("material_name", { required: "Nama material wajib diisi." })}
            />
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="Kode Material (Opsional)"
                placeholder="misal: FO-001"
                {...addForm.register("material_code")}
              />
              <TextField
                label="Kategori"
                placeholder="misal: Kabel, Pipa, Konektor"
                {...addForm.register("category")}
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <TextField
                type="number"
                step="any"
                label="Estimasi Kebutuhan"
                {...addForm.register("estimated_qty", { required: true })}
              />
              <TextField
                type="number"
                step="any"
                label="Jumlah terpakai"
                {...addForm.register("actual_qty")}
              />
              <TextField
                label="Satuan"
                placeholder="Meter, Unit, Batang"
                {...addForm.register("unit", { required: true })}
              />
            </div>
            <TextAreaField
              label="Catatan Lapangan"
              placeholder="Keterangan spesifikasi teknis atau jalur penarikan"
              {...addForm.register("notes")}
            />
            <div className="mt-4 flex justify-end gap-2">
              <DialogActions
                onCancel={() => setIsAddOpen(false)}
                submitLabel="Simpan Material"
                busy={createBom.isPending}
                formId="add-bom-material-form"
              />
            </div>
          </FormBlock>
        </VmsDialog>
      )}

      {/* Dialog Edit Realisasi Material */}
      {editingItem && (
        <VmsDialog
          open
          title={`Ubah jumlah terpakai: ${editingItem.material_name}`}
          onClose={() => setEditingItem(null)}
        >
          <FormBlock id="edit-bom-material-form" onSubmit={editForm.handleSubmit(onEditSubmit)}>
            <div className="grid grid-cols-2 gap-3">
              <TextField
                type="number"
                step="any"
                label="Estimasi Kebutuhan"
                {...editForm.register("estimated_qty", { required: true })}
              />
              <TextField
                type="number"
                step="any"
                label={`Jumlah terpakai (${editingItem.unit})`}
                {...editForm.register("actual_qty", { required: true })}
              />
            </div>
            <TextAreaField
              label="Catatan lapangan"
              placeholder="mis. kabel FO terpakai 69 meter"
              {...editForm.register("notes")}
            />
            <div className="mt-4 flex justify-end gap-2">
              <DialogActions
                onCancel={() => setEditingItem(null)}
                submitLabel="Simpan"
                busy={updateBom.isPending}
                formId="edit-bom-material-form"
              />
            </div>
          </FormBlock>
        </VmsDialog>
      )}
    </div>
  );
}
