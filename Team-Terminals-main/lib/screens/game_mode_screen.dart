import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/models.dart';
import '../theme/app_themes.dart';
import '../widgets/window_frame.dart';
import '../services/game_network_service.dart';

class GameModeScreen extends StatefulWidget {
  const GameModeScreen({super.key});

  @override
  State<GameModeScreen> createState() => _GameModeScreenState();
}

class _GameModeScreenState extends State<GameModeScreen> {
  final _net = GameNetworkService();
  bool _isNetServer = false;
  bool _netConnected = false;
  bool _discovering = false;
  String _netStatus = 'Not connected';
  StreamSubscription? _netSub;

  @override
  void initState() {
    super.initState();
    _netSub = _net.events.listen(_onNetEvent);
  }

  @override
  void dispose() {
    _netSub?.cancel();
    _net.dispose();
    super.dispose();
  }

  void _onNetEvent(NetEvent ev) {
    final state = context.read<AppState>();
    final file = state.activeGameFile;
    if (file == null) return;

    switch (ev.type) {
      case NetEventType.respawn:
        final teamName = ev.payload['team'] as String?;
        if (teamName != null) {
          final team = TeamType.values.byName(teamName);
          final session = file.sessions.cast<GameSession?>().firstWhere(
              (s) => s?.isActive == true,
              orElse: () => null);
          if (session != null) {
            state.incrementRespawn(file.id, session.id, team);
          }
        }
        break;
      case NetEventType.ping:
        setState(() {
          _netConnected = true;
          _netStatus = 'Connected';
        });
        break;
      default:
        break;
    }
  }

  Future<void> _startServer() async {
    await _net.startServer();
    setState(() {
      _isNetServer = true;
      _netStatus = 'Hosting — waiting for client…';
    });
    _net.sendPing();
    setState(() {
      _netConnected = true;
      _netStatus = 'Hosting (port ${tcpPort})';
    });
  }

  Future<void> _discover() async {
    setState(() {
      _discovering = true;
      _netStatus = 'Searching…';
    });
    final ip = await _net.discover();
    if (ip == null) {
      setState(() {
        _discovering = false;
        _netStatus = 'No server found on network.';
      });
      return;
    }
    final ok = await _net.connectToServer(ip);
    setState(() {
      _discovering = false;
      _netConnected = ok;
      _netStatus = ok ? 'Connected to $ip' : 'Connection failed';
    });
    if (ok) _net.sendPing();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final file = state.activeGameFile;

    return WindowFrame(
      title: 'Game Mode',
      onClose: () => Navigator.pop(context),
      child: file == null
          ? const Center(
              child: Text('No active game file. Select one in My Computer.',
                  style: TextStyle(color: Colors.white54)),
            )
          : _GameBody(
              file: file,
              state: state,
              ext: ext,
              net: _net,
              netConnected: _netConnected,
              netStatus: _netStatus,
              discovering: _discovering,
              isServer: _isNetServer,
              onStartServer: _startServer,
              onDiscover: _discover,
            ),
    );
  }
}

class _GameBody extends StatelessWidget {
  const _GameBody({
    required this.file,
    required this.state,
    required this.ext,
    required this.net,
    required this.netConnected,
    required this.netStatus,
    required this.discovering,
    required this.isServer,
    required this.onStartServer,
    required this.onDiscover,
  });

  final GameFile file;
  final AppState state;
  final AppThemeExtension ext;
  final GameNetworkService net;
  final bool netConnected;
  final String netStatus;
  final bool discovering;
  final bool isServer;
  final VoidCallback onStartServer;
  final VoidCallback onDiscover;

  GameSession? get _active => file.sessions.cast<GameSession?>().firstWhere(
      (s) => s?.isActive == true,
      orElse: () => null);

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // ── Network bar ───────────────────────────────────────────────
        _NetBar(
          status: netStatus,
          connected: netConnected,
          discovering: discovering,
          isServer: isServer,
          ext: ext,
          onStartServer: onStartServer,
          onDiscover: onDiscover,
        ),

        Expanded(
          child: _active == null
              ? _NoSession(
                  file: file,
                  state: state,
                  ext: ext,
                  isAdmin: state.isAdmin,
                )
              : _ActiveSession(
                  session: _active!,
                  file: file,
                  state: state,
                  ext: ext,
                  net: net,
                  netConnected: netConnected,
                ),
        ),
      ],
    );
  }
}

// ── Network bar ───────────────────────────────────────────────────────────────

class _NetBar extends StatelessWidget {
  const _NetBar({
    required this.status,
    required this.connected,
    required this.discovering,
    required this.isServer,
    required this.ext,
    required this.onStartServer,
    required this.onDiscover,
  });
  final String status;
  final bool connected;
  final bool discovering;
  final bool isServer;
  final AppThemeExtension ext;
  final VoidCallback onStartServer;
  final VoidCallback onDiscover;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: ext.taskbarColor,
        border:
            Border(bottom: BorderSide(color: ext.taskbarBorderColor)),
      ),
      child: Row(
        children: [
          Icon(
            connected ? Icons.wifi : Icons.wifi_off,
            size: 16,
            color: connected
                ? const Color(0xFF4CAF50)
                : Colors.white38,
          ),
          const SizedBox(width: 8),
          Text(status,
              style: TextStyle(
                  color: connected
                      ? const Color(0xFF4CAF50)
                      : Colors.white38,
                  fontSize: 12,
                  fontFamily: 'monospace')),
          const Spacer(),
          if (!connected && !isServer) ...[
            OutlinedButton.icon(
              onPressed: discovering ? null : onDiscover,
              icon: discovering
                  ? const SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(
                          strokeWidth: 2))
                  : const Icon(Icons.search, size: 14),
              label: Text(discovering ? 'Searching…' : 'Find Server'),
              style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 4),
                  side: BorderSide(color: ext.taskbarBorderColor)),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              onPressed: onStartServer,
              icon: const Icon(Icons.host_outlined, size: 14),
              label: const Text('Host'),
              style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 4),
                  side: BorderSide(color: ext.taskbarBorderColor)),
            ),
          ],
        ],
      ),
    );
  }
}

// ── No active session ─────────────────────────────────────────────────────────

class _NoSession extends StatefulWidget {
  const _NoSession({
    required this.file,
    required this.state,
    required this.ext,
    required this.isAdmin,
  });
  final GameFile file;
  final AppState state;
  final AppThemeExtension ext;
  final bool isAdmin;

  @override
  State<_NoSession> createState() => _NoSessionState();
}

class _NoSessionState extends State<_NoSession> {
  final _modeCtrl = TextEditingController(text: 'Team Deathmatch');
  final Map<TeamType, TextEditingController> _limitCtrls = {
    TeamType.taskForceOnyx: TextEditingController(text: '20'),
    TeamType.blackTalon: TextEditingController(text: '20'),
  };

  @override
  void dispose() {
    _modeCtrl.dispose();
    for (final c in _limitCtrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _startSession() async {
    final session = GameSession(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      gameModeName: _modeCtrl.text.trim(),
      respawnLimits: {
        for (final t in TeamType.values)
          t: int.tryParse(_limitCtrls[t]!.text) ?? 20
      },
    );
    await widget.state.startSession(widget.file.id, session);
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAdmin) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.hourglass_empty,
                size: 48, color: widget.ext.iconGlowColor.withAlpha(60)),
            const SizedBox(height: 12),
            const Text('Waiting for admin to start a session…',
                style: TextStyle(color: Colors.white54)),
          ],
        ),
      );
    }

    return Center(
      child: Container(
        width: 380,
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          color: widget.ext.taskbarColor,
          border: Border.all(color: widget.ext.taskbarBorderColor),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.play_circle_outline,
                size: 40, color: widget.ext.iconGlowColor),
            const SizedBox(height: 16),
            Text('START NEW SESSION',
                style: TextStyle(
                    color: widget.ext.iconGlowColor,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2)),
            const SizedBox(height: 20),
            TextField(
              controller: _modeCtrl,
              decoration:
                  const InputDecoration(labelText: 'Game Mode'),
            ),
            const SizedBox(height: 12),
            ...TeamType.values.map((t) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: TextField(
                    controller: _limitCtrls[t],
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                        labelText:
                            '${t.displayName} Respawn Limit'),
                  ),
                )),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 46,
              child: ElevatedButton.icon(
                onPressed: _startSession,
                icon: const Icon(Icons.play_arrow),
                label: const Text('START GAME',
                    style: TextStyle(letterSpacing: 2)),
              ),
            ),

            if (widget.file.sessions.isNotEmpty) ...[
              const SizedBox(height: 20),
              Text('PAST SESSIONS',
                  style: TextStyle(
                      color: widget.ext.accentColor,
                      fontSize: 10,
                      letterSpacing: 2)),
              const SizedBox(height: 8),
              ...widget.file.sessions.reversed
                  .take(5)
                  .map((s) => _PastSessionRow(s, widget.ext)),
            ],
          ],
        ),
      ),
    );
  }
}

class _PastSessionRow extends StatelessWidget {
  const _PastSessionRow(this.session, this.ext);
  final GameSession session;
  final AppThemeExtension ext;

  @override
  Widget build(BuildContext context) {
    final onyxCount =
        session.respawnCounts[TeamType.taskForceOnyx] ?? 0;
    final talonCount =
        session.respawnCounts[TeamType.blackTalon] ?? 0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(Icons.history, size: 12, color: Colors.white38),
          const SizedBox(width: 6),
          Expanded(
            child: Text(session.gameModeName,
                style: const TextStyle(
                    fontSize: 11, color: Colors.white54)),
          ),
          Text(
            'Onyx $onyxCount | Talon $talonCount',
            style: const TextStyle(
                fontSize: 10,
                color: Colors.white38,
                fontFamily: 'monospace'),
          ),
        ],
      ),
    );
  }
}

// ── Active session ────────────────────────────────────────────────────────────

class _ActiveSession extends StatelessWidget {
  const _ActiveSession({
    required this.session,
    required this.file,
    required this.state,
    required this.ext,
    required this.net,
    required this.netConnected,
  });

  final GameSession session;
  final GameFile file;
  final AppState state;
  final AppThemeExtension ext;
  final GameNetworkService net;
  final bool netConnected;

  Future<void> _respawn(BuildContext context, TeamType team) async {
    await state.incrementRespawn(file.id, session.id, team);
    if (netConnected) {
      net.sendRespawn(team.name);
    }
  }

  Future<void> _endSession(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('END SESSION'),
        content: const Text('End this game session now?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('CANCEL')),
          ElevatedButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('END GAME')),
        ],
      ),
    );
    if (confirmed == true) {
      await state.endSession(file.id, session.id);
    }
  }

  @override
  Widget build(BuildContext context) {
    final elapsed = session.startTime != null
        ? DateTime.now().difference(session.startTime!)
        : Duration.zero;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          // ── Session header ──────────────────────────────────────────
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF4CAF50).withAlpha(40),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                      color: const Color(0xFF4CAF50).withAlpha(120)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.fiber_manual_record,
                        size: 10, color: Color(0xFF4CAF50)),
                    const SizedBox(width: 4),
                    const Text('LIVE',
                        style: TextStyle(
                            color: Color(0xFF4CAF50),
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 2)),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Text(session.gameModeName,
                  style: Theme.of(context).textTheme.titleLarge),
              const Spacer(),
              Text(
                '${elapsed.inHours.toString().padLeft(2, '0')}:${(elapsed.inMinutes % 60).toString().padLeft(2, '0')}:${(elapsed.inSeconds % 60).toString().padLeft(2, '0')}',
                style: TextStyle(
                  color: ext.accentColor,
                  fontSize: 20,
                  fontFamily: 'monospace',
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // ── Respawn counters ────────────────────────────────────────
          Row(
            children: TeamType.values
                .map((team) => Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        child: _RespawnPanel(
                          team: team,
                          count: session.respawnCounts[team] ?? 0,
                          limit: session.respawnLimits[team] ?? 20,
                          ext: ext,
                          onRespawn: () => _respawn(context, team),
                          isAdmin: state.isAdmin,
                        ),
                      ),
                    ))
                .toList(),
          ),

          const SizedBox(height: 24),

          if (state.isAdmin)
            SizedBox(
              width: 240,
              child: OutlinedButton.icon(
                onPressed: () => _endSession(context),
                icon: const Icon(Icons.stop_circle_outlined,
                    color: Colors.red),
                label: const Text('END SESSION',
                    style: TextStyle(
                        color: Colors.red, letterSpacing: 2)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Colors.red),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _RespawnPanel extends StatelessWidget {
  const _RespawnPanel({
    required this.team,
    required this.count,
    required this.limit,
    required this.ext,
    required this.onRespawn,
    required this.isAdmin,
  });
  final TeamType team;
  final int count;
  final int limit;
  final AppThemeExtension ext;
  final VoidCallback onRespawn;
  final bool isAdmin;

  @override
  Widget build(BuildContext context) {
    final teamColor = team == TeamType.taskForceOnyx
        ? const Color(0xFF4CAF50)
        : const Color(0xFFC41E3A);

    final remaining = (limit - count).clamp(0, limit);
    final progress = limit > 0 ? count / limit : 0.0;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: teamColor.withAlpha(15),
        border: Border.all(color: teamColor.withAlpha(80)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        children: [
          Icon(
            team == TeamType.taskForceOnyx
                ? Icons.military_tech
                : Icons.dark_mode,
            size: 28,
            color: teamColor,
          ),
          const SizedBox(height: 6),
          Text(team.displayName,
              style: TextStyle(
                  color: teamColor,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  letterSpacing: 1)),
          Text(team.displayNameJa,
              style: TextStyle(
                  color: teamColor.withAlpha(160), fontSize: 11)),
          const SizedBox(height: 16),

          // Count
          Text('$count',
              style: TextStyle(
                  color: teamColor,
                  fontSize: 48,
                  fontWeight: FontWeight.bold,
                  fontFamily: 'monospace')),
          Text('RESPAWNS USED',
              style: TextStyle(
                  color: teamColor.withAlpha(120),
                  fontSize: 9,
                  letterSpacing: 2)),

          const SizedBox(height: 10),

          // Progress bar
          ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: progress.clamp(0.0, 1.0),
              backgroundColor: teamColor.withAlpha(30),
              valueColor: AlwaysStoppedAnimation(teamColor),
              minHeight: 6,
            ),
          ),
          const SizedBox(height: 4),
          Text('$remaining remaining of $limit',
              style: const TextStyle(
                  color: Colors.white38, fontSize: 10)),

          const SizedBox(height: 16),

          // Respawn button — large, prominent
          SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton.icon(
              onPressed: count < limit ? onRespawn : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: teamColor.withAlpha(60),
                foregroundColor: teamColor,
                side: BorderSide(color: teamColor),
                disabledBackgroundColor:
                    Colors.white12,
                disabledForegroundColor:
                    Colors.white24,
              ),
              icon: const Icon(Icons.loop, size: 20),
              label: const Text('RESPAWN',
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 2)),
            ),
          ),
        ],
      ),
    );
  }
}
