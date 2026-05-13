import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/app_themes.dart';
import '../providers/app_state.dart';
import '../widgets/desktop_icon.dart';
import '../widgets/taskbar.dart';
import 'my_computer_screen.dart';
import 'schedule_screen.dart';
import 'field_map_screen.dart';
import 'devices_screen.dart';
import 'roster_screen.dart';
import 'game_mode_screen.dart';
import 'intel_screen.dart';
import 'comms_log_screen.dart';
import 'admin/admin_panel_screen.dart';

class DesktopScreen extends StatefulWidget {
  const DesktopScreen({super.key});

  @override
  State<DesktopScreen> createState() => _DesktopScreenState();
}

class _DesktopScreenState extends State<DesktopScreen> {
  void _openScreen(BuildContext context, String key) {
    final routes = <String, Widget Function()>{
      'my_computer': () => const MyComputerScreen(),
      'schedule': () => const ScheduleScreen(),
      'field_map': () => const FieldMapScreen(),
      'devices': () => const DevicesScreen(),
      'roster': () => const RosterScreen(),
      'game_mode': () => const GameModeScreen(),
      'intel': () => const IntelScreen(),
      'comms_log': () => const CommsLogScreen(),
      'admin_panel': () => const AdminPanelScreen(),
    };

    final builder = routes[key];
    if (builder == null) return;

    Navigator.of(context).push(
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => builder(),
        transitionDuration: const Duration(milliseconds: 180),
        transitionsBuilder: (_, anim, __, child) => FadeTransition(
          opacity: CurvedAnimation(parent: anim, curve: Curves.easeIn),
          child: child,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final state = context.watch<AppState>();

    return Scaffold(
      body: Stack(
        children: [
          // ── Desktop background ─────────────────────────────────────────
          Container(
            decoration: BoxDecoration(
              color: ext.desktopBackground,
            ),
            child: _DesktopBackground(ext: ext),
          ),

          // ── Icon grid ─────────────────────────────────────────────────
          Positioned(
            top: 16,
            left: 16,
            right: 16,
            bottom: 58,
            child: Align(
              alignment: Alignment.topLeft,
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  DesktopIcon(
                    icon: Icons.computer,
                    label: 'My Computer',
                    onTap: () => _openScreen(context, 'my_computer'),
                  ),
                  DesktopIcon(
                    icon: Icons.calendar_today,
                    label: 'Schedule',
                    onTap: () => _openScreen(context, 'schedule'),
                  ),
                  DesktopIcon(
                    icon: Icons.map,
                    label: 'Field Map',
                    onTap: () => _openScreen(context, 'field_map'),
                  ),
                  DesktopIcon(
                    icon: Icons.router,
                    label: 'Devices',
                    onTap: () => _openScreen(context, 'devices'),
                  ),
                  DesktopIcon(
                    icon: Icons.people,
                    label: 'Roster',
                    onTap: () => _openScreen(context, 'roster'),
                  ),
                  DesktopIcon(
                    icon: Icons.gamepad,
                    label: 'Game Mode',
                    sublabel: state.activeGameFile?.name,
                    onTap: () => _openScreen(context, 'game_mode'),
                  ),
                  DesktopIcon(
                    icon: Icons.article_outlined,
                    label: 'Intel',
                    onTap: () => _openScreen(context, 'intel'),
                  ),
                  DesktopIcon(
                    icon: Icons.chat_outlined,
                    label: 'Comms Log',
                    onTap: () => _openScreen(context, 'comms_log'),
                  ),
                  if (state.isAdmin)
                    DesktopIcon(
                      icon: Icons.admin_panel_settings,
                      label: 'Admin',
                      iconColor: ext.accentColor,
                      onTap: () => _openScreen(context, 'admin_panel'),
                    ),
                ],
              ),
            ),
          ),

          // ── Team watermark ─────────────────────────────────────────────
          Positioned(
            bottom: 66,
            right: 16,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  ext.teamName.toUpperCase(),
                  style: TextStyle(
                    color: ext.iconGlowColor.withAlpha(40),
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 6,
                  ),
                ),
                Text(
                  ext.teamNameJa,
                  style: TextStyle(
                    color: ext.iconGlowColor.withAlpha(25),
                    fontSize: 14,
                    letterSpacing: 3,
                  ),
                ),
              ],
            ),
          ),

          // ── Taskbar ────────────────────────────────────────────────────
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Taskbar(
              onOpenWindow: (key) => _openScreen(context, key),
            ),
          ),
        ],
      ),
    );
  }
}

/// Subtle grid/scanline background pattern
class _DesktopBackground extends StatelessWidget {
  const _DesktopBackground({required this.ext});
  final AppThemeExtension ext;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _GridPainter(color: ext.iconGlowColor.withAlpha(10)),
      child: const SizedBox.expand(),
    );
  }
}

class _GridPainter extends CustomPainter {
  final Color color;
  _GridPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color..strokeWidth = 0.5;
    const spacing = 40.0;
    for (double x = 0; x < size.width; x += spacing) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += spacing) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(_GridPainter old) => old.color != color;
}
