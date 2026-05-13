import 'package:flutter/material.dart';
import '../theme/app_themes.dart';

class DesktopIcon extends StatefulWidget {
  const DesktopIcon({
    super.key,
    required this.icon,
    required this.label,
    required this.onTap,
    this.sublabel,
    this.iconColor,
  });

  final IconData icon;
  final String label;
  final String? sublabel;
  final Color? iconColor;
  final VoidCallback onTap;

  @override
  State<DesktopIcon> createState() => _DesktopIconState();
}

class _DesktopIconState extends State<DesktopIcon> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final glow = widget.iconColor ?? ext.iconGlowColor;

    return GestureDetector(
      onTap: widget.onTap,
      onTapDown: (_) => setState(() => _hovered = true),
      onTapUp: (_) => setState(() => _hovered = false),
      onTapCancel: () => setState(() => _hovered = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 120),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
        decoration: BoxDecoration(
          color: _hovered
              ? glow.withAlpha(40)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: _hovered
              ? Border.all(color: glow.withAlpha(120))
              : null,
          boxShadow: _hovered
              ? [BoxShadow(color: glow.withAlpha(60), blurRadius: 12)]
              : null,
        ),
        child: SizedBox(
          width: 80,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(widget.icon, size: 40, color: glow),
              const SizedBox(height: 6),
              Text(
                widget.label,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  shadows: [
                    Shadow(color: Colors.black, blurRadius: 4),
                  ],
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              if (widget.sublabel != null) ...[
                const SizedBox(height: 2),
                Text(
                  widget.sublabel!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white54,
                    fontSize: 9,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
