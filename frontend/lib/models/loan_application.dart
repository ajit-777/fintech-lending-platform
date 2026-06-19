class LoanApplication {
  final String id;
  final String userId;
  final double amount;
  final int tenureMonths;
  final String purpose;
  final String loanType;
  final int cibilScore;
  final double monthlyIncome;
  final double annualInterestRate;
  final double processingFee;
  final double earlyClosureFeePct;
  final double latePaymentPenaltyPct;
  final String status;
  final String? rejectionReason;
  final DateTime? reviewedAt;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;
  final bool? bankAccountVerified;
  final String? bankAccountHolderName;

  LoanApplication({
    required this.id,
    required this.userId,
    required this.amount,
    required this.tenureMonths,
    required this.purpose,
    required this.loanType,
    required this.cibilScore,
    required this.monthlyIncome,
    required this.annualInterestRate,
    required this.processingFee,
    required this.earlyClosureFeePct,
    required this.latePaymentPenaltyPct,
    required this.status,
    this.rejectionReason,
    this.reviewedAt,
    this.notes,
    required this.createdAt,
    required this.updatedAt,
    this.bankAccountVerified,
    this.bankAccountHolderName,
  });

  factory LoanApplication.fromJson(Map<String, dynamic> json) => LoanApplication(
        id: json['id'],
        userId: json['user_id'],
        amount: (json['amount'] as num).toDouble(),
        tenureMonths: json['tenure_months'],
        purpose: json['purpose'],
        loanType: json['loan_type'],
        cibilScore: json['cibil_score'],
        monthlyIncome: (json['monthly_income'] as num).toDouble(),
        annualInterestRate: (json['annual_interest_rate'] as num).toDouble(),
        processingFee: (json['processing_fee'] as num).toDouble(),
        earlyClosureFeePct: (json['early_closure_fee_pct'] as num).toDouble(),
        latePaymentPenaltyPct: (json['late_payment_penalty_pct'] as num).toDouble(),
        status: json['status'],
        rejectionReason: json['rejection_reason'],
        reviewedAt: json['reviewed_at'] != null ? DateTime.parse(json['reviewed_at']) : null,
        notes: json['notes'],
        createdAt: DateTime.parse(json['created_at']),
        updatedAt: DateTime.parse(json['updated_at']),
        bankAccountVerified: json['bank_account_verified'] as bool?,
        bankAccountHolderName: json['bank_account_holder_name'] as String?,
      );
}
