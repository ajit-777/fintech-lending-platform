class RepaymentInstallment {
  final String id;
  final String loanId;
  final int installmentNumber;
  final DateTime dueDate;
  final double emiAmount;
  final double principal;
  final double interest;
  final double outstandingPrincipal;
  final String status;
  final DateTime? paidAt;
  final double? paidAmount;

  RepaymentInstallment({
    required this.id,
    required this.loanId,
    required this.installmentNumber,
    required this.dueDate,
    required this.emiAmount,
    required this.principal,
    required this.interest,
    required this.outstandingPrincipal,
    required this.status,
    this.paidAt,
    this.paidAmount,
  });

  factory RepaymentInstallment.fromJson(Map<String, dynamic> json) => RepaymentInstallment(
        id: json['id'],
        loanId: json['loan_id'],
        installmentNumber: json['installment_number'],
        dueDate: DateTime.parse(json['due_date']),
        emiAmount: (json['emi_amount'] as num).toDouble(),
        principal: (json['principal'] as num).toDouble(),
        interest: (json['interest'] as num).toDouble(),
        outstandingPrincipal: (json['outstanding_principal'] as num).toDouble(),
        status: json['status'],
        paidAt: json['paid_at'] != null ? DateTime.parse(json['paid_at']) : null,
        paidAmount: json['paid_amount'] != null ? (json['paid_amount'] as num).toDouble() : null,
      );
}
