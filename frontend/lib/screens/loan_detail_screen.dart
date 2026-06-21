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
    final future = LoanService.getLoan(widget.loanId);
    setState(() { _loanFuture = future; });
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

                if (loan.status == 'disbursed') ...[
                  const SizedBox(height: 4),
                  OutlinedButton.icon(
                    onPressed: () => _showForeclosureFlow(loan.id),
                    icon: const Icon(Icons.lock_outline, size: 18),
                    label: const Text('Foreclose Loan'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red.shade700,
                      side: BorderSide(color: Colors.red.shade300),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],

                if (loan.status == 'approved' || loan.status == 'disbursed' || loan.status == 'closed') ...[
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
                        children: installments.map((i) => _installmentCard(i, loan.id, loan.status)).toList(),
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

  Widget _installmentCard(RepaymentInstallment i, String loanId, String loanStatus) {
    final dueDateStr = DateFormat('dd MMM yyyy').format(i.dueDate);
    final isPaid = i.status == 'paid';
    final isOverdue = i.status == 'overdue';
    final canPay = loanStatus == 'disbursed' && !isPaid;
    final totalDue = i.emiAmount + (i.penaltyAmount ?? 0);

    Color statusColor = isPaid ? Colors.green : (isOverdue ? Colors.red : Colors.orange);

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'EMI #${i.installmentNumber} — ₹${i.emiAmount.toStringAsFixed(0)}',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Due: $dueDateStr  •  P: ₹${i.principal.toStringAsFixed(0)}  I: ₹${i.interest.toStringAsFixed(0)}',
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                  if ((i.penaltyAmount ?? 0) > 0)
                    Text(
                      'Penalty: ₹${(i.penaltyAmount ?? 0).toStringAsFixed(0)}  •  Total: ₹${totalDue.toStringAsFixed(0)}',
                      style: TextStyle(fontSize: 12, color: Colors.red.shade700),
                    ),
                  if (isPaid && i.paidAt != null)
                    Text(
                      'Paid on ${DateFormat('dd MMM yyyy').format(i.paidAt!)}',
                      style: TextStyle(fontSize: 12, color: Colors.green.shade700),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            if (canPay)
              ElevatedButton(
                onPressed: () => _confirmPayment(loanId, i, totalDue),
                style: ElevatedButton.styleFrom(
                  backgroundColor: isOverdue ? Colors.red : Colors.green,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
                child: const Text('Pay', style: TextStyle(color: Colors.white)),
              )
            else
              Chip(
                label: Text(i.status.toUpperCase(), style: const TextStyle(fontSize: 11)),
                backgroundColor: statusColor.withValues(alpha: 0.15),
                labelStyle: TextStyle(color: statusColor),
                padding: EdgeInsets.zero,
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmPayment(String loanId, RepaymentInstallment installment, double totalDue) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text('Pay EMI #${installment.installmentNumber}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _dialogRow('EMI Amount', '₹${installment.emiAmount.toStringAsFixed(2)}'),
            if ((installment.penaltyAmount ?? 0) > 0)
              _dialogRow('Late Penalty', '₹${(installment.penaltyAmount ?? 0).toStringAsFixed(2)}'),
            const Divider(),
            _dialogRow('Total Payable', '₹${totalDue.toStringAsFixed(2)}'),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Confirm Payment')),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    try {
      await LoanService.payInstallment(loanId, installment.id);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('EMI #${installment.installmentNumber} paid successfully'),
          backgroundColor: Colors.green,
        ),
      );
      _reload();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Payment failed: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _showForeclosureFlow(String loanId) async {
    // Step 1: fetch quote
    Map<String, dynamic>? quote;
    try {
      quote = await LoanService.getForeclosureQuote(loanId);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not fetch foreclosure quote: $e'), backgroundColor: Colors.red),
      );
      return;
    }

    if (!mounted) return;

    // Step 2: show quote and confirm
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Foreclose Loan'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'You are about to pay off your entire outstanding loan balance early.',
              style: TextStyle(fontSize: 13, color: Colors.grey),
            ),
            const SizedBox(height: 16),
            _dialogRow('Installments Remaining', '${quote!['installments_remaining']}'),
            _dialogRow('Outstanding Principal', '₹${(quote['outstanding_principal'] as num).toStringAsFixed(2)}'),
            _dialogRow('Early Closure Fee (${quote['early_closure_fee_pct']}%)', '₹${(quote['closure_fee'] as num).toStringAsFixed(2)}'),
            const Divider(height: 20),
            _dialogRow('Total Payable', '₹${(quote['total_payable'] as num).toStringAsFixed(2)}'),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.orange.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.orange.shade200),
              ),
              child: const Text(
                'This action cannot be undone. All remaining installments will be marked as settled.',
                style: TextStyle(fontSize: 12),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red.shade700),
            child: const Text('Confirm Foreclosure', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    // Step 3: execute
    try {
      await LoanService.forecloseLoan(loanId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Loan foreclosed successfully'), backgroundColor: Colors.green),
      );
      _reload();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Foreclosure failed: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Widget _dialogRow(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(color: Colors.grey)),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
      );

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
