class AppUser {
  final String id;
  final String email;
  final String phone;
  final String role;

  AppUser({required this.id, required this.email, required this.phone, required this.role});

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'],
        email: json['email'],
        phone: json['phone'],
        role: json['role'],
      );
}
