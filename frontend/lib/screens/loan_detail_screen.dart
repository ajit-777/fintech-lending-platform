import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/loan_application.dart';
import '../models/repayment_installment.dart';
import '../services/loan_service.dart';
import 'agreement_screen.dart';

class LoanDetailScreen extends StatefulWidget {
  final String loanId;
  const LoanDetailScreen({super.key, required this.loanId});

  @override
  State<LoanDetailScreen> createState() => _LoanDetailScreenState();
}

class _LoanDetailScreenState extends State<LoanDetailScreen> {
  late Future<LoanApplication> _loanFuture;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    setState(() => _loanFuture = LoanService.getLoan(widget.loanId));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Loan Details')),
      body: FutureBuilder<LoanApplication>(
        future: _loanFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Failed to load: ${snapshot.error}'));
          }
          final loan = snapshot.data!;
          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _infoRow('Amount', '₹${loan.amount.toStringAsFixed(0)}'),
                _infoRow('Tenure', '${loan.tenureMonths} months'),
                _infoRow('Purpose', loan.purpose),
                _infoRow('Status', loan.status.toUpperCase()),
                _infoRow('Interest Rate', '${loan.annualInterestRate}% p.a.'),
                _infoRow('Processing Fee', '₹${loan.processingFee.toStringAsFixed(0)}'),
                if (loan.rejectionReason != null) _infoRow('Reason', loan.rejectionReason!),
                _infoRow('Bank Account Verified', loan.bankAccountVerified == true ? '✓ Yes' : '✗ Pending review'),
                _infoRow('Agreement', loan.agreementAccepted == true ? '✓ Accepted' : '— Pending'),
                const SizedBox(height: 16),

                // Agreement acceptance banner
                if (loan.status == 'approved' && loan.agreementAccepted != true)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade50,
                      border: Border.all(color: Colors.orange.shade300),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Action Required', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.orange.shade800)),
                        const SizedBox(height: 4),
                        const Text('Please accept the loan agreement before disbursement can proceed.', style: TextStyle(fontSize: 13)),
                        const SizedBox(height: 10),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: () async {
                              final accepted = await Navigator.push<bool>(
                                context,
                                MaterialPageRoute(builder: (_) => AgreementScreen(loanId: loan.id)),
                              );
                              if (accepted == true) _reload();
                            },
                            style: ElevatedButton.styleFrom(backgroundColor: Colors.orange.shade700),
                            child: const Text('Review & Accept Agreement', style: TextStyle(color: Colors.white)),
                          ),
                        ),
                      ],
                    ),
                  ),

                if (loan.status == 'approved') ...[
                  const Text('Repayment Schedule', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  FutureBuilder<List<RepaymentInstallment>>(
                    future: LoanService.getRepaymentSchedule(loan.id),
                    builder: (context, schedSnapshot) {
                      if (schedSnapshot.connectionState == ConnectionState.waiting) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (schedSnapshot.hasError) {
                        return Text('Failed to load schedule: ${schedSnapshot.error}');
                      }
                      final installments = schedSnapshot.data ?? [];
                      return Column(
                        children: installments.map((i) {
                          final dueDateStr = DateFormat('dd MMM yyyy').format(i.dueDate);
                          return Card(
                            child: ListTile(
                              title: Text('Installment #${i.installmentNumber} — ₹${i.emiAmount.toStringAsFixed(0)}'),
                              subtitle: Text('Due: $dueDateStr  •  Principal: ₹${i.principal.toStringAsFixed(0)}  •  Interest: ₹${i.interest.toStringAsFixed(0)}'),
                              trailing: Chip(
                                label: Text(i.status.toUpperCase()),
                                backgroundColor: i.status == 'paid' ? Colors.green.withValues(alpha: 0.15) : Colors.grey.withValues(alpha: 0.15),
                              ),
                            ),
                          );
                        }).toList(),
                      );
                    },
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _infoRow(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(color: Colors.grey)),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
      );
}
