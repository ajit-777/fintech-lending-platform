import '../services/api_client.dart';

class AgreementService {
  static Future<Map<String, dynamic>> sendOTP(String loanId) async {
    return await ApiClient.post('/loans/$loanId/agreement/send-otp', {});
  }

  static Future<Map<String, dynamic>> acceptAgreement({
    required String loanId,
    required String otp,
    required String refId,
  }) async {
    return await ApiClient.post('/loans/$loanId/agreement/accept', {
      'otp': otp,
      'ref_id': refId,
    });
  }
}
