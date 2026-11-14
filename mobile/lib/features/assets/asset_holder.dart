/// Pemegang aset yang aman untuk penerima eksternal: `employee_id` boleh null
/// dan `employee_name` berisi nama penerima (bukan karyawan).
String assetHolderName(Map<String, dynamic> row) {
  final nama = row['employee_name'];
  if (nama is String && nama.trim().isNotEmpty) return nama.trim();
  return 'Penerima tanpa nama';
}

/// Penerima eksternal = tidak punya `employee_id` (bukan karyawan).
bool isExternalHolder(Map<String, dynamic> row) => row['employee_id'] == null;

/// Label awam untuk satu baris pemegang, mis. "Budi (penerima luar)".
String assetHolderLabel(Map<String, dynamic> row) {
  final nama = assetHolderName(row);
  return isExternalHolder(row) ? '$nama (penerima luar)' : nama;
}
