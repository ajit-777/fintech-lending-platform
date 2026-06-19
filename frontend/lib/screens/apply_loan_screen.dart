import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../services/loan_service.dart';
import 'kyc_screen.dart';

class ApplyLoanScreen extends StatefulWidget {
  const ApplyLoanScreen({super.key});

  @override
  State<ApplyLoanScreen> createState() => _ApplyLoanScreenState();
}

class _ApplyLoanScreenState extends State<ApplyLoanScreen> {
  final _amountController = TextEditingController();
  final _tenureController = TextEditingController();
  final _purposeController = TextEditingController();
  final _cibilController = TextEditingController();
  final _incomeController = TextEditingController();
  final _bankAccountController = TextEditingController();
  final _ifscController = TextEditingController();
  bool _submitting = false;
  String? _error;

  Future<void> _submit() async {
    setState(() {
      _error = null;
      _submitting = true;
    });
    try {
      final loan = await LoanService.createLoan(
        amount: double.parse(_amountController.text),
        tenureMonths: int.parse(_tenureController.text),
        purpose: _purposeController.text.trim(),
        cibilScore: int.parse(_cibilController.text),
        monthlyIncome: double.parse(_incomeController.text),
        bankAccountNumber: _bankAccountController.text.trim(),
        ifscCode: _ifscController.text.trim().toUpperCase(),
      );
      if (mounted) {
        final bankMsg = loan.bankAccountVerified == true
            ? 'Bank account verified ✓'
            : 'Bank account name mismatch — admin review required';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Application submitted — ${loan.status.toUpperCase()}. $bankMsg'),
            duration: const Duration(seconds: 4),
          ),
        );
        Navigator.pop(context);
      }
    } on ApiException catch (e) {
      if (e.statusCode == 403 && e.message.contains('KYC') && mounted) {
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const KYCScreen()));
        return;
      }
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = 'Please check your inputs and try again.');
    } finally {
      setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Apply for Loan')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _amountController,
              decoration: const InputDecoration(labelText: 'Loan Amount (INR)'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _tenureController,
              decoration: const InputDecoration(labelText: 'Tenure (months)'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _purposeController,
              decoration: const InputDecoration(labelText: 'Purpose'),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _cibilController,
              decoration: const InputDecoration(labelText: 'CIBIL Score (300–900)'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _incomeController,
              decoration: const InputDecoration(labelText: 'Monthly Income (INR)'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 24),
            const Divider(),
            const SizedBox(height: 8),
            Text(
              'Bank Account for Disbursement',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(color: Colors.grey[700]),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _bankAccountController,
              decoration: const InputDecoration(labelText: 'Bank Account Number'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _ifscController,
              decoration: const InputDecoration(
                labelText: 'IFSC Code',
                hintText: 'e.g. SBIN0001234',
              ),
              textCapitalization: TextCapitalization.characters,
            ),
            const SizedBox(height: 24),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            ElevatedButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting ? const CircularProgressIndicator() : const Text('Submit Application'),
            ),
          ],
        ),
      ),
    );
  }
}
