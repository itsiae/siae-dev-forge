// Use this template for: Flutter widgets, BLoC, Riverpod, and service classes.
// Requires: flutter_test (SDK), mocktail ^1.0.0.
// Replace all {{PLACEHOLDER}} tokens before use.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:{{package_name}}/{{module_import_path}}';
import 'package:{{package_name}}/{{dep_import_path}}';

// ─── Mocks ────────────────────────────────────────────────────────────────────

class Mock{{DepClass}} extends Mock implements {{DepClass}} {}

// ─── Service / Logic Tests ────────────────────────────────────────────────────

void main() {
  late {{ClassName}} {{instanceName}};
  late Mock{{DepClass}} mock{{DepClass}};

  setUp(() {
    mock{{DepClass}} = Mock{{DepClass}}();
    {{instanceName}} = {{ClassName}}({{constructorArgs}}: mock{{DepClass}});
  });

  tearDown(() {
    reset(mock{{DepClass}});
  });

  group('{{ClassName}}.{{methodName}}', () {
    test('should {{HAPPY_PATH_DESCRIPTION}}', () async {
      // Arrange
      final input = {{HAPPY_PATH_INPUT}};
      when(() => mock{{DepClass}}.{{depMethod}}(any()))
          .thenAnswer((_) async => {{DEP_RETURN_VALUE}});

      // Act
      final result = await {{instanceName}}.{{methodName}}(input);

      // Assert
      expect(result, equals({{EXPECTED_OUTPUT}}));
      verify(() => mock{{DepClass}}.{{depMethod}}(input)).called(1);
    });

    test('should {{EDGE_CASE_1_DESCRIPTION}} when input is empty', () async {
      // Arrange
      when(() => mock{{DepClass}}.{{depMethod}}(any()))
          .thenAnswer((_) async => {{EDGE_CASE_1_DEP_RETURN}});

      // Act
      final result = await {{instanceName}}.{{methodName}}({{EDGE_CASE_1_INPUT}});

      // Assert
      expect(result, equals({{EDGE_CASE_1_EXPECTED}}));
    });

    test('should {{EDGE_CASE_2_DESCRIPTION}} at boundary', () async {
      // Arrange
      final boundaryInput = {{EDGE_CASE_2_INPUT}};

      // Act
      final result = await {{instanceName}}.{{methodName}}(boundaryInput);

      // Assert
      expect(result, isNotNull);
    });

    test('should throw {{ExceptionType}} when {{NEGATIVE_CONDITION}}', () async {
      // Arrange
      when(() => mock{{DepClass}}.{{depMethod}}(any()))
          .thenThrow({{ExceptionType}}('{{ERROR_MESSAGE}}'));

      // Act & Assert
      expect(
        () => {{instanceName}}.{{methodName}}({{INVALID_INPUT}}),
        throwsA(isA<{{ExceptionType}}>()),
      );
    });
  });

  // ─── Widget Tests ─────────────────────────────────────────────────────────

  group('{{WidgetName}} widget', () {
    testWidgets('should render {{WIDGET_HAPPY_PATH_DESCRIPTION}}',
        (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: {{WidgetName}}({{widgetProps}}),
        ),
      );

      // Act
      await tester.pump();

      // Assert
      expect(find.byType({{WidgetName}}), findsOneWidget);
      expect(find.text('{{EXPECTED_TEXT}}'), findsOneWidget);
    });

    testWidgets('should display loading indicator while fetching',
        (WidgetTester tester) async {
      // Arrange
      when(() => mock{{DepClass}}.{{depMethod}}(any()))
          .thenAnswer((_) async {
        await Future<void>.delayed(const Duration(milliseconds: 100));
        return {{DEP_RETURN_VALUE}};
      });

      await tester.pumpWidget(
        MaterialApp(home: {{WidgetName}}({{widgetProps}})),
      );

      // Act — pump without settling
      await tester.pump();

      // Assert — loading state
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // Settle and assert final state
      await tester.pumpAndSettle();
      expect(find.byType(CircularProgressIndicator), findsNothing);
    });

    testWidgets('should show error message when dep throws',
        (WidgetTester tester) async {
      // Arrange
      when(() => mock{{DepClass}}.{{depMethod}}(any()))
          .thenThrow(Exception('network error'));

      await tester.pumpWidget(
        MaterialApp(home: {{WidgetName}}({{widgetProps}})),
      );

      // Act
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('{{ERROR_TEXT}}'), findsOneWidget);
    });
  });
}
