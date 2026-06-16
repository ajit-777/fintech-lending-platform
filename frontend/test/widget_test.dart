import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/main.dart';

void main() {
  testWidgets('App starts and shows splash screen', (WidgetTester tester) async {
    await tester.pumpWidget(const FintechApp());
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
