import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/loan_application.dart';
import '../models/repayment_installment.dart';
import '../services/loan_service.dart';

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
    _loanFuture = LoanService.getLoan(widget.loanId);
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
                const SizedBox(height: 24),
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
