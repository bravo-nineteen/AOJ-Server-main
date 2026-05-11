import 'package:flutter/material.dart';

// ─── THEME EXTENSION ──────────────────────────────────────────────────────────

class AppThemeExtension extends ThemeExtension<AppThemeExtension> {
  const AppThemeExtension({
    required this.teamName,
    required this.teamNameJa,
    required this.desktopBackground,
    required this.taskbarColor,
    required this.taskbarBorderColor,
    required this.iconGlowColor,
    required this.accentColor,
    required this.markerColorA,
    required this.markerColorB,
    required this.objectiveColor,
    required this.startButtonColor,
  });

  final String teamName;
  final String teamNameJa;
  final Color desktopBackground;
  final Color taskbarColor;
  final Color taskbarBorderColor;
  final Color iconGlowColor;
  final Color accentColor;
  final Color markerColorA;
  final Color markerColorB;
  final Color objectiveColor;
  final Color startButtonColor;

  @override
  AppThemeExtension copyWith({
    String? teamName,
    String? teamNameJa,
    Color? desktopBackground,
    Color? taskbarColor,
    Color? taskbarBorderColor,
    Color? iconGlowColor,
    Color? accentColor,
    Color? markerColorA,
    Color? markerColorB,
    Color? objectiveColor,
    Color? startButtonColor,
  }) {
    return AppThemeExtension(
      teamName: teamName ?? this.teamName,
      teamNameJa: teamNameJa ?? this.teamNameJa,
      desktopBackground: desktopBackground ?? this.desktopBackground,
      taskbarColor: taskbarColor ?? this.taskbarColor,
      taskbarBorderColor: taskbarBorderColor ?? this.taskbarBorderColor,
      iconGlowColor: iconGlowColor ?? this.iconGlowColor,
      accentColor: accentColor ?? this.accentColor,
      markerColorA: markerColorA ?? this.markerColorA,
      markerColorB: markerColorB ?? this.markerColorB,
      objectiveColor: objectiveColor ?? this.objectiveColor,
      startButtonColor: startButtonColor ?? this.startButtonColor,
    );
  }

  @override
  AppThemeExtension lerp(AppThemeExtension? other, double t) {
    if (other == null) return this;
    return AppThemeExtension(
      teamName: t < 0.5 ? teamName : other.teamName,
      teamNameJa: t < 0.5 ? teamNameJa : other.teamNameJa,
      desktopBackground:
          Color.lerp(desktopBackground, other.desktopBackground, t)!,
      taskbarColor: Color.lerp(taskbarColor, other.taskbarColor, t)!,
      taskbarBorderColor:
          Color.lerp(taskbarBorderColor, other.taskbarBorderColor, t)!,
      iconGlowColor: Color.lerp(iconGlowColor, other.iconGlowColor, t)!,
      accentColor: Color.lerp(accentColor, other.accentColor, t)!,
      markerColorA: Color.lerp(markerColorA, other.markerColorA, t)!,
      markerColorB: Color.lerp(markerColorB, other.markerColorB, t)!,
      objectiveColor: Color.lerp(objectiveColor, other.objectiveColor, t)!,
      startButtonColor:
          Color.lerp(startButtonColor, other.startButtonColor, t)!,
    );
  }
}

// ─── THEMES ───────────────────────────────────────────────────────────────────

class AppThemes {
  // Task Force Onyx — military olive/dark green
  static ThemeData get onyxTheme => ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF1A2B1A),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF6B8F47),
          secondary: Color(0xFFD4A017),
          surface: Color(0xFF243524),
          onPrimary: Colors.white,
          onSecondary: Colors.black,
          onSurface: Color(0xFFCFE8C0),
          error: Color(0xFFFF6B35),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0F1F0F),
          foregroundColor: Color(0xFF8FB860),
          elevation: 0,
          titleTextStyle: TextStyle(
            color: Color(0xFF8FB860),
            fontSize: 16,
            fontWeight: FontWeight.bold,
            letterSpacing: 2,
          ),
        ),
        cardTheme: const CardThemeData(
          color: Color(0xFF1E2E1E),
          elevation: 4,
          margin: EdgeInsets.all(4),
        ),
        dialogTheme: const DialogThemeData(
          backgroundColor: Color(0xFF182818),
          titleTextStyle: TextStyle(
            color: Color(0xFF8FB860),
            fontSize: 18,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.5,
          ),
        ),
        textTheme: const TextTheme(
          bodyLarge: TextStyle(color: Color(0xFFCFE8C0)),
          bodyMedium: TextStyle(color: Color(0xFFB0C890)),
          bodySmall: TextStyle(color: Color(0xFF8FA870)),
          titleLarge: TextStyle(
              color: Color(0xFF8FB860), fontWeight: FontWeight.bold),
          titleMedium: TextStyle(
              color: Color(0xFF8FB860), letterSpacing: 1.2),
          labelLarge: TextStyle(
              color: Color(0xFFD4A017), letterSpacing: 2),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF3D5C2E),
            foregroundColor: const Color(0xFFCFE8C0),
            side: const BorderSide(color: Color(0xFF6B8F47)),
          ),
        ),
        inputDecorationTheme: const InputDecorationTheme(
          filled: true,
          fillColor: Color(0xFF1A2B1A),
          border: OutlineInputBorder(
            borderSide: BorderSide(color: Color(0xFF4A6741)),
          ),
          enabledBorder: OutlineInputBorder(
            borderSide: BorderSide(color: Color(0xFF4A6741)),
          ),
          focusedBorder: OutlineInputBorder(
            borderSide: BorderSide(color: Color(0xFF8FB860), width: 2),
          ),
          labelStyle: TextStyle(color: Color(0xFF8FA870)),
          hintStyle: TextStyle(color: Color(0xFF4A6741)),
        ),
        iconTheme: const IconThemeData(color: Color(0xFF6B8F47), size: 28),
        dividerColor: const Color(0xFF3D5C2E),
        listTileTheme: const ListTileThemeData(
          tileColor: Color(0xFF1E2E1E),
          textColor: Color(0xFFCFE8C0),
          iconColor: Color(0xFF6B8F47),
        ),
        extensions: [
          const AppThemeExtension(
            teamName: 'Task Force Onyx',
            teamNameJa: 'タスクフォース・オニキス',
            desktopBackground: Color(0xFF0F1A0F),
            taskbarColor: Color(0xFF0A140A),
            taskbarBorderColor: Color(0xFF4A6741),
            iconGlowColor: Color(0xFF6B8F47),
            accentColor: Color(0xFFD4A017),
            markerColorA: Color(0xFF4CAF50),
            markerColorB: Color(0xFFFF9800),
            objectiveColor: Color(0xFFFFEB3B),
            startButtonColor: Color(0xFF2D4A1E),
          ),
        ],
      );

  // Black Talon — dark charcoal with crimson/silver
  static ThemeData get blackTalonTheme => ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0D0D12),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFC41E3A),
          secondary: Color(0xFF8B8B9A),
          surface: Color(0xFF1A1A22),
          onPrimary: Colors.white,
          onSecondary: Colors.white,
          onSurface: Color(0xFFD0D0E0),
          error: Color(0xFFFF4444),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF080810),
          foregroundColor: Color(0xFFC41E3A),
          elevation: 0,
          titleTextStyle: TextStyle(
            color: Color(0xFFC41E3A),
            fontSize: 16,
            fontWeight: FontWeight.bold,
            letterSpacing: 2,
          ),
        ),
        cardTheme: const CardThemeData(
          color: Color(0xFF14141C),
          elevation: 4,
          margin: EdgeInsets.all(4),
        ),
        dialogTheme: const DialogThemeData(
          backgroundColor: Color(0xFF0D0D12),
          titleTextStyle: TextStyle(
            color: Color(0xFFC41E3A),
            fontSize: 18,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.5,
          ),
        ),
        textTheme: const TextTheme(
          bodyLarge: TextStyle(color: Color(0xFFD0D0E0)),
          bodyMedium: TextStyle(color: Color(0xFFB0B0C8)),
          bodySmall: TextStyle(color: Color(0xFF808090)),
          titleLarge: TextStyle(
              color: Color(0xFFC41E3A), fontWeight: FontWeight.bold),
          titleMedium: TextStyle(
              color: Color(0xFFC41E3A), letterSpacing: 1.2),
          labelLarge: TextStyle(
              color: Color(0xFF8B8B9A), letterSpacing: 2),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF2A0A12),
            foregroundColor: const Color(0xFFD0D0E0),
            side: const BorderSide(color: Color(0xFFC41E3A)),
          ),
        ),
        inputDecorationTheme: const InputDecorationTheme(
          filled: true,
          fillColor: Color(0xFF0D0D12),
          border: OutlineInputBorder(
            borderSide: BorderSide(color: Color(0xFF3A1A22)),
          ),
          enabledBorder: OutlineInputBorder(
            borderSide: BorderSide(color: Color(0xFF3A1A22)),
          ),
          focusedBorder: OutlineInputBorder(
            borderSide: BorderSide(color: Color(0xFFC41E3A), width: 2),
          ),
          labelStyle: TextStyle(color: Color(0xFF808090)),
          hintStyle: TextStyle(color: Color(0xFF3A2A30)),
        ),
        iconTheme:
            const IconThemeData(color: Color(0xFFC41E3A), size: 28),
        dividerColor: const Color(0xFF2A1A22),
        listTileTheme: const ListTileThemeData(
          tileColor: Color(0xFF14141C),
          textColor: Color(0xFFD0D0E0),
          iconColor: Color(0xFFC41E3A),
        ),
        extensions: [
          const AppThemeExtension(
            teamName: 'Black Talon',
            teamNameJa: 'ブラック・タロン',
            desktopBackground: Color(0xFF080810),
            taskbarColor: Color(0xFF050508),
            taskbarBorderColor: Color(0xFFC41E3A),
            iconGlowColor: Color(0xFFC41E3A),
            accentColor: Color(0xFF8B8B9A),
            markerColorA: Color(0xFFC41E3A),
            markerColorB: Color(0xFF4455DD),
            objectiveColor: Color(0xFFFFAA00),
            startButtonColor: Color(0xFF1A0010),
          ),
        ],
      );
}
