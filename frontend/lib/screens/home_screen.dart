import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/loan_application.dart';
import '../providers/auth_provider.dart';
import '../services/kyc_service.dart';
import '../services/loan_service.dart';
import '../services/notification_service.dart';
import 'apply_loan_screen.dart';
import 'kyc_screen.dart';
import 'loan_detail_screen.dart';
import 'login_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<LoanApplication>> _loansFuture;
  bool _kycVerified = false;

  @override
  void initState() {
    super.initState();
    _loansFuture = LoanService.listLoans();
    _checkKYC();
  }

  Future<void> _checkKYC() async {
    try {
      final kyc = await KYCService.getMyKYC();
      if (!mounted) return;
      if (kyc['kyc_status'] == 'verified') {
        setState(() => _kycVerified = true);
      } else {
        Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const KYCScreen()));
      }
    } on Exception {
      if (mounted) {
        Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const KYCScreen()));
      }
    }
  }

  Future<void> _showNotifications(BuildContext context) async {
    final notifications = await NotificationService.fetchRecent();
    if (!context.mounted) return;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.5,
        maxChildSize: 0.85,
        builder: (_, controller) => Column(
          children: [
            const SizedBox(height: 8),
            Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.grey[300], borderRadius: BorderRadius.circular(2))),
            const SizedBox(height: 12),
            const Text('Notifications', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const Divider(),
            Expanded(
              child: notifications.isEmpty
                  ? const Center(child: Text('No notifications yet', style: TextStyle(color: Colors.grey)))
                  : ListView.builder(
                      controller: controller,
                      itemCount: notifications.length,
                      itemBuilder: (_, i) {
                        final n = notifications[i];
                        return ListTile(
                          leading: Icon(_eventIcon(n['event_type'] as String), color: Colors.indigo),
                          title: Text(n['subject'] ?? n['event_type'], style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
                          subtitle: Text(n['body'], style: const TextStyle(fontSize: 12)),
                          isThreeLine: true,
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _eventIcon(String eventType) {
    switch (eventType) {
      case 'loan_approved': return Icons.check_circle_outline;
      case 'loan_rejected': return Icons.cancel_outlined;
      case 'loan_disbursed': return Icons.account_balance_wallet_outlined;
      case 'installment_paid': return Icons.receipt_long_outlined;
      case 'emi_due_reminder': return Icons.calendar_today_outlined;
      default: return Icons.notifications_outlined;
    }
  }

  void _refresh() {
    final future = LoanService.listLoans();
    setState(() => _loansFuture = future);
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'approved':
        return Colors.green;
      case 'disbursed':
        return Colors.blue;
      case 'rejected':
        return Colors.red;
      default:
        return Colors.orange;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Loans'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            tooltip: 'Notifications',
            onPressed: () => _showNotifications(context),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await context.read<AuthProvider>().logout();
              if (context.mounted) {
                Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const LoginScreen()));
              }
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => _refresh(),
        child: FutureBuilder<List<LoanApplication>>(
          future: _loansFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return Center(child: Text('Failed to load loans: ${snapshot.error}'));
            }
            final loans = snapshot.data ?? [];
            if (loans.isEmpty) {
              return const Center(child: Text('No loan applications yet. Tap + to apply.'));
            }
            return ListView.builder(
              itemCount: loans.length,
              itemBuilder: (context, index) {
                final loan = loans[index];
                return ListTile(
                  title: Text('₹${loan.amount.toStringAsFixed(0)} • ${loan.tenureMonths} months'),
                  subtitle: Text(loan.purpose),
                  trailing: Chip(
                    label: Text(loan.status.toUpperCase()),
                    backgroundColor: _statusColor(loan.status).withValues(alpha: 0.15),
                    labelStyle: TextStyle(color: _statusColor(loan.status)),
                  ),
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => LoanDetailScreen(loanId: loan.id)),
                  ),
                );
              },
            );
          },
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: !_kycVerified ? null : () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => const ApplyLoanScreen()));
          _refresh();
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}
