import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/app_state.dart';
import '../../models/models.dart';
import '../../theme/app_themes.dart';

/// Shown only on first launch. Admin must set team and PIN before proceeding.
class TeamSetupScreen extends StatefulWidget {
  const TeamSetupScreen({super.key});

  @override
  State<TeamSetupScreen> createState() => _TeamSetupScreenState();
}

class _TeamSetupScreenState extends State<TeamSetupScreen> {
  TeamType _selectedTeam = TeamType.taskForceOnyx;
  final _pinCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  final _serverCtrl = TextEditingController(text: '127.0.0.1');
  String? _error;
  bool _loading = false;

  Future<void> _confirm() async {
    final pin = _pinCtrl.text.trim();
    final confirm = _confirmCtrl.text.trim();

    if (pin.length < 4) {
      setState(() => _error = 'PIN must be at least 4 digits.');
      return;
    }
    if (pin != confirm) {
      setState(() => _error = 'PINs do not match.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    await context.read<AppState>().completeFirstRunSetup(
          team: _selectedTeam,
          pin: pin,
          serverHost: _serverCtrl.text.trim(),
        );
    // AppState notifies and MaterialApp rebuilds to DesktopScreen
  }

  @override
  void dispose() {
    _pinCtrl.dispose();
    _confirmCtrl.dispose();
    _serverCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _Body(
        selectedTeam: _selectedTeam,
        pinCtrl: _pinCtrl,
        confirmCtrl: _confirmCtrl,
        serverCtrl: _serverCtrl,
        error: _error,
        loading: _loading,
        onTeamChanged: (t) => setState(() => _selectedTeam = t),
        onConfirm: _confirm,
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({
    required this.selectedTeam,
    required this.pinCtrl,
    required this.confirmCtrl,
    required this.serverCtrl,
    required this.error,
    required this.loading,
    required this.onTeamChanged,
    required this.onConfirm,
  });

  final TeamType selectedTeam;
  final TextEditingController pinCtrl;
  final TextEditingController confirmCtrl;
  final TextEditingController serverCtrl;
  final String? error;
  final bool loading;
  final ValueChanged<TeamType> onTeamChanged;
  final VoidCallback onConfirm;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(color: Color(0xFF080C08)),
      child: Center(
        child: SingleChildScrollView(
          child: Container(
            width: 440,
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              color: const Color(0xFF111811),
              border: Border.all(color: const Color(0xFF3D5C2E), width: 1.5),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.shield_outlined,
                    size: 48, color: Color(0xFF6B8F47)),
                const SizedBox(height: 12),
                const Text(
                  'TEAM TERMINALS',
                  style: TextStyle(
                    color: Color(0xFF8FB860),
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 5,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'INITIAL SETUP — ADMIN REQUIRED',
                  style: TextStyle(
                    color: Color(0xFF4A6741),
                    fontSize: 10,
                    letterSpacing: 3,
                  ),
                ),
                const SizedBox(height: 32),

                // ── Team selection ──────────────────────────────────────
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'SELECT TEAM',
                    style: TextStyle(
                      color: Color(0xFFD4A017),
                      fontSize: 10,
                      letterSpacing: 2,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _TeamCard(
                      team: TeamType.taskForceOnyx,
                      selected: selectedTeam == TeamType.taskForceOnyx,
                      onTap: () =>
                          onTeamChanged(TeamType.taskForceOnyx),
                      primaryColor: const Color(0xFF6B8F47),
                      bgColor: const Color(0xFF1A2B1A),
                    ),
                    const SizedBox(width: 12),
                    _TeamCard(
                      team: TeamType.blackTalon,
                      selected: selectedTeam == TeamType.blackTalon,
                      onTap: () =>
                          onTeamChanged(TeamType.blackTalon),
                      primaryColor: const Color(0xFFC41E3A),
                      bgColor: const Color(0xFF1A0A12),
                    ),
                  ],
                ),

                const SizedBox(height: 24),
                // ── PIN ─────────────────────────────────────────────────
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'SET ADMIN PIN',
                    style: TextStyle(
                      color: Color(0xFFD4A017),
                      fontSize: 10,
                      letterSpacing: 2,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: pinCtrl,
                  obscureText: true,
                  keyboardType: TextInputType.number,
                  maxLength: 8,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Admin PIN (4–8 digits)',
                    prefixIcon: Icon(Icons.lock),
                    counterText: '',
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: confirmCtrl,
                  obscureText: true,
                  keyboardType: TextInputType.number,
                  maxLength: 8,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Confirm PIN',
                    prefixIcon: Icon(Icons.lock_outline),
                    counterText: '',
                  ),
                ),

                const SizedBox(height: 10),
                TextField(
                  controller: serverCtrl,
                  keyboardType: TextInputType.url,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'AOJ Server Host (IP or DNS)',
                    prefixIcon: Icon(Icons.dns_outlined),
                    helperText: 'Example: 192.168.1.50',
                  ),
                ),

                if (error != null) ...[
                  const SizedBox(height: 10),
                  Text(
                    error!,
                    style: const TextStyle(
                        color: Color(0xFFFF6B35), fontSize: 12),
                  ),
                ],

                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  height: 46,
                  child: ElevatedButton.icon(
                    onPressed: loading ? null : onConfirm,
                    icon: loading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                                strokeWidth: 2))
                        : const Icon(Icons.check_circle_outline),
                    label: const Text(
                      'CONFIRM & LAUNCH',
                      style: TextStyle(letterSpacing: 2),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TeamCard extends StatelessWidget {
  const _TeamCard({
    required this.team,
    required this.selected,
    required this.onTap,
    required this.primaryColor,
    required this.bgColor,
  });
  final TeamType team;
  final bool selected;
  final VoidCallback onTap;
  final Color primaryColor;
  final Color bgColor;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: bgColor,
            border: Border.all(
              color: selected ? primaryColor : primaryColor.withAlpha(50),
              width: selected ? 2 : 1,
            ),
            borderRadius: BorderRadius.circular(4),
            boxShadow: selected
                ? [BoxShadow(color: primaryColor.withAlpha(60), blurRadius: 12)]
                : null,
          ),
          child: Column(
            children: [
              Icon(
                team == TeamType.taskForceOnyx
                    ? Icons.military_tech
                    : Icons.dark_mode,
                size: 28,
                color: primaryColor,
              ),
              const SizedBox(height: 6),
              Text(
                team.displayName.toUpperCase(),
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: primaryColor,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2,
                ),
              ),
              Text(
                team.displayNameJa,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: primaryColor.withAlpha(160),
                  fontSize: 9,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
