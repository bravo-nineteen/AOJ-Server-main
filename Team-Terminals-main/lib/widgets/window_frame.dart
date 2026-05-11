import 'package:flutter/material.dart';
import '../theme/app_themes.dart';

/// A themed window frame used as the chrome for full-screen overlay screens.
class WindowFrame extends StatelessWidget {
  const WindowFrame({
    super.key,
    required this.title,
    required this.child,
    this.actions,
    this.onClose,
  });

  final String title;
  final Widget child;
  final List<Widget>? actions;
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(44),
        child: Container(
          decoration: BoxDecoration(
            color: ext.taskbarColor,
            border: Border(
              bottom: BorderSide(color: ext.taskbarBorderColor, width: 1.5),
            ),
          ),
          child: Row(
            children: [
              // Window-control dot row (cosmetic)
              const SizedBox(width: 8),
              _WindowDot(color: const Color(0xFFFF5F57)),
              const SizedBox(width: 5),
              _WindowDot(color: const Color(0xFFFFBD2E)),
              const SizedBox(width: 5),
              _WindowDot(color: const Color(0xFF28C840)),
              const SizedBox(width: 12),
              // Title
              Icon(Icons.terminal, size: 14, color: ext.iconGlowColor),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  title.toUpperCase(),
                  style: TextStyle(
                    color: ext.iconGlowColor,
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (actions != null) ...actions!,
              if (onClose != null)
                IconButton(
                  icon: const Icon(Icons.close, size: 18),
                  color: Colors.white54,
                  onPressed: onClose,
                  tooltip: 'Close',
                ),
              const SizedBox(width: 4),
            ],
          ),
        ),
      ),
      body: child,
    );
  }
}

class _WindowDot extends StatelessWidget {
  const _WindowDot({required this.color});
  final Color color;
  @override
  Widget build(BuildContext context) =>
      Container(width: 11, height: 11, decoration: BoxDecoration(color: color, shape: BoxShape.circle));
}
