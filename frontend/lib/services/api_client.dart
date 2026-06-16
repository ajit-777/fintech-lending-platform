import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class ApiClient {
  // Update this to your backend's reachable address.
  // - iOS simulator: http://127.0.0.1:8000
  // - Android emulator: http://10.0.2.2:8000
  // - Physical device: http://<your-machine-lan-ip>:8000
  static const String baseUrl = 'http://10.0.2.2:8000';

  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'access_token';

  static Future<void> saveToken(String token) => _storage.write(key: _tokenKey, value: token);
  static Future<String?> getToken() => _storage.read(key: _tokenKey);
  static Future<void> clearToken() => _storage.delete(key: _tokenKey);

  static Future<Map<String, String>> _headers({bool authorized = false}) async {
    final headers = {'Content-Type': 'application/json'};
    if (authorized) {
      final token = await getToken();
      if (token != null) headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  static dynamic _decode(http.Response response) {
    final body = response.body.isNotEmpty ? jsonDecode(response.body) : null;
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body;
    }
    final detail = body is Map && body['detail'] != null ? body['detail'].toString() : 'Request failed';
    throw ApiException(response.statusCode, detail);
  }

  static Future<dynamic> get(String path, {bool authorized = true}) async {
    final response = await http.get(Uri.parse('$baseUrl$path'), headers: await _headers(authorized: authorized));
    return _decode(response);
  }

  static Future<dynamic> post(String path, Map<String, dynamic> body, {bool authorized = true}) async {
    final response = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: await _headers(authorized: authorized),
      body: jsonEncode(body),
    );
    return _decode(response);
  }

  static Future<dynamic> patch(String path, Map<String, dynamic> body, {bool authorized = true}) async {
    final response = await http.patch(
      Uri.parse('$baseUrl$path'),
      headers: await _headers(authorized: authorized),
      body: jsonEncode(body),
    );
    return _decode(response);
  }
}
