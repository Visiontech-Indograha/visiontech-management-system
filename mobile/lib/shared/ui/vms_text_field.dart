import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Kolom teks standar proyek: batas panjang wajib (sama dengan batas API), tanpa penghitung bawaan.
class VmsTextField extends StatelessWidget {
  const VmsTextField({
    super.key,
    required this.maxLength,
    this.controller,
    this.decoration,
    this.enabled,
    this.readOnly = false,
    this.autofocus = false,
    this.maxLines = 1,
    this.keyboardType,
    this.textInputAction,
    this.onChanged,
    this.onSubmitted,
  });

  final int maxLength;
  final TextEditingController? controller;
  final InputDecoration? decoration;
  final bool? enabled;
  final bool readOnly;
  final bool autofocus;
  final int? maxLines;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;

  @override
  Widget build(BuildContext context) => TextField(
    controller: controller,
    decoration: decoration,
    enabled: enabled,
    readOnly: readOnly,
    autofocus: autofocus,
    maxLines: maxLines,
    keyboardType: keyboardType,
    textInputAction: textInputAction,
    onChanged: onChanged,
    onSubmitted: onSubmitted,
    inputFormatters: [LengthLimitingTextInputFormatter(maxLength)],
  );
}
