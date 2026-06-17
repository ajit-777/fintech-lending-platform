import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/loan_application.dart';
import '../providers/auth_provider.dart';
import '../services/loan_service.dart';
import 'apply_loan_screen.dart';
import 'loan_detail_screen.dart';
import 'login_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<LoanApplication>> _loansFuture;

  @override
  void initState() {
    super.initState();
    _loansFuture = LoanService.listLoans();
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
        onPressed: () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => const ApplyLoanScreen()));
          _refresh();
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}
