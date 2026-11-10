<#
.SYNOPSIS
  Tarik (PULL) cadangan terenkripsi dari server Linux lewat SFTP (OpenSSH Client bawaan), verifikasi sha256,
  terapkan retensi, tulis log, kirim peringatan Discord/Uptime Kuma. Dijalankan Task Scheduler tiap malam.
.DESCRIPTION
  Hanya berkas dengan .manifest (tanda sah) yang ditarik. Berkas diunduh ke *.partial, diverifikasi, baru diberi nama.
  Retensi DB: harian 14, mingguan 8, bulanan 12. MinIO: set mingguan (penuh + inkremental) dibuang bila bagian
  terbarunya lebih tua dari 35 hari. Cadangan dianggap basi bila terbaru > 26 jam.
.EXAMPLE
  .\Tarik-Cadangan.ps1 -ServerHost 100.x.y.z -KunciSsh D:\rahasia\backup_reader_ed25519
  .\Tarik-Cadangan.ps1 -ServerHost 100.x.y.z -KunciSsh ... -HanyaPeriksa   # hanya cek kesegaran
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ServerHost,
    [Parameter(Mandatory)][string]$KunciSsh,
    [string]$Tujuan = 'D:\cadangan-vms',
    [string[]]$Lingkungan = @('prod', 'beta'),
    [string]$Pengguna = 'backup-reader',
    [int]$MaksUsiaJam = 26,
    [int]$RetensiMinioHari = 35,
    [int]$HarianDb = 14,
    [int]$MingguanDb = 8,
    [int]$BulananDb = 12,
    [switch]$HanyaPeriksa
)
$ErrorActionPreference = 'Stop'
$script:FolderLog = Join-Path $Tujuan 'log'
. (Join-Path $PSScriptRoot 'Cadangan-Umum.ps1')

function Jalankan-Sftp {
    param([string[]]$Perintah)
    $batch = Join-Path ([IO.Path]::GetTempPath()) ('sftp-' + [guid]::NewGuid().ToString('N') + '.txt')
    try {
        Set-Content -Path $batch -Value $Perintah -Encoding ASCII
        $keluar = & sftp.exe -b $batch -i $KunciSsh -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=20 -o ServerAliveInterval=30 "$Pengguna@$ServerHost" 2>&1
        if ($LASTEXITCODE -ne 0) { throw ('sftp gagal (kode {0}): {1}' -f $LASTEXITCODE, (($keluar | Select-Object -Last 5) -join ' | ')) }
        return $keluar
    } finally { Remove-Item -Force -ErrorAction SilentlyContinue $batch }
}

function Hash-Berkas([string]$Path) { (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLower() }

function Tarik-Lingkungan {
    param([string]$Env)
    $lokal = Join-Path $Tujuan $Env
    New-Item -ItemType Directory -Force -Path $lokal | Out-Null
    $daftar = Jalankan-Sftp @("ls -1 $Env")
    $nama = @($daftar | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ -match '\.(age|sha256|manifest)$' } |
        ForEach-Object { Split-Path $_ -Leaf } | Sort-Object -Unique)
    $baru = 0
    foreach ($a in @($nama | Where-Object { $_ -like '*.age' })) {
        if (-not (Baca-NamaCadangan $a)) { continue }
        if ((Test-Path (Join-Path $lokal $a)) -and (Test-Path (Join-Path $lokal "$a.manifest"))) { continue }
        # Tanda sah di server: manifest dan sha256 harus ada.
        if (($nama -notcontains "$a.manifest") -or ($nama -notcontains "$a.sha256")) { continue }
        $tmp = Join-Path $lokal "$a.partial"
        $null = Jalankan-Sftp @("get $Env/$a `"$tmp`"", "get $Env/$a.sha256 `"$lokal\$a.sha256.partial`"", "get $Env/$a.manifest `"$lokal\$a.manifest.partial`"")
        $diharap = ((Get-Content -Path "$lokal\$a.sha256.partial" -TotalCount 1) -split '\s+')[0].ToLower()
        $nyata = Hash-Berkas $tmp
        if ($diharap -ne $nyata) {
            Remove-Item -Force "$tmp", "$lokal\$a.sha256.partial", "$lokal\$a.manifest.partial"
            throw "Checksum TIDAK cocok untuk $Env/$a (server=$diharap, unduhan=$nyata)"
        }
        Move-Item -Force "$lokal\$a.sha256.partial" "$lokal\$a.sha256"
        Move-Item -Force $tmp (Join-Path $lokal $a)
        Move-Item -Force "$lokal\$a.manifest.partial" "$lokal\$a.manifest"   # manifest terakhir = sah
        Tulis-Log ("Ditarik {0} ({1:N1} MB), sha256 cocok" -f "$Env/$a", ((Get-Item (Join-Path $lokal $a)).Length / 1MB))
        $baru++
    }
    Tulis-Log "$Env: $baru berkas baru"
}

function Hapus-Cadangan($o) {
    $dir = Join-Path $Tujuan $o.Env
    foreach ($ekst in @('', '.sha256', '.manifest')) { Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $dir ($o.Nama + $ekst)) }
    Tulis-Log "Retensi: hapus $($o.Env)/$($o.Nama)"
}

function Terapkan-Retensi {
    param([string]$Env)
    # DB: simpan union {terbaru per hari (14), terbaru per minggu ISO (8), terbaru per bulan (12)}.
    $db = @(Daftar-Cadangan $Tujuan $Env | Where-Object { $_.Tipe -eq 'db' })
    $simpan = @{}
    $porHari = $db | Group-Object { $_.Waktu.ToString('yyyyMMdd') } | Sort-Object Name -Descending | Select-Object -First $HarianDb
    foreach ($g in $porHari) { $simpan[($g.Group | Sort-Object Waktu | Select-Object -Last 1).Nama] = 1 }
    $porMinggu = $db | Group-Object { '{0}-{1}' -f $_.Waktu.Year, [Globalization.CultureInfo]::InvariantCulture.Calendar.GetWeekOfYear($_.Waktu, 'FirstFourDayWeek', 'Monday') } |
        Sort-Object { ($_.Group | Sort-Object Waktu | Select-Object -Last 1).Waktu } -Descending | Select-Object -First $MingguanDb
    foreach ($g in $porMinggu) { $simpan[($g.Group | Sort-Object Waktu | Select-Object -Last 1).Nama] = 1 }
    $porBulan = $db | Group-Object { $_.Waktu.ToString('yyyyMM') } | Sort-Object Name -Descending | Select-Object -First $BulananDb
    foreach ($g in $porBulan) { $simpan[($g.Group | Sort-Object Waktu | Select-Object -Last 1).Nama] = 1 }
    foreach ($o in $db) { if (-not $simpan.ContainsKey($o.Nama)) { Hapus-Cadangan $o } }

    # MinIO: kelompokkan jadi set (full + inc berikutnya). Hapus set bila bagian terbarunya > 35 hari.
    # Set terakhir selalu dipertahankan. Berkas yang sudah dihapus di sumber hilang dari sini paling lambat
    # ~RetensiMinioHari + panjang set (7 hari) setelah set terakhir yang memuatnya.
    $mn = @(Daftar-Cadangan $Tujuan $Env | Where-Object { $_.Tipe -eq 'minio' })
    $set = @(); $cur = @()
    foreach ($o in $mn) {
        if ($o.Jenis -eq 'full' -and $cur.Count -gt 0) { $set += , $cur; $cur = @() }
        $cur += $o
    }
    if ($cur.Count -gt 0) { $set += , $cur }
    for ($i = 0; $i -lt $set.Count - 1; $i++) {
        $terbaru = ($set[$i] | Sort-Object Waktu | Select-Object -Last 1).Waktu
        if ($terbaru -lt (Get-Date).AddDays(-$RetensiMinioHari)) { foreach ($o in $set[$i]) { Hapus-Cadangan $o } }
    }
}

function Periksa-Kesegaran {
    param([string]$Env)
    $masalah = @()
    foreach ($tipe in @('db', 'minio')) {
        $o = @(Daftar-Cadangan $Tujuan $Env | Where-Object { $_.Tipe -eq $tipe -and (Test-Path (Join-Path $Tujuan "$Env\$($_.Nama).manifest")) }) | Select-Object -Last 1
        if (-not $o) { $masalah += "$Env/$tipe tidak ada cadangan sama sekali"; continue }
        $umur = ((Get-Date) - $o.Waktu).TotalHours
        if ($umur -gt $MaksUsiaJam) { $masalah += ('{0}/{1} basi: terbaru {2:N1} jam lalu (batas {3})' -f $Env, $tipe, $umur, $MaksUsiaJam) }
    }
    return $masalah
}

$masalah = @()
try {
    New-Item -ItemType Directory -Force -Path $Tujuan | Out-Null
    if (-not $HanyaPeriksa) {
        foreach ($e in $Lingkungan) {
            try { Tarik-Lingkungan $e; Terapkan-Retensi $e } catch { $masalah += "$e tarik gagal: $($_.Exception.Message)"; Tulis-Log $masalah[-1] 'GALAT' }
        }
    }
    foreach ($e in $Lingkungan) { $masalah += Periksa-Kesegaran $e }
} catch { $masalah += "Skrip gagal: $($_.Exception.Message)" }

if ($masalah.Count -gt 0) {
    Kirim-Peringatan ($masalah -join ' ; ')
    Kirim-Kuma $false ($masalah -join ' ; ')
    exit 1
}
Tulis-Log 'Semua cadangan segar dan terverifikasi'
Kirim-Kuma $true 'OK'
exit 0
