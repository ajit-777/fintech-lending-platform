import 'api_client.dart';
import '../models/loan_application.dart';
import '../models/repayment_installment.dart';

class LoanService {
  static Future<LoanApplication> createLoan({
    required double amount,
    required int tenureMonths,
    required String purpose,
    required int cibilScore,
    required double monthlyIncome,
    required String bankAccountNumber,
    required String ifscCode,
    String? notes,
  }) async {
    final response = await ApiClient.post('/loans', {
      'amount': amount,
      'tenure_months': tenureMonths,
      'purpose': purpose,
      'cibil_score': cibilScore,
      'monthly_income': monthlyIncome,
      'bank_account_number': bankAccountNumber,
      'ifsc_code': ifscCode,
      if (notes != null) 'notes': notes,
    });
    return LoanApplication.fromJson(response);
  }

  static Future<List<LoanApplication>> listLoans() async {
    final response = await ApiClient.get('/loans') as List;
    return response.map((e) => LoanApplication.fromJson(e)).toList();
  }

  static Future<LoanApplication> getLoan(String loanId) async {
    final response = await ApiClient.get('/loans/$loanId');
    return LoanApplication.fromJson(response);
  }

  static Future<List<RepaymentInstallment>> getRepaymentSchedule(String loanId) async {
    final response = await ApiClient.get('/loans/$loanId/repayments') as List;
    return response.map((e) => RepaymentInstallment.fromJson(e)).toList();
  }

  static Future<RepaymentInstallment> payInstallment(String loanId, String installmentId) async {
    final response = await ApiClient.post('/loans/$loanId/repayments/$installmentId/pay', {});
    return RepaymentInstallment.fromJson(response);
  }
}
