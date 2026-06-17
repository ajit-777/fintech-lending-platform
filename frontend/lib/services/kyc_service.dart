import '../services/api_client.dart';

class KYCService {
  static Future<Map<String, dynamic>> getMyKYC() async {
    return await ApiClient.get('/kyc/me');
  }

  static Future<Map<String, dynamic>> submitKYC({
    required String panNumber,
    required String dateOfBirth,
    required String addressLine1,
    String? addressLine2,
    required String city,
    required String state,
    required String pincode,
  }) async {
    return await ApiClient.post('/kyc/submit', {
      'pan_number': panNumber,
      'date_of_birth': dateOfBirth,
      'address_line1': addressLine1,
      if (addressLine2 != null && addressLine2.isNotEmpty) 'address_line2': addressLine2,
      'city': city,
      'state': state,
      'pincode': pincode,
    });
  }

  static Future<Map<String, dynamic>> verifyPAN() async {
    return await ApiClient.post('/kyc/verify-pan', {});
  }

  static Future<Map<String, dynamic>> sendAadhaarOTP(String aadhaarNumber) async {
    return await ApiClient.post('/kyc/aadhaar/send-otp', {'aadhaar_number': aadhaarNumber});
  }

  static Future<Map<String, dynamic>> verifyAadhaarOTP({
    required String otp,
    required String refId,
  }) async {
    return await ApiClient.post('/kyc/aadhaar/verify-otp', {'otp': otp, 'ref_id': refId});
  }
}
