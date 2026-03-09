import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Brand Colors
  static const Color brandPrimary = Color(0xFF173C64);
  static const Color brandPrimaryHover = Color(0xFF1F4F7E);
  static const Color brandPrimaryLight = Color(0xFFE8EEF5);
  
  // Gradient Colors
  static const Color gradientStart = Color(0xFFE3F2FD);
  static const Color gradientMid = Color(0xFFBBDEFB);
  static const Color gradientEnd = Color(0xFF90CAF9);
  
  static ThemeData get lightTheme {
    return ThemeData(
      primaryColor: brandPrimary,
      scaffoldBackgroundColor: brandPrimary,
      colorScheme: ColorScheme.light(
        primary: brandPrimary,
        secondary: brandPrimaryHover,
        surface: Colors.white,
      ),
      textTheme: GoogleFonts.interTextTheme(),
      appBarTheme: AppBarTheme(
        backgroundColor: brandPrimary,
        elevation: 0,
        iconTheme: IconThemeData(color: Colors.white),
        titleTextStyle: GoogleFonts.inter(
          color: Colors.white,
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: brandPrimary,
          foregroundColor: Colors.white,
          padding: EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          elevation: 8,
          shadowColor: brandPrimary.withValues(alpha: 0.5),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: brandPrimary,
          side: BorderSide(color: brandPrimary, width: 2),
          padding: EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.grey.shade300),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.grey.shade300),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: brandPrimary, width: 2),
        ),
        filled: true,
        fillColor: Colors.white,
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),
    );
  }
  
  static LinearGradient get backgroundGradient {
    return LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [
        Color(0xFFE8EEF5),  // Very light blue-grey
        Color(0xFF9BB4D4),  // Light blue
        Color(0xFF5A7BA8),  // Medium blue
        Color(0xFF2E5180),  // Deeper blue
        Color(0xFF173C64),  // Base color
      ],
    );
  }
}
