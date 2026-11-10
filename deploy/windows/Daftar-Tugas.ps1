<#
.SYNOPSIS
  Daftarkan dua tugas Task Scheduler: tarik cadangan (03:30) dan pemeriksaan kesegaran (09:00). Jalankan sebagai Administrator.
.DESCRIPTION
  Berjalan sebagai AKUN LAYANAN khusus (bukan Administrator) yang menjadi satu-satunya pemilik izin NTFS di folder
  cadangan dan kunci SSH. Sandi akun diminta interaktif (tidak disimpan di skrip). Idempoten (menimpa tugas lama).
  Hapus: Unregister-ScheduledTask -TaskName 'VMS Tarik Cadangan' -Confirm:$false (juga 'VMS Periksa Cadangan').
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ServerHost,
    [Parameter(Mandatory)][string]$KunciSsh,
    [string]$Tujuan = 'D:\cadangan-vms',
    [string]$AkunLayanan = '.\svc-cadangan'
)
$ErrorActionPreference = 'Stop'
$skrip = Join-Path $PSScriptRoot 'Tarik-Cadangan.ps1'
$kred = Get-Credential -UserName $AkunLayanan -Message 'Sandi akun layanan cadangan'
$sandi = $kred.GetNetworkCredential().Password
$arg = '-NoProfile -ExecutionPolicy RemoteSigned -File "{0}" -ServerHost {1} -KunciSsh "{2}" -Tujuan "{3}"' -f $skrip, $ServerHost, $KunciSsh, $Tujuan
$setelan = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 6) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew
$tugas = @(
    @{ Nama = 'VMS Tarik Cadangan'; Jam = '03:30'; Tambahan = '' },
    @{ Nama = 'VMS Periksa Cadangan'; Jam = '09:00'; Tambahan = ' -HanyaPeriksa' }
)
foreach ($t in $tugas) {
    $aksi = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ($arg + $t.Tambahan)
    $pemicu = New-ScheduledTaskTrigger -Daily -At $t.Jam
    Register-ScheduledTask -TaskName $t.Nama -Action $aksi -Trigger $pemicu -Settings $setelan -User $kred.UserName -Password $sandi -RunLevel Limited -Force | Out-Null
    Write-Host "Terdaftar: $($t.Nama) pukul $($t.Jam) sebagai $($kred.UserName)"
}
$sandi = $null
Write-Host 'Uji sekarang: Start-ScheduledTask -TaskName "VMS Tarik Cadangan"; lalu baca log di' (Join-Path $Tujuan 'log')
