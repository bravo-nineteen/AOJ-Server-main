import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/app_themes.dart';
import 'start_menu.dart';

class Taskbar extends StatefulWidget {
  const Taskbar({super.key, this.onOpenWindow});
  final void Function(String screenKey)? onOpenWindow;

  @override
  State<Taskbar> createState() => _TaskbarState();
}

class _TaskbarState extends State<Taskbar> {
  bool _startMenuOpen = false;

  void _toggleStartMenu() => setState(() => _startMenuOpen = !_startMenuOpen);
  void _closeStartMenu() => setState(() => _startMenuOpen = false);

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final state = context.watch<AppState>();

    return Stack(
      clipBehavior: Clip.none,
      children: [
        // ── Start menu popup ────────────────────────────────────────────────
        if (_startMenuOpen)
          Positioned(
            bottom: 50,
            left: 0,
            child: StartMenu(
              onClose: _closeStartMenu,
              onOpenWindow: (key) {
                _closeStartMenu();
                widget.onOpenWindow?.call(key);
              },
            ),
          ),

        // ── Taskbar bar ─────────────────────────────────────────────────────
        Container(
          height: 50,
          decoration: BoxDecoration(
            color: ext.taskbarColor,
            border: Border(
              top: BorderSide(color: ext.taskbarBorderColor, width: 1.5),
            ),
          ),
          child: Row(
            children: [
              // Start button
              _StartButton(
                teamName: ext.teamName,
                color: ext.startButtonColor,
                borderColor: ext.taskbarBorderColor,
                isOpen: _startMenuOpen,
                onTap: _toggleStartMenu,
              ),

              Container(
                width: 1,
                height: 30,
                color: ext.taskbarBorderColor.withAlpha(80),
                margin: const EdgeInsets.symmetric(horizontal: 8),
              ),

              // Quick-launch icons
              _QuickIcon(
                icon: Icons.gamepad_outlined,
                tooltip: 'Active Game',
                onTap: () => widget.onOpenWindow?.call('game_mode'),
              ),
              _QuickIcon(
                icon: Icons.map_outlined,
                tooltip: 'Field Map',
                onTap: () => widget.onOpenWindow?.call('field_map'),
              ),
              _QuickIcon(
                icon: Icons.people_outline,
                tooltip: 'Roster',
                onTap: () => widget.onOpenWindow?.call('roster'),
              ),

              const Spacer(),

              // Admin badge
              if (state.isAdmin)
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 6),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: ext.taskbarBorderColor.withAlpha(40),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                        color: ext.taskbarBorderColor.withAlpha(120)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.shield, size: 12, color: ext.accentColor),
                      const SizedBox(width: 4),
                      Text(
                        'ADMIN',
                        style: TextStyle(
                          color: ext.accentColor,
                          fontSize: 10,
                          letterSpacing: 2,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),

              // Clock
              _Clock(borderColor: ext.taskbarBorderColor),
            ],
          ),
        ),
      ],
    );
  }
}

class _StartButton extends StatelessWidget {
  const _StartButton({
    required this.teamName,
    required this.color,
    required this.borderColor,
    required this.isOpen,
    required this.onTap,
  });
  final String teamName;
  final Color color;
  final Color borderColor;
  final bool isOpen;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 120),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 0),
        height: double.infinity,
        decoration: BoxDecoration(
          color: isOpen ? borderColor.withAlpha(80) : color,
          border: Border(
            right: BorderSide(color: borderColor.withAlpha(80)),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.my_library_books_outlined,
                size: 16, color: borderColor),
            const SizedBox(width: 8),
            Text(
              teamName.toUpperCase(),
              style: TextStyle(
                color: borderColor,
                fontSize: 11,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickIcon extends StatelessWidget {
  const _QuickIcon(
      {required this.icon, required this.tooltip, required this.onTap});
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Icon(icon, size: 20, color: ext.iconGlowColor),
        ),
      ),
    );
  }
}

class _Clock extends StatefulWidget {
  const _Clock({required this.borderColor});
  final Color borderColor;

  @override
  State<_Clock> createState() => _ClockState();
}

class _ClockState extends State<_Clock> {
  late DateTime _now;
  late final Stream<DateTime> _tick;

  @override
  void initState() {
    super.initState();
    _now = DateTime.now();
    _tick = Stream.periodic(const Duration(seconds: 1), (_) => DateTime.now());
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<DateTime>(
      stream: _tick,
      initialData: _now,
      builder: (context, snap) {
        final t = snap.data ?? _now;
        final h = t.hour.toString().padLeft(2, '0');
        final m = t.minute.toString().padLeft(2, '0');
        final s = t.second.toString().padLeft(2, '0');
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '$h:$m:$s',
                style: TextStyle(
                  color: widget.borderColor,
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  fontFamily: 'monospace',
                  letterSpacing: 1,
                ),
              ),
              Text(
                '${t.year}-${t.month.toString().padLeft(2, '0')}-${t.day.toString().padLeft(2, '0')}',
                style: const TextStyle(
                  color: Colors.white38,
                  fontSize: 9,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
