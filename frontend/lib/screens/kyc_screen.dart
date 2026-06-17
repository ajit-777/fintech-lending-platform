import 'package:flutter/material.dart';
import '../services/kyc_service.dart';
import 'home_screen.dart';

class KYCScreen extends StatefulWidget {
  const KYCScreen({super.key});

  @override
  State<KYCScreen> createState() => _KYCScreenState();
}

class _KYCScreenState extends State<KYCScreen> {
  // Step 0 = details form, 1 = PAN verify, 2 = Aadhaar OTP, 3 = done
  int _step = 0;
  bool _loading = false;
  String? _error;

  // Step 0 controllers
  final _panCtrl = TextEditingController();
  final _dobCtrl = TextEditingController();
  final _addr1Ctrl = TextEditingController();
  final _addr2Ctrl = TextEditingController();
  final _cityCtrl = TextEditingController();
  final _stateCtrl = TextEditingController();
  final _pincodeCtrl = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  // Step 2 controllers
  final _aadhaarCtrl = TextEditingController();
  final _otpCtrl = TextEditingController();
  String? _aadhaarRefId;

  @override
  void dispose() {
    for (final c in [_panCtrl, _dobCtrl, _addr1Ctrl, _addr2Ctrl, _cityCtrl, _stateCtrl, _pincodeCtrl, _aadhaarCtrl, _otpCtrl]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submitDetails() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });
    try {
      await KYCService.submitKYC(
        panNumber: _panCtrl.text.trim().toUpperCase(),
        dateOfBirth: _dobCtrl.text.trim(),
        addressLine1: _addr1Ctrl.text.trim(),
        addressLine2: _addr2Ctrl.text.trim(),
        city: _cityCtrl.text.trim(),
        state: _stateCtrl.text.trim(),
        pincode: _pincodeCtrl.text.trim(),
      );
      setState(() => _step = 1);
    } on Exception catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _verifyPAN() async {
    setState(() { _loading = true; _error = null; });
    try {
      await KYCService.verifyPAN();
      setState(() => _step = 2);
    } on Exception catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _sendAadhaarOTP() async {
    if (_aadhaarCtrl.text.trim().length != 12) {
      setState(() => _error = 'Aadhaar number must be 12 digits');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final result = await KYCService.sendAadhaarOTP(_aadhaarCtrl.text.trim());
      setState(() => _aadhaarRefId = result['ref_id'] as String?);
    } on Exception catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _confirmAadhaarOTP() async {
    if (_aadhaarRefId == null) {
      setState(() => _error = 'Request OTP first');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      await KYCService.verifyAadhaarOTP(otp: _otpCtrl.text.trim(), refId: _aadhaarRefId!);
      setState(() => _step = 3);
    } on Exception catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('KYC Verification')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: _buildStep(),
        ),
      ),
    );
  }

  Widget _buildStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _StepIndicator(current: _step),
        const SizedBox(height: 24),
        if (_error != null)
          Container(
            padding: const EdgeInsets.all(12),
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(
              color: Colors.red.shade50,
              border: Border.all(color: Colors.red.shade200),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(_error!, style: TextStyle(color: Colors.red.shade800)),
          ),
        if (_step == 0) _buildDetailsForm(),
        if (_step == 1) _buildPANVerify(),
        if (_step == 2) _buildAadhaarVerify(),
        if (_step == 3) _buildDone(),
      ],
    );
  }

  Widget _buildDetailsForm() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Personal Details', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          _field(_panCtrl, 'PAN Number', hint: 'ABCDE1234F',
            validator: (v) {
              if (v == null || v.isEmpty) return 'Required';
              final pan = v.trim().toUpperCase();
              final re = RegExp(r'^[A-Z]{5}[0-9]{4}[A-Z]$');
              if (!re.hasMatch(pan)) return 'Invalid PAN format (e.g. ABCDE1234F)';
              return null;
            },
          ),
          const SizedBox(height: 12),
          _field(_dobCtrl, 'Date of Birth', hint: 'YYYY-MM-DD',
            validator: (v) {
              if (v == null || v.isEmpty) return 'Required';
              final re = RegExp(r'^\d{4}-\d{2}-\d{2}$');
              if (!re.hasMatch(v.trim())) return 'Format must be YYYY-MM-DD';
              return null;
            },
          ),
          const SizedBox(height: 20),
          const Text('Address', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          _field(_addr1Ctrl, 'Address Line 1', validator: (v) => v == null || v.isEmpty ? 'Required' : null),
          const SizedBox(height: 12),
          _field(_addr2Ctrl, 'Address Line 2 (optional)'),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: _field(_cityCtrl, 'City', validator: (v) => v == null || v.isEmpty ? 'Required' : null)),
            const SizedBox(width: 12),
            Expanded(child: _field(_pincodeCtrl, 'Pincode',
              keyboardType: TextInputType.number,
              validator: (v) {
                if (v == null || v.isEmpty) return 'Required';
                if (!RegExp(r'^\d{6}$').hasMatch(v.trim())) return '6 digits';
                return null;
              },
            )),
          ]),
          const SizedBox(height: 12),
          _field(_stateCtrl, 'State', validator: (v) => v == null || v.isEmpty ? 'Required' : null),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _loading ? null : _submitDetails,
              child: _loading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Save & Continue'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPANVerify() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('PAN Verification', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        const Text('We will verify your PAN with the Income Tax Department.'),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: _loading ? null : _verifyPAN,
            child: _loading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Verify PAN'),
          ),
        ),
      ],
    );
  }

  Widget _buildAadhaarVerify() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Aadhaar Verification', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        TextFormField(
          controller: _aadhaarCtrl,
          keyboardType: TextInputType.number,
          maxLength: 12,
          decoration: const InputDecoration(labelText: 'Aadhaar Number (12 digits)', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: _loading ? null : _sendAadhaarOTP,
            child: const Text('Send OTP to Aadhaar-linked mobile'),
          ),
        ),
        if (_aadhaarRefId != null) ...[
          const SizedBox(height: 20),
          TextFormField(
            controller: _otpCtrl,
            keyboardType: TextInputType.number,
            maxLength: 6,
            decoration: const InputDecoration(labelText: 'Enter OTP', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _loading ? null : _confirmAadhaarOTP,
              child: _loading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Verify OTP'),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildDone() {
    return Column(
      children: [
        const Icon(Icons.verified, color: Colors.green, size: 72),
        const SizedBox(height: 16),
        const Text('KYC Verified!', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        const Text('You can now apply for a loan.', textAlign: TextAlign.center),
        const SizedBox(height: 32),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: () => Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const HomeScreen())),
            child: const Text('Go to Dashboard'),
          ),
        ),
      ],
    );
  }

  Widget _field(TextEditingController ctrl, String label, {
    String? hint,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: ctrl,
      keyboardType: keyboardType,
      decoration: InputDecoration(labelText: label, hintText: hint, border: const OutlineInputBorder()),
      validator: validator,
    );
  }
}

class _StepIndicator extends StatelessWidget {
  final int current;
  const _StepIndicator({required this.current});

  @override
  Widget build(BuildContext context) {
    final steps = ['Details', 'PAN', 'Aadhaar', 'Done'];
    return Row(
      children: steps.asMap().entries.map((e) {
        final idx = e.key;
        final label = e.value;
        final done = idx < current;
        final active = idx == current;
        return Expanded(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  children: [
                    CircleAvatar(
                      radius: 16,
                      backgroundColor: done ? Colors.green : active ? Theme.of(context).colorScheme.primary : Colors.grey.shade300,
                      child: done
                          ? const Icon(Icons.check, color: Colors.white, size: 16)
                          : Text('${idx + 1}', style: TextStyle(color: active ? Colors.white : Colors.grey.shade700, fontWeight: FontWeight.bold)),
                    ),
                    const SizedBox(height: 4),
                    Text(label, style: TextStyle(fontSize: 11, color: active ? Theme.of(context).colorScheme.primary : Colors.grey)),
                  ],
                ),
              ),
              if (idx < steps.length - 1)
                Container(width: 24, height: 2, color: done ? Colors.green : Colors.grey.shade300),
            ],
          ),
        );
      }).toList(),
    );
  }
}
