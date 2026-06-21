import 'dart:io';
import 'api_client.dart';

class NotificationService {
  /// Register device token with backend.
  /// In mock mode we send a placeholder token.
  /// When Firebase is configured, replace this with:
  ///   final token = await FirebaseMessaging.instance.getToken();
  static Future<void> registerToken() async {
    try {
      final platform = Platform.isIOS ? 'ios' : 'android';
      // Placeholder token — replace with real FCM token when Firebase is set up
      const mockToken = 'mock-fcm-token-replace-with-firebase';
      await ApiClient.post('/users/me/device-token', {
        'token': mockToken,
        'platform': platform,
      });
    } catch (_) {
      // Non-fatal — app works fine without push tokens
    }
  }

  /// Fetch recent unread push notifications from backend for in-app display.
  static Future<List<Map<String, dynamic>>> fetchRecent() async {
    try {
      final response = await ApiClient.get('/users/me/notifications') as List;
      return response.cast<Map<String, dynamic>>();
    } catch (_) {
      return [];
    }
  }
}
