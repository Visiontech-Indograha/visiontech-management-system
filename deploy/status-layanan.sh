#!/usr/bin/env bash
# Tabel jelas semua kontainer VMS: lingkungan, layanan, versi (commit), port (host → dalam), kesehatan.
#   bash deploy/status-layanan.sh        # di server atau PC (butuh docker)
# Lingkungan/versi dibaca dari label citra (vms.lingkungan, org.opencontainers.image.revision) yang diisi autodeploy.sh;
# kontainer infrastruktur (DB, MinIO) dikenali dari namanya.
set -uo pipefail
printf '%-16s %-9s %-8s %-9s %-26s %s\n' KONTAINER LINGKUNGAN LAYANAN VERSI "PORT (host→dalam)" STATUS
docker ps -a --filter "name=vms" --format '{{.Names}}' | sort | while read -r n; do
  lab() { docker inspect -f "{{index .Config.Labels \"$1\"}}" "$n" 2>/dev/null; }
  img=$(docker inspect -f '{{.Image}}' "$n" 2>/dev/null)
  ling=$(docker image inspect -f '{{index .Config.Labels "vms.lingkungan"}}' "$img" 2>/dev/null)
  lay=$(docker image inspect -f '{{index .Config.Labels "vms.layanan"}}' "$img" 2>/dev/null)
  rev=$(docker image inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$img" 2>/dev/null)
  case "$n" in
    *_beta_*|*_beta) : "${ling:=beta}" ;; *_test*|*-test*) : "${ling:=uji}" ;; *_prod*) : "${ling:=produksi}" ;; *-dev*|*_local*) : "${ling:=dev}" ;; esac
  case "$n" in *db*) lay=${lay:-database} ;; *minio*) lay=${lay:-minio} ;; esac
  ports=$(docker port "$n" 2>/dev/null | sed -E 's#^([0-9]+)/tcp -> (0\.0\.0\.0|127\.0\.0\.1|\[::\]|[0-9.]+):([0-9]+)$#\3→\1#' | sort -u | tr '\n' ' ')
  st=$(docker inspect -f '{{.State.Status}}{{if .State.Health}}/{{.State.Health.Status}}{{end}}' "$n" 2>/dev/null)
  printf '%-16s %-9s %-8s %-9s %-26s %s\n' "$n" "${ling:--}" "${lay:--}" "${rev:0:8}" "${ports:--}" "$st"
done
