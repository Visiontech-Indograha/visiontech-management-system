import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import type { components } from "@/lib/api-types";
import { ResourcePage } from "./ResourcePage";

type S = components["schemas"];

export function ProductsPage() {
  return (
    <ResourcePage<S["ProductOut"]>
      title="Produk"
      noun="produk"
      endpoint="/products"
      managePermission="master:product"
      rowName={(r) => r.name}
      columns={[
        { header: "Kode", cell: (r) => <span className="font-medium">{r.code}</span> },
        { header: "Nama", cell: (r) => r.name },
      ]}
      fields={[
        { name: "code", label: "Kode", hint: "Contoh: CCTV, BARRIER_GATE" },
        { name: "name", label: "Nama" },
      ]}
    />
  );
}

export function VehiclesPage() {
  return (
    <ResourcePage<S["VehicleOut"]>
      title="Kendaraan"
      noun="kendaraan"
      endpoint="/vehicles"
      managePermission="master:vehicle"
      rowName={(r) => r.plate_number}
      columns={[
        { header: "Plat nomor", cell: (r) => <span className="font-medium">{r.plate_number}</span> },
        { header: "Nama", cell: (r) => r.name },
        { header: "Tipe", cell: (r) => r.type ?? "-" },
        { header: "Catatan", cell: (r) => r.notes ?? "-" },
      ]}
      fields={[
        { name: "plate_number", label: "Plat nomor" },
        { name: "name", label: "Nama" },
        { name: "type", label: "Tipe" },
        { name: "notes", label: "Catatan" },
      ]}
    />
  );
}

export function SitesPage() {
  return (
    <ResourcePage<S["SiteOut"]>
      title="Site"
      noun="site"
      endpoint="/sites"
      managePermission="master:site"
      rowName={(r) => r.name}
      columns={[
        { header: "Nama", cell: (r) => <span className="font-medium">{r.name}</span> },
        { header: "Customer", cell: (r) => r.customer_name ?? "-" },
        { header: "Alamat", cell: (r) => r.address ?? "-" },
        {
          header: "Koordinat",
          cell: (r) => (r.latitude != null && r.longitude != null ? `${r.latitude}, ${r.longitude}` : "-"),
        },
      ]}
      fields={[
        { name: "name", label: "Nama" },
        { name: "customer_name", label: "Customer" },
        { name: "address", label: "Alamat" },
        { name: "latitude", label: "Latitude", type: "number", step: "any", hint: "Isi bersama longitude." },
        { name: "longitude", label: "Longitude", type: "number", step: "any" },
      ]}
    />
  );
}

const ITEM_COLUMNS = [
  { header: "Nama", cell: (r: S["ItemOut"]) => <span className="font-medium">{r.name}</span> },
  { header: "Satuan", cell: (r: S["ItemOut"]) => r.unit },
  { header: "SKU", cell: (r: S["ItemOut"]) => r.sku ?? "-" },
  {
    header: "Dikembalikan",
    cell: (r: S["ItemOut"]) => (r.returnable ? <Badge tone="info">Ya</Badge> : <Badge>Tidak</Badge>),
  },
];

const ITEM_FIELDS = [
  { name: "name", label: "Nama" },
  { name: "unit", label: "Satuan", hint: "Contoh: pcs, roll, meter" },
  { name: "sku", label: "SKU" },
];

/** Item barang proyek (PROJECT_GOODS) — dikelola Admin (dan SA). */
export function ProjectItemsPage() {
  return (
    <ResourcePage<S["ItemOut"]>
      title="Item barang"
      noun="item"
      endpoint="/items"
      params={{ category: "PROJECT_GOODS" }}
      createDefaults={{ category: "PROJECT_GOODS" }}
      managePermission="master:item_project"
      rowName={(r) => r.name}
      columns={ITEM_COLUMNS}
      fields={[...ITEM_FIELDS, { name: "returnable", label: "Harus dikembalikan", type: "checkbox" }]}
    />
  );
}

/** Item TOOL dan PPE (APD) — dikelola HES (dan SA). */
export function ToolItemsPage() {
  const [category, setCategory] = useState<"TOOL" | "PPE">("TOOL");
  return (
    <ResourcePage<S["ItemOut"]>
      key={category}
      title="Item tool/APD"
      noun={category === "TOOL" ? "tool" : "APD"}
      endpoint="/items"
      params={{ category }}
      createDefaults={{ category }}
      managePermission="master:item_tool_ppe"
      rowName={(r) => r.name}
      columns={ITEM_COLUMNS}
      fields={[...ITEM_FIELDS, { name: "returnable", label: "Harus dikembalikan", type: "checkbox" }]}
      toolbar={
        <div role="group" aria-label="Kategori" className="flex rounded-control border border-line bg-surface p-0.5 text-sm">
          {(["TOOL", "PPE"] as const).map((c) => (
            <button
              key={c}
              type="button"
              aria-pressed={category === c}
              onClick={() => setCategory(c)}
              className={`h-9 rounded-control px-3 font-medium ${category === c ? "bg-lens-soft text-lens" : "text-mist"}`}
            >
              {c === "TOOL" ? "Tool" : "APD"}
            </button>
          ))}
        </div>
      }
    />
  );
}
