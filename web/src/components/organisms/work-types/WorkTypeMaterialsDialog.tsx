import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Edit2, Package, Plus, Trash2 } from "@/components/molecules/Glyphs";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextField, TextAreaField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import {
  TableBlock,
  TableBlockHead,
  TableBlockBody,
  TableBlockRow,
  TableBlockHeaderCell,
  TableBlockCell,
} from "@/components/molecules/TableBlock";
import {
  useWorkTypeMaterials,
  useCreateWorkTypeMaterial,
  useUpdateWorkTypeMaterial,
  useDeleteWorkTypeMaterial,
  type DefaultMaterial,
  type WorkType,
} from "@/services/workTypeService";

interface WorkTypeMaterialsDialogProps {
  workType: WorkType | null;
  onClose: () => void;
}

interface NewMaterialValues {
  material_code?: string;
  material_name: string;
  default_qty: number;
  unit: string;
  category?: string;
  description?: string;
}

export function WorkTypeMaterialsDialog({
  workType,
  onClose,
}: WorkTypeMaterialsDialogProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [editingMaterial, setEditingMaterial] = useState<DefaultMaterial | null>(null);

  const { data: materials = [], isPending, isError } = useWorkTypeMaterials(workType?.id || "");
  const createMaterial = useCreateWorkTypeMaterial();
  const updateMaterial = useUpdateWorkTypeMaterial();
  const deleteMaterial = useDeleteWorkTypeMaterial();

  const { register, handleSubmit, reset } = useForm<NewMaterialValues>({
    defaultValues: {
      material_code: "",
      material_name: "",
      default_qty: 1,
      unit: "Unit",
      category: "Kabel & Aksesoris",
      description: "",
    },
  });

  if (!workType) return null;

  const startEdit = (m: DefaultMaterial) => {
    setEditingMaterial(m);
    reset({
      material_name: m.material_name,
      material_code: m.material_code || "",
      default_qty: m.default_qty,
      unit: m.unit,
      category: m.category || "",
      description: m.description || "",
    });
    setIsAdding(true);
  };

  const handleCancelForm = () => {
    setIsAdding(false);
    setEditingMaterial(null);
    reset({
      material_code: "",
      material_name: "",
      default_qty: 1,
      unit: "Unit",
      category: "Kabel & Aksesoris",
      description: "",
    });
  };

  const onAddSubmit = async (values: NewMaterialValues) => {
    try {
      if (editingMaterial) {
        await updateMaterial.mutateAsync({
          workTypeId: workType.id,
          materialId: editingMaterial.default_material_id,
          payload: {
            material_name: values.material_name,
            material_code: values.material_code || undefined,
            default_qty: Number(values.default_qty),
            unit: values.unit,
            category: values.category || undefined,
            description: values.description || undefined,
          },
        });
        toast.success("Material default berhasil diperbarui.");
      } else {
        await createMaterial.mutateAsync({
          workTypeId: workType.id,
          payload: {
            material_name: values.material_name,
            material_code: values.material_code || undefined,
            default_qty: Number(values.default_qty),
            unit: values.unit,
            category: values.category || undefined,
            description: values.description || undefined,
          },
        });
        toast.success("Material default berhasil ditambahkan.");
      }
      handleCancelForm();
    } catch {
      toast.error(editingMaterial ? "Gagal memperbarui material default." : "Gagal menambahkan material default.");
    }
  };

  const handleDelete = async (materialId: string, name: string) => {
    try {
      await deleteMaterial.mutateAsync({
        workTypeId: workType.id,
        materialId,
      });
      toast.success(`Material '${name}' berhasil dihapus.`);
    } catch {
      toast.error("Gagal menghapus material default.");
    }
  };

  return (
    <VmsDialog
      open={Boolean(workType)}
      title={`Material standar: ${workType.name}`}
      onClose={onClose}
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-2">
          <TextBlock className="text-xs text-mist">
            Template kebutuhan material standar (1:N) yang akan otomatis disalin saat order proyek klien dibuat.
          </TextBlock>

          {!isAdding && (
            <ActionButton
              variant="default"
              size="sm"
              onClick={() => {
                setEditingMaterial(null);
                reset({
                  material_code: "",
                  material_name: "",
                  default_qty: 1,
                  unit: "Unit",
                  category: "Kabel & Aksesoris",
                  description: "",
                });
                setIsAdding(true);
              }}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Tambah Material
            </ActionButton>
          )}
        </div>

        {/* Form Tambah/Ubah Material */}
        {isAdding && (
          <div className="rounded-control border border-primary/30 bg-primary/5 p-3">
            <TextBlock className="mb-2 text-xs font-bold text-ink uppercase tracking-wider">
              {editingMaterial ? "Ubah Material Standar" : "Material Baru"}
            </TextBlock>
            <FormBlock id="add-material-template-form" onSubmit={handleSubmit(onAddSubmit)}>
              <TextField
                label="Nama Material"
                placeholder="misal: Kabel Fiber Optic Drop Core"
                {...register("material_name", { required: true })}
              />
              <div className="grid grid-cols-2 gap-2">
                <TextField
                  label="Kode (Opsional)"
                  placeholder="misal: FO-DROP-01"
                  {...register("material_code")}
                />
                <TextField
                  label="Kategori"
                  placeholder="misal: Kabel, Pipa, Tiang"
                  {...register("category")}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <TextField
                  type="number"
                  min={0}
                  step="any"
                  label="Kebutuhan Default"
                  {...register("default_qty", { required: true })}
                />
                <TextField
                  label="Satuan"
                  placeholder="Meter, Unit, Batang"
                  {...register("unit", { required: true })}
                />
              </div>
              <TextAreaField
                label="Keterangan Spesifikasi"
                placeholder="Standar pabrikan atau ukuran"
                {...register("description")}
              />
              <div className="mt-3 flex justify-end gap-2">
                <DialogActions
                  onCancel={handleCancelForm}
                  submitLabel={editingMaterial ? "Simpan Perubahan" : "Simpan Template"}
                  busy={createMaterial.isPending || updateMaterial.isPending}
                  formId="add-material-template-form"
                />
              </div>
            </FormBlock>
          </div>
        )}

        {/* 4 States Material List */}
        {isPending && (
          <div className="space-y-2 py-4">
            <LoadingBar className="h-8" />
            <LoadingBar className="h-8" />
          </div>
        )}

        {isError && (
          <div className="py-4 text-center">
            <TextBlock className="text-xs text-danger">
              Gagal memuat template material jenis pekerjaan.
            </TextBlock>
          </div>
        )}

        {!isPending && !isError && materials.length === 0 && !isAdding && (
          <div className="rounded-control border border-dashed border-line p-6 text-center">
            <Package className="mx-auto mb-1 h-6 w-6 text-mist" />
            <TextBlock className="text-xs text-mist">
              Belum ada material standar untuk jenis pekerjaan ini.
            </TextBlock>
          </div>
        )}

        {!isPending && !isError && materials.length > 0 && (
          <div className="overflow-x-auto rounded-control border border-line">
            <TableBlock>
              <TableBlockHead>
                <TableBlockRow>
                  <TableBlockHeaderCell className="w-10 text-center">No</TableBlockHeaderCell>
                  <TableBlockHeaderCell>Kode</TableBlockHeaderCell>
                  <TableBlockHeaderCell>Nama Material</TableBlockHeaderCell>
                  <TableBlockHeaderCell>Kategori</TableBlockHeaderCell>
                  <TableBlockHeaderCell className="text-right">Kebutuhan</TableBlockHeaderCell>
                  <TableBlockHeaderCell className="text-center">Satuan</TableBlockHeaderCell>
                  <TableBlockHeaderCell className="text-center">Aksi</TableBlockHeaderCell>
                </TableBlockRow>
              </TableBlockHead>
              <TableBlockBody>
                {materials.map((m, idx) => (
                  <TableBlockRow key={m.default_material_id}>
                    <TableBlockCell className="text-center text-xs text-mist">
                      {idx + 1}
                    </TableBlockCell>
                    <TableBlockCell className="font-mono text-xs text-mist">
                      {m.material_code || "-"}
                    </TableBlockCell>
                    <TableBlockCell className="font-medium text-ink">
                      {m.material_name}
                    </TableBlockCell>
                    <TableBlockCell className="text-xs text-mist">
                      {m.category || "-"}
                    </TableBlockCell>
                    <TableBlockCell className="text-right font-semibold text-primary">
                      {m.default_qty}
                    </TableBlockCell>
                    <TableBlockCell className="text-center text-xs text-mist">
                      {m.unit}
                    </TableBlockCell>
                    <TableBlockCell className="text-center">
                      <div className="flex items-center justify-center gap-1">
                        <ActionButton
                          variant="ghost"
                          size="sm"
                          onClick={() => startEdit(m)}
                          aria-label="Ubah Material"
                        >
                          <Edit2 className="h-3.5 w-3.5 text-mist hover:text-primary" />
                        </ActionButton>
                        <ActionButton
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(m.default_material_id, m.material_name)}
                          aria-label="Hapus Material"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-danger" />
                        </ActionButton>
                      </div>
                    </TableBlockCell>
                  </TableBlockRow>
                ))}
              </TableBlockBody>
            </TableBlock>
          </div>
        )}
      </div>
    </VmsDialog>
  );
}
