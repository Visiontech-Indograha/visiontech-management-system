<#
.SYNOPSIS
  Uji pulih bulanan (manual, butuh kunci privat age): dekripsi cadangan terbaru ke folder sementara, cek isinya,
  hapus folder sementara, catat hasil di log. TIDAK menimpa database/MinIO mana pun.
.DESCRIPTION
  DB   : age -d -> berkas .dump -> pg_restore --list (jumlah entri harus > 0). Tanpa pg_restore: cek header 'PGDMP'.
  MinIO: age -d -> tar -tf; hitung berkas. Memeriksa seluruh rantai set terbaru (full + inkremental).
  Kunci privat dibaca dari -Identitas; jalankan dari sesi yang kunci itu terpasang (mis. diambil dari penyimpanan aman).
.EXAMPLE
  .\Uji-Pulih.ps1 -Identitas E:\kunci\vms-age.key -Lingkungan prod
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Identitas,
    [string]$Tujuan = 'D:\cadangan-vms',
    [string]$Lingkungan = 'prod',
    [string]$Sementara = (Join-Path $env:TEMP ('uji-pulih-' + [guid]::NewGuid().ToString('N')))
)
$ErrorActionPreference = 'Stop'
$script:FolderLog = Join-Path $Tujuan 'log'
. (Join-Path $PSScriptRoot 'Cadangan-Umum.ps1')
if (-not (Get-Command age.exe -ErrorAction SilentlyContinue)) { throw 'age.exe tidak ditemukan di PATH (winget install FiloSottile.age).' }
if (-not (Test-Path $Identitas)) { throw "Berkas kunci privat tidak ada: $Identitas" }
$hasil = @()
$gagal = $false
New-Item -ItemType Directory -Force -Path $Sementara | Out-Null
try {
    $semua = @(Daftar-Cadangan $Tujuan $Lingkungan)

    $db = $semua | Where-Object { $_.Tipe -eq 'db' } | Select-Object -Last 1
    if (-not $db) { throw "Tidak ada cadangan DB untuk $Lingkungan" }
    $dump = Join-Path $Sementara 'uji.dump'
    & age.exe -d -i $Identitas -o $dump (Join-Path $Tujuan "$Lingkungan\$($db.Nama)")
    if ($LASTEXITCODE -ne 0) { throw "Dekripsi DB gagal: $($db.Nama)" }
    $pr = Get-Command pg_restore.exe -ErrorAction SilentlyContinue
    if ($pr) {
        $entri = @(& $pr.Source --list $dump | Where-Object { $_ -and $_ -notmatch '^;' }).Count
        if ($entri -le 0) { throw 'pg_restore --list tidak menemukan entri' }
        $hasil += "DB $($db.Nama): pg_restore --list OK, $entri entri, $([math]::Round((Get-Item $dump).Length/1MB,1)) MB"
    } else {
        $kepala = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($dump)[0..4])
        if ($kepala -ne 'PGDMP') { throw 'Header dump bukan PGDMP' }
        $hasil += "DB $($db.Nama): header PGDMP OK (pg_restore tidak terpasang, hanya cek header)"
    }
    Remove-Item -Force $dump

    $mn = @($semua | Where-Object { $_.Tipe -eq 'minio' })
    $idx = -1
    for ($i = 0; $i -lt $mn.Count; $i++) { if ($mn[$i].Jenis -eq 'full') { $idx = $i } }
    if ($idx -lt 0) { throw "Tidak ada arsip MinIO penuh untuk $Lingkungan" }
    $rantai = @($mn[$idx..($mn.Count - 1)])
    $total = 0
    foreach ($o in $rantai) {
        $tar = Join-Path $Sementara 'uji.tar'
        & age.exe -d -i $Identitas -o $tar (Join-Path $Tujuan "$Lingkungan\$($o.Nama)")
        if ($LASTEXITCODE -ne 0) { throw "Dekripsi MinIO gagal: $($o.Nama)" }
        $baris = @(& tar.exe -tf $tar)
        if ($LASTEXITCODE -ne 0) { throw "tar -tf gagal: $($o.Nama)" }
        $berkas = @($baris | Where-Object { $_ -notmatch '/$' }).Count
        if ($o.Jenis -eq 'full' -and $berkas -le 0) { throw "Arsip penuh kosong: $($o.Nama)" }
        $total += $berkas
        $hasil += "MinIO $($o.Nama) ($($o.Jenis)): $berkas berkas"
        Remove-Item -Force $tar
    }
    $hasil += "MinIO rantai $($rantai.Count) arsip, total entri berkas $total"
} catch {
    $gagal = $true
    $hasil += "GAGAL: $($_.Exception.Message)"
} finally {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Sementara
}
foreach ($h in $hasil) { Tulis-Log "UjiPulih[$Lingkungan] $h" $(if ($gagal) { 'GALAT' } else { 'INFO' }) }
$laporan = Join-Path $script:FolderLog ('uji-pulih-{0}-{1}.txt' -f $Lingkungan, (Get-Date -Format 'yyyyMM'))
$hasil | Set-Content -Path $laporan -Encoding UTF8
if ($gagal) { Kirim-Peringatan "Uji pulih $Lingkungan GAGAL: $($hasil[-1])"; exit 1 }
Write-Host "Uji pulih LULUS. Laporan: $laporan"
exit 0
