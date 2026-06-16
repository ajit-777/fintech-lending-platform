import 'api_client.dart';
import '../models/user.dart';

class AuthService {
  static Future<void> register({required String email, required String phone, required String password}) async {
    final response = await ApiClient.post(
      '/auth/register',
      {'email': email, 'phone': phone, 'password': password},
      authorized: false,
    );
    await ApiClient.saveToken(response['access_token']);
  }

  static Future<void> login({required String identifier, required String password}) async {
    final response = await ApiClient.post(
      '/auth/login',
      {'identifier': identifier, 'password': password},
      authorized: false,
    );
    await ApiClient.saveToken(response['access_token']);
  }

  static Future<void> logout() => ApiClient.clearToken();

  static Future<bool> isLoggedIn() async => (await ApiClient.getToken()) != null;

  static Future<AppUser> getMe() async {
    final response = await ApiClient.get('/users/me');
    return AppUser.fromJson(response);
  }
}
