// Stub implementation for web platform
// QR scanner is not available on web
import 'package:flutter/material.dart';

class QRScannerScreen extends StatelessWidget {
  const QRScannerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('QR Scanner'),
      ),
      body: const Center(
        child: Text('QR Scanner not available on web platform'),
      ),
    );
  }
}
