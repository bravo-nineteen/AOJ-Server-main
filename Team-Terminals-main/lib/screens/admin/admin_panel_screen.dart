import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/app_state.dart';
import '../../models/models.dart';
import '../../theme/app_themes.dart';
import '../../widgets/window_frame.dart';

class AdminPanelScreen extends StatelessWidget {
  const AdminPanelScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return WindowFrame(
      title: 'Admin Panel',
      onClose: () => Navigator.pop(context),
      child: const _AdminBody(),
    );
  }
}

class _AdminBody extends StatefulWidget {
  const _AdminBody();

  @override
  State<_AdminBody> createState() => _AdminBodyState();
}

class _AdminBodyState extends State<_AdminBody>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    return Column(
      children: [
        TabBar(
          controller: _tabs,
          indicatorColor: ext.iconGlowColor,
          labelColor: ext.iconGlowColor,
          unselectedLabelColor: Colors.white54,
          tabs: const [
            Tab(text: 'TEAM'),
            Tab(text: 'PIN'),
            Tab(text: 'ABOUT'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabs,
            children: const [
              _TeamTab(),
              _PinTab(),
              _AboutTab(),
            ],
          ),
        ),
      ],
    );
  }
}

// ── Team tab ────────────────────────────────────────────────────────────────

class _TeamTab extends StatelessWidget {
  const _TeamTab();

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final ext = Theme.of(context).extension<AppThemeExtension>()!;

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('CURRENT TEAM',
              style: TextStyle(
                  color: ext.accentColor,
                  fontSize: 10,
                  letterSpacing: 2)),
          const SizedBox(height: 12),
          Text(
            state.team.displayName,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          Text(state.team.displayNameJa,
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 24),
          Text('CHANGE TEAM',
              style: TextStyle(
                  color: ext.accentColor,
                  fontSize: 10,
                  letterSpacing: 2)),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            children: TeamType.values.map((t) {
              final sel = state.team == t;
              final col = t == TeamType.taskForceOnyx
                  ? const Color(0xFF6B8F47)
                  : const Color(0xFFC41E3A);
              return ChoiceChip(
                selected: sel,
                label: Text(t.displayName),
                selectedColor: col.withAlpha(80),
                labelStyle: TextStyle(color: sel ? col : Colors.white54),
                side: BorderSide(color: sel ? col : Colors.white24),
                onSelected: (_) async {
                  await context.read<AppState>().setTeam(t);
                },
              );
            }).toList(),
          ),
          const SizedBox(height: 8),
          const Text(
            'Changing the team updates the theme on this device immediately.',
            style: TextStyle(color: Colors.white38, fontSize: 11),
          ),
        ],
      ),
    );
  }
}

// ── PIN tab ─────────────────────────────────────────────────────────────────

class _PinTab extends StatefulWidget {
  const _PinTab();

  @override
  State<_PinTab> createState() => _PinTabState();
}

class _PinTabState extends State<_PinTab> {
  final _currentCtrl = TextEditingController();
  final _newCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  String? _error;
  String? _success;

  @override
  void dispose() {
    _currentCtrl.dispose();
    _newCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  void _change() {
    final cur = _currentCtrl.text.trim();
    final nw = _newCtrl.text.trim();
    final conf = _confirmCtrl.text.trim();

    if (nw.length < 4) {
      setState(() {
        _error = 'PIN must be at least 4 digits.';
        _success = null;
      });
      return;
    }
    if (nw != conf) {
      setState(() {
        _error = 'New PINs do not match.';
        _success = null;
      });
      return;
    }

    final ok = context.read<AppState>().login(cur);
    if (!ok) {
      setState(() {
        _error = 'Current PIN incorrect.';
        _success = null;
      });
      return;
    }

    context.read<AppState>().changePin(nw).then((_) {
      setState(() {
        _error = null;
        _success = 'PIN updated successfully.';
        _currentCtrl.clear();
        _newCtrl.clear();
        _confirmCtrl.clear();
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _currentCtrl,
            obscureText: true,
            keyboardType: TextInputType.number,
            decoration:
                const InputDecoration(labelText: 'Current PIN'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _newCtrl,
            obscureText: true,
            keyboardType: TextInputType.number,
            maxLength: 8,
            decoration:
                const InputDecoration(labelText: 'New PIN', counterText: ''),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _confirmCtrl,
            obscureText: true,
            keyboardType: TextInputType.number,
            maxLength: 8,
            decoration: const InputDecoration(
                labelText: 'Confirm New PIN', counterText: ''),
          ),
          const SizedBox(height: 16),
          if (_error != null)
            Text(_error!,
                style: const TextStyle(color: Color(0xFFFF6B35))),
          if (_success != null)
            Text(_success!,
                style: const TextStyle(color: Color(0xFF4CAF50))),
          const SizedBox(height: 12),
          ElevatedButton.icon(
            onPressed: _change,
            icon: const Icon(Icons.lock_reset),
            label: const Text('CHANGE PIN'),
          ),
        ],
      ),
    );
  }
}

// ── About tab ────────────────────────────────────────────────────────────────

class _AboutTab extends StatelessWidget {
  const _AboutTab();

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('TEAM TERMINALS v1.0',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          const Text(
            'Airsoft Command & Control System\n'
            'Designed for field operations, game management,\n'
            'device coordination and team roster tracking.\n\n'
            'Two-team bilingual platform:\n'
            '  • Task Force Onyx (タスクフォース・オニキス)\n'
            '  • Black Talon (ブラック・タロン)',
            style: TextStyle(
                color: Colors.white60, fontSize: 13, height: 1.6),
          ),
          const SizedBox(height: 24),
          Text('NETWORK',
              style: TextStyle(
                  color: ext.accentColor,
                  fontSize: 10,
                  letterSpacing: 2)),
          const SizedBox(height: 8),
          const Text(
            'WiFi sync port: 47731 (TCP)\n'
            'Discovery port: 47730 (UDP)\n'
            'Ensure both tablets are on the same network.',
            style: TextStyle(
                color: Colors.white54,
                fontSize: 12,
                fontFamily: 'monospace'),
          ),
        ],
      ),
    );
  }
}
