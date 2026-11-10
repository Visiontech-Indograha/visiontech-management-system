# Fungsi bersama skrip cadangan Windows (di-dot-source oleh Tarik-Cadangan.ps1 dan Uji-Pulih.ps1).
# Kompatibel Windows PowerShell 5.1 (Windows Server 2019). TIDAK berisi rahasia.
# Rahasia hanya lewat variabel lingkungan mesin: VMS_DISCORD_WEBHOOK, VMS_KUMA_PUSH_URL (keduanya opsional).
Set-StrictMode -Version 2.0

function Tulis-Log {
    param([string]$Pesan, [string]$Tingkat = 'INFO')
    $baris = '{0} [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Tingkat, $Pesan
    if (-not (Test-Path $script:FolderLog)) { New-Item -ItemType Directory -Force -Path $script:FolderLog | Out-Null }
    Add-Content -Path (Join-Path $script:FolderLog ('cadangan-{0}.log' -f (Get-Date -Format 'yyyyMM'))) -Value $baris -Encoding UTF8
    Write-Host $baris
}

function Kirim-Peringatan {
    param([string]$Pesan)
    Tulis-Log $Pesan 'PERINGATAN'
    $hook = [Environment]::GetEnvironmentVariable('VMS_DISCORD_WEBHOOK', 'Machine')
    if (-not $hook) { $hook = $env:VMS_DISCORD_WEBHOOK }
    if ($hook) {
        try {
            $isi = @{ content = ('[Cadangan pobonguar] ' + $Pesan) } | ConvertTo-Json
            Invoke-RestMethod -Uri $hook -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($isi)) -TimeoutSec 20 | Out-Null
        } catch { Tulis-Log ('Gagal kirim Discord: ' + $_.Exception.Message) 'GALAT' }
    }
}

function Kirim-Kuma {
    param([bool]$Sehat, [string]$Pesan)
    $url = [Environment]::GetEnvironmentVariable('VMS_KUMA_PUSH_URL', 'Machine')
    if (-not $url) { $url = $env:VMS_KUMA_PUSH_URL }
    if (-not $url) { return }
    $status = if ($Sehat) { 'up' } else { 'down' }
    try {
        $sep = if ($url.Contains('?')) { '&' } else { '?' }
        Invoke-RestMethod -Uri ($url + $sep + 'status=' + $status + '&msg=' + [uri]::EscapeDataString($Pesan)) -TimeoutSec 20 | Out-Null
    } catch { Tulis-Log ('Gagal kirim Uptime Kuma: ' + $_.Exception.Message) 'GALAT' }
}

# Parse nama berkas cadangan -> objek (Env, Tipe: db|minio, Waktu, Jenis: full|inc|''). $null bila bukan cadangan.
function Baca-NamaCadangan {
    param([string]$Nama)
    if ($Nama -match '^(prod|beta)-db-(\d{8})-(\d{6})\.dump\.age$') {
        return [pscustomobject]@{ Env = $Matches[1]; Tipe = 'db'; Jenis = ''; Nama = $Nama
            Waktu = [datetime]::ParseExact($Matches[2] + $Matches[3], 'yyyyMMddHHmmss', $null) }
    }
    if ($Nama -match '^(prod|beta)-minio-(\d{8})-(\d{6})-(full|inc)\.tar\.age$') {
        return [pscustomobject]@{ Env = $Matches[1]; Tipe = 'minio'; Jenis = $Matches[4]; Nama = $Nama
            Waktu = [datetime]::ParseExact($Matches[2] + $Matches[3], 'yyyyMMddHHmmss', $null) }
    }
    return $null
}

function Daftar-Cadangan {
    param([string]$Folder, [string]$Env)
    $hasil = @()
    $dir = Join-Path $Folder $Env
    if (-not (Test-Path $dir)) { return $hasil }
    foreach ($f in Get-ChildItem -Path $dir -Filter '*.age' -File) {
        $o = Baca-NamaCadangan $f.Name
        if ($o) { $hasil += $o }
    }
    return @($hasil | Sort-Object Waktu)
}
