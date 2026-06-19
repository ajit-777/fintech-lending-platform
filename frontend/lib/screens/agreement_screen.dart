import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../services/agreement_service.dart';

class AgreementScreen extends StatefulWidget {
  final String loanId;
  const AgreementScreen({super.key, required this.loanId});

  @override
  State<AgreementScreen> createState() => _AgreementScreenState();
}

class _AgreementScreenState extends State<AgreementScreen> {
  bool _loading = false;
  bool _otpSent = false;
  String? _refId;
  String? _error;
  final _otpCtrl = TextEditingController();

  @override
  void dispose() {
    _otpCtrl.dispose();
    super.dispose();
  }

  Future<void> _sendOTP() async {
    setState(() { _loading = true; _error = null; });
    try {
      final result = await AgreementService.sendOTP(widget.loanId);
      setState(() {
        _refId = result['ref_id'] as String;
        _otpSent = true;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('OTP sent to your registered mobile number')),
        );
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _acceptAgreement() async {
    if (_refId == null || _otpCtrl.text.trim().length != 6) {
      setState(() => _error = 'Enter the 6-digit OTP');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      await AgreementService.acceptAgreement(
        loanId: widget.loanId,
        otp: _otpCtrl.text.trim(),
        refId: _refId!,
      );
      if (mounted) {
        Navigator.of(context).pop(true); // return true = accepted
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Loan Agreement')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Agreement summary card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.indigo.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.indigo.shade200),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Icon(Icons.description, color: Colors.indigo.shade700),
                    const SizedBox(width: 8),
                    Text('Loan Sanction Letter & Agreement',
                        style: TextStyle(fontWeight: FontWeight.bold, color: Colors.indigo.shade800)),
                  ]),
                  const SizedBox(height: 12),
                  const Text(
                    'Your loan has been approved. Please review the agreement and accept it to proceed with disbursement.',
                    style: TextStyle(fontSize: 13, height: 1.5),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Download PDF button
            OutlinedButton.icon(
              icon: const Icon(Icons.download),
              label: const Text('View / Download Agreement PDF'),
              onPressed: () async {
                // Open in system browser — the PDF endpoint streams bytes
                final url = '${ApiClient.baseUrl}/loans/${widget.loanId}/agreement';
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('PDF available at:\n$url')),
                );
              },
            ),
            const SizedBox(height: 28),

            const Divider(),
            const SizedBox(height: 16),

            Text('Accept Agreement', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            const Text(
              'To confirm your acceptance, we will send a one-time password (OTP) to your registered mobile number.',
              style: TextStyle(fontSize: 13, color: Colors.black54, height: 1.5),
            ),
            const SizedBox(height: 16),

            if (!_otpSent) ...[
              ElevatedButton(
                onPressed: _loading ? null : _sendOTP,
                child: _loading
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Send OTP'),
              ),
            ] else ...[
              TextField(
                controller: _otpCtrl,
                keyboardType: TextInputType.number,
                maxLength: 6,
                decoration: const InputDecoration(
                  labelText: 'Enter OTP',
                  border: OutlineInputBorder(),
                  counterText: '',
                ),
              ),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: _loading ? null : _acceptAgreement,
                style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                child: _loading
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('I Accept the Agreement', style: TextStyle(color: Colors.white)),
              ),
              TextButton(
                onPressed: _loading ? null : _sendOTP,
                child: const Text('Resend OTP'),
              ),
            ],

            if (_error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Text(_error!, style: TextStyle(color: Colors.red.shade800, fontSize: 13)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
