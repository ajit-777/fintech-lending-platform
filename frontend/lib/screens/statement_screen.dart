import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_pdfview/flutter_pdfview.dart';
import 'package:path_provider/path_provider.dart';
import '../services/api_client.dart';

class StatementScreen extends StatefulWidget {
  final String loanId;
  final String loanRef;
  const StatementScreen({super.key, required this.loanId, required this.loanRef});

  @override
  State<StatementScreen> createState() => _StatementScreenState();
}

class _StatementScreenState extends State<StatementScreen> {
  String? _pdfPath;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPdf();
  }

  Future<void> _loadPdf() async {
    try {
      final bytes = await ApiClient.getBytes('/loans/${widget.loanId}/statement.pdf');
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/statement_${widget.loanRef}.pdf');
      await file.writeAsBytes(bytes);
      if (mounted) setState(() => _pdfPath = file.path);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Statement — ${widget.loanRef}')),
      body: _error != null
          ? Center(child: Text('Failed to load statement: $_error'))
          : _pdfPath == null
              ? const Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 12),
                      Text('Generating statement…'),
                    ],
                  ),
                )
              : PDFView(filePath: _pdfPath!),
    );
  }
}
