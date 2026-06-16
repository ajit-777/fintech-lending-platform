import 'package:flutter/foundation.dart';
import '../models/user.dart';
import '../services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  AppUser? _user;
  bool _loading = false;

  AppUser? get user => _user;
  bool get isAuthenticated => _user != null;
  bool get loading => _loading;

  Future<void> tryAutoLogin() async {
    if (!await AuthService.isLoggedIn()) return;
    try {
      _user = await AuthService.getMe();
      notifyListeners();
    } catch (_) {
      await AuthService.logout();
    }
  }

  Future<void> register({required String email, required String phone, required String password}) async {
    _loading = true;
    notifyListeners();
    try {
      await AuthService.register(email: email, phone: phone, password: password);
      _user = await AuthService.getMe();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> login({required String identifier, required String password}) async {
    _loading = true;
    notifyListeners();
    try {
      await AuthService.login(identifier: identifier, password: password);
      _user = await AuthService.getMe();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await AuthService.logout();
    _user = null;
    notifyListeners();
  }
}
