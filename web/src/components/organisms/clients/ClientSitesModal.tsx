import { useState } from "react";
import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TextField, TextAreaField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { MapPin, User, Plus, Trash2, Edit2, Compass } from "@/components/molecules/Glyphs";
import {
  useClientSites,
  useSaveClientSite,
  useDeleteClientSite,
  type Client,
  type ClientSite,
  type ClientSiteInput,
} from "@/services/clientService";

interface ClientSitesModalProps {
  client: Client;
  onClose: () => void;
}

export function ClientSitesModal({ client, onClose }: ClientSitesModalProps) {
  const { data: sites = [], isLoading } = useClientSites(client.client_id);
  const saveMutation = useSaveClientSite(client.client_id);
  const deleteMutation = useDeleteClientSite(client.client_id);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingSiteId, setEditingSiteId] = useState<string | null>(null);

  const [siteName, setSiteName] = useState("");
  const [address, setAddress] = useState("");
  const [latitude, setLatitude] = useState("-6.2088");
  const [longitude, setLongitude] = useState("106.8456");
  const [radius, setRadius] = useState("100");
  const [picName, setPicName] = useState("");
  const [picPhone, setPicPhone] = useState("");

  const handleOpenCreate = () => {
    setEditingSiteId(null);
    setSiteName("");
    setAddress("");
    setLatitude("-6.2088");
    setLongitude("106.8456");
    setRadius("100");
    setPicName("");
    setPicPhone("");
    setIsFormOpen(true);
  };

  const handleOpenEdit = (site: ClientSite) => {
    setEditingSiteId(site.site_id);
    setSiteName(site.site_name);
    setAddress(site.address);
    setLatitude(site.latitude.toString());
    setLongitude(site.longitude.toString());
    setRadius(site.geofence_radius_meters.toString());
    setPicName(site.pic_name || "");
    setPicPhone(site.pic_phone || "");
    setIsFormOpen(true);
  };

  const handleGetCurrentLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocation tidak didukung oleh browser ini.");
      return;
    }
    toast.info("Mengambil koordinat GPS saat ini...");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));
        toast.success("Koordinat GPS berhasil disinkronkan.");
      },
      (err) => {
        toast.error(`Gagal mendapatkan lokasi: ${err.message}`);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!siteName.trim()) {
      toast.error("Nama lokasi / cabang wajib diisi.");
      return;
    }
    if (!address.trim()) {
      toast.error("Alamat lokasi wajib diisi.");
      return;
    }

    const latNum = parseFloat(latitude);
    const lngNum = parseFloat(longitude);
    const radiusNum = parseInt(radius, 10);

    if (isNaN(latNum) || latNum < -90 || latNum > 90) {
      toast.error("Latitude tidak valid (-90 s/d 90).");
      return;
    }
    if (isNaN(lngNum) || lngNum < -180 || lngNum > 180) {
      toast.error("Longitude tidak valid (-180 s/d 180).");
      return;
    }
    if (isNaN(radiusNum) || radiusNum < 10) {
      toast.error("Radius geofence minimal 10 meter.");
      return;
    }

    const payload: ClientSiteInput = {
      site_name: siteName.trim(),
      address: address.trim(),
      latitude: latNum,
      longitude: lngNum,
      geofence_radius_meters: radiusNum,
      pic_name: picName.trim() || undefined,
      pic_phone: picPhone.trim() || undefined,
    };

    try {
      await saveMutation.mutateAsync({
        siteId: editingSiteId || undefined,
        data: payload,
      });
      toast.success(
        editingSiteId
          ? "Lokasi cabang berhasil diperbarui."
          : "Lokasi cabang baru berhasil ditambahkan."
      );
      setIsFormOpen(false);
    } catch {
      toast.error("Gagal menyimpan lokasi cabang.");
    }
  };

  const handleDelete = async (site: ClientSite) => {
    try {
      await deleteMutation.mutateAsync(site.site_id);
      toast.success("Lokasi cabang berhasil dihapus.");
    } catch {
      toast.error("Gagal menghapus lokasi cabang.");
    }
  };

  return (
    <VmsDialog
      open
      title={`Kelola Lokasi Site — ${client.name}`}
      onClose={onClose}
      size="xl"
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <div>
            <TextBlock className="text-sm text-mist">
              Lokasi site digunakan untuk validasi geofence absensi teknisi dan target tugas Work Order.
            </TextBlock>
          </div>
          {!isFormOpen && (
            <ActionButton variant="default" size="sm" onClick={handleOpenCreate}>
              <Plus size={16} className="mr-1" />
              <TextBlock as="span">Tambah Lokasi</TextBlock>
            </ActionButton>
          )}
        </div>

        {isFormOpen && (
          <FormBlock onSubmit={handleSubmit} className="rounded-panel border border-primary/20 bg-primary/5 p-4 space-y-3">
            <TextBlock className="font-semibold text-primary">
              {editingSiteId ? "Ubah Lokasi Cabang / Site" : "Tambah Lokasi Cabang Baru"}
            </TextBlock>

            <div className="space-y-3">
              <TextField
                label="Nama Lokasi / Site"
                placeholder="mis. Gedung Menara Thamrin Lt. 12"
                value={siteName}
                onChange={(e) => setSiteName(e.target.value)}
                required
              />
              <TextAreaField
                label="Alamat Lengkap"
                placeholder="Jl. M.H. Thamrin No. 9, Jakarta Pusat..."
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <TextField
                  label="PIC Lokasi (Opsional)"
                  placeholder="Nama Penanggung Jawab"
                  value={picName}
                  onChange={(e) => setPicName(e.target.value)}
                />
                <TextField
                  label="No. HP PIC (Opsional)"
                  placeholder="0812xxxxxxx"
                  value={picPhone}
                  onChange={(e) => setPicPhone(e.target.value)}
                />
              </div>

              {/* Coordinate & Geofence Picker */}
              <div className="rounded-control border border-line bg-surface p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <TextBlock className="text-xs font-semibold text-foreground flex items-center gap-1">
                    <Compass size={14} className="text-primary" />
                    <TextBlock as="span">Koordinat Geofence Absensi</TextBlock>
                  </TextBlock>
                  <ActionButton
                    type="button"
                    variant="link"
                    size="xs"
                    onClick={handleGetCurrentLocation}
                    className="p-0 h-auto text-primary font-medium"
                  >
                    <MapPin size={12} className="mr-1" />
                    <TextBlock as="span">Gunakan GPS Saat Ini</TextBlock>
                  </ActionButton>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <TextField
                    label="Latitude"
                    placeholder="-6.2088"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    required
                  />
                  <TextField
                    label="Longitude"
                    placeholder="106.8456"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    required
                  />
                  <TextField
                    label="Radius (Meter)"
                    type="number"
                    min="10"
                    max="5000"
                    placeholder="100"
                    value={radius}
                    onChange={(e) => setRadius(e.target.value)}
                    required
                  />
                </div>
                <TextBlock className="text-[11px] text-mist">
                  Teknisi yang bertugas pada site ini dapat presensi dalam radius toleransi di atas.
                </TextBlock>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <ActionButton
                type="button"
                variant="outline"
                onClick={() => setIsFormOpen(false)}
                disabled={saveMutation.isPending}
              >
                <TextBlock as="span">Batal</TextBlock>
              </ActionButton>
              <ActionButton
                type="submit"
                variant="default"
                disabled={saveMutation.isPending}
              >
                <TextBlock as="span">
                  {saveMutation.isPending
                    ? "Menyimpan..."
                    : editingSiteId
                    ? "Simpan Perubahan"
                    : "Simpan Lokasi"}
                </TextBlock>
              </ActionButton>
            </div>
          </FormBlock>
        )}

        <div className="space-y-2">
          {isLoading ? (
            <div className="p-6 text-center">
              <TextBlock className="text-mist">Memuat daftar lokasi cabang...</TextBlock>
            </div>
          ) : sites.length === 0 ? (
            <div className="p-6 text-center border border-dashed border-line rounded-control">
              <TextBlock className="text-mist text-sm">
                Belum ada lokasi cabang / site yang didaftarkan untuk klien ini.
              </TextBlock>
            </div>
          ) : (
            <div className="grid gap-2">
              {sites.map((site) => (
                <div
                  key={site.site_id}
                  className="flex items-center justify-between rounded-control border border-line bg-surface p-3 hover:border-mist transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <MapPin size={16} className="text-primary shrink-0" />
                      <TextBlock className="font-medium text-foreground">{site.site_name}</TextBlock>
                      <TextBlock as="span" className="rounded-control bg-hover px-1.5 py-0.5 text-[10px] text-mist">
                        Radius: {site.geofence_radius_meters}m
                      </TextBlock>
                    </div>
                    <TextBlock className="text-xs text-mist line-clamp-1">{site.address}</TextBlock>
                    <div className="flex items-center gap-3 text-[11px] text-mist">
                      <TextBlock as="span">
                        GPS: {Number(site.latitude).toFixed(4)}, {Number(site.longitude).toFixed(4)}
                      </TextBlock>
                      {site.pic_name && (
                        <div className="flex items-center gap-1">
                          <User size={10} />
                          <TextBlock as="span">
                            {site.pic_name} {site.pic_phone ? `(${site.pic_phone})` : ""}
                          </TextBlock>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0 ml-3">
                    <ActionButton
                      variant="ghost"
                      size="sm"
                      onClick={() => handleOpenEdit(site)}
                      title="Ubah lokasi ini"
                    >
                      <Edit2 size={14} />
                    </ActionButton>
                    <ActionButton
                      variant="ghost"
                      size="sm"
                      className="text-danger hover:text-danger"
                      onClick={() => handleDelete(site)}
                      title="Hapus lokasi ini"
                    >
                      <Trash2 size={14} />
                    </ActionButton>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </VmsDialog>
  );
}
