import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/app_themes.dart';

class StartMenu extends StatefulWidget {
  const StartMenu({super.key, this.onClose, this.onOpenWindow});
  final VoidCallback? onClose;
  final void Function(String)? onOpenWindow;

  @override
  State<StartMenu> createState() => _StartMenuState();
}

class _StartMenuState extends State<StartMenu> {
  void _open(String key) => widget.onOpenWindow?.call(key);

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final state = context.watch<AppState>();

    return Material(
      elevation: 16,
      color: Colors.transparent,
      child: Container(
        width: 260,
        decoration: BoxDecoration(
          color: ext.taskbarColor,
          border: Border.all(color: ext.taskbarBorderColor, width: 1.5),
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(6),
            topRight: Radius.circular(6),
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // ── Header ──────────────────────────────────────────────────────
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: ext.startButtonColor,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(6),
                  topRight: Radius.circular(6),
                ),
                border: Border(
                  bottom: BorderSide(color: ext.taskbarBorderColor),
                ),
              ),
              child: Row(
                children: [
                  Icon(Icons.person_pin, size: 28, color: ext.iconGlowColor),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          ext.teamName.toUpperCase(),
                          style: TextStyle(
                            color: ext.iconGlowColor,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.5,
                            fontSize: 13,
                          ),
                        ),
                        Text(
                          state.isAdmin ? '[ ADMIN ]' : '[ OPERATOR ]',
                          style: TextStyle(
                            color: ext.accentColor,
                            fontSize: 10,
                            letterSpacing: 1,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // ── Menu items ───────────────────────────────────────────────────
            _MenuSection(label: 'SYSTEM'),
            _MenuItem(
              icon: Icons.folder_open,
              label: 'My Computer',
              onTap: () => _open('my_computer'),
            ),
            _MenuItem(
              icon: Icons.calendar_today,
              label: 'Schedule',
              onTap: () => _open('schedule'),
            ),
            _MenuItem(
              icon: Icons.map,
              label: 'Field Map',
              onTap: () => _open('field_map'),
            ),
            _MenuItem(
              icon: Icons.router,
              label: 'Devices',
              onTap: () => _open('devices'),
            ),
            _MenuItem(
              icon: Icons.people,
              label: 'Roster',
              onTap: () => _open('roster'),
            ),
            _MenuItem(
              icon: Icons.gamepad,
              label: 'Game Mode',
              onTap: () => _open('game_mode'),
            ),
            _MenuItem(
              icon: Icons.article_outlined,
              label: 'Intel Briefing',
              onTap: () => _open('intel'),
            ),
            _MenuItem(
              icon: Icons.chat_outlined,
              label: 'Comms Log',
              onTap: () => _open('comms_log'),
            ),

            Divider(color: ext.taskbarBorderColor, height: 1),
            _MenuSection(label: 'ADMIN'),

            if (!state.isAdmin)
              _MenuItem(
                icon: Icons.lock_outline,
                label: 'Admin Login',
                onTap: () {
                  widget.onClose?.call();
                  _showLoginDialog(context);
                },
              ),

            if (state.isAdmin) ...[
              _MenuItem(
                icon: Icons.admin_panel_settings,
                label: 'Admin Panel',
                onTap: () => _open('admin_panel'),
              ),
              _MenuItem(
                icon: Icons.logout,
                label: 'Logout Admin',
                onTap: () {
                  context.read<AppState>().logout();
                  widget.onClose?.call();
                },
              ),
            ],

            Divider(color: ext.taskbarBorderColor, height: 1),

            _MenuItem(
              icon: Icons.close,
              label: 'Close Menu',
              onTap: widget.onClose ?? () {},
            ),
            const SizedBox(height: 4),
          ],
        ),
      ),
    );
  }

  void _showLoginDialog(BuildContext context) {
    final ctrl = TextEditingController();
    String? error;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) {
          final ext = Theme.of(ctx).extension<AppThemeExtension>()!;
          return AlertDialog(
            title: Row(
              children: [
                Icon(Icons.shield, color: ext.iconGlowColor),
                const SizedBox(width: 8),
                const Text('ADMIN LOGIN'),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: ctrl,
                  obscureText: true,
                  keyboardType: TextInputType.number,
                  maxLength: 8,
                  decoration: InputDecoration(
                    labelText: 'PIN',
                    errorText: error,
                    prefixIcon: const Icon(Icons.lock),
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('CANCEL'),
              ),
              ElevatedButton(
                onPressed: () {
                  final ok =
                      context.read<AppState>().login(ctrl.text.trim());
                  if (ok) {
                    Navigator.pop(ctx);
                  } else {
                    setS(() => error = 'Incorrect PIN');
                  }
                },
                child: const Text('LOGIN'),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _MenuSection extends StatelessWidget {
  const _MenuSection({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 2),
      child: Text(
        label,
        style: TextStyle(
          color: ext.accentColor,
          fontSize: 9,
          letterSpacing: 2,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

class _MenuItem extends StatelessWidget {
  const _MenuItem(
      {required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    return InkWell(
      onTap: onTap,
      hoverColor: ext.iconGlowColor.withAlpha(30),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        child: Row(
          children: [
            Icon(icon, size: 18, color: ext.iconGlowColor),
            const SizedBox(width: 12),
            Text(
              label,
              style: const TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w500),
            ),
          ],
        ),
      ),
    );
  }
}
