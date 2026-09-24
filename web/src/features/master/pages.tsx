import type { components } from "@/lib/api-types";
import { ResourcePage } from "./ResourcePage";

type S = components["schemas"];

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

