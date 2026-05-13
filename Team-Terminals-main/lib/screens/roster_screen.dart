import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/models.dart';
import '../theme/app_themes.dart';
import '../widgets/window_frame.dart';

class RosterScreen extends StatelessWidget {
  const RosterScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return WindowFrame(
      title: 'Roster',
      onClose: () => Navigator.pop(context),
      child: const _RosterBody(),
    );
  }
}

class _RosterBody extends StatefulWidget {
  const _RosterBody();

  @override
  State<_RosterBody> createState() => _RosterBodyState();
}

class _RosterBodyState extends State<_RosterBody> {
  String? _selectedId;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final players = state.players;
    final isAdmin = state.isAdmin;

    return Row(
      children: [
        // ── Player list ───────────────────────────────────────────────
        Container(
          width: 220,
          decoration: BoxDecoration(
            border: Border(
                right: BorderSide(color: ext.taskbarBorderColor)),
          ),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                    border: Border(
                        bottom:
                            BorderSide(color: ext.taskbarBorderColor))),
                child: Row(
                  children: [
                    Icon(Icons.people,
                        size: 14, color: ext.iconGlowColor),
                    const SizedBox(width: 6),
                    Text('PERSONNEL (${players.length})',
                        style: TextStyle(
                            color: ext.iconGlowColor,
                            fontSize: 11,
                            letterSpacing: 1.5)),
                    const Spacer(),
                    if (isAdmin)
                      IconButton(
                        icon: const Icon(Icons.person_add, size: 16),
                        color: ext.accentColor,
                        onPressed: () =>
                            _showAddPlayerDialog(context, state),
                      ),
                  ],
                ),
              ),
              Expanded(
                child: players.isEmpty
                    ? const Center(
                        child: Text('No players.\nAdd one.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                                color: Colors.white38,
                                fontSize: 12)))
                    : ListView.builder(
                        itemCount: players.length,
                        itemBuilder: (ctx, i) {
                          final p = players[i];
                          final warnings = p.reports
                              .where((r) =>
                                  r.type == ReportType.warning ||
                                  r.type == ReportType.incident)
                              .length;
                          return ListTile(
                            dense: true,
                            selected: _selectedId == p.id,
                            selectedTileColor:
                                ext.iconGlowColor.withAlpha(30),
                            leading: CircleAvatar(
                              radius: 16,
                              backgroundColor:
                                  ext.iconGlowColor.withAlpha(40),
                              child: Text(
                                p.callsign.isNotEmpty
                                    ? p.callsign[0].toUpperCase()
                                    : '?',
                                style: TextStyle(
                                    color: ext.iconGlowColor,
                                    fontSize: 12),
                              ),
                            ),
                            title: Text(p.callsign,
                                style:
                                    const TextStyle(fontSize: 12)),
                            subtitle: Text(
                              '${p.team.displayName}${p.role.isNotEmpty ? '  •  ${p.role}' : ''}',
                              style:
                                  const TextStyle(fontSize: 10),
                            ),
                            trailing: warnings > 0
                                ? Container(
                                    padding:
                                        const EdgeInsets.all(4),
                                    decoration: const BoxDecoration(
                                      color: Color(0xFFFF6B35),
                                      shape: BoxShape.circle,
                                    ),
                                    child: Text('$warnings',
                                        style: const TextStyle(
                                            fontSize: 10,
                                            color: Colors.white)),
                                  )
                                : null,
                            onTap: () => setState(
                                () => _selectedId = p.id),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),

        // ── Player detail ─────────────────────────────────────────────
        Expanded(
          child: _selectedId == null
              ? Center(
                  child: Icon(Icons.person_outline,
                      size: 48,
                      color: ext.iconGlowColor.withAlpha(40)),
                )
              : _PlayerDetail(
                  player: players
                      .cast<Player?>()
                      .firstWhere((p) => p?.id == _selectedId,
                          orElse: () => null)!,
                  isAdmin: isAdmin,
                  onDelete: !isAdmin
                      ? null
                      : () async {
                          await state.removePlayer(_selectedId!);
                          setState(() => _selectedId = null);
                        },
                  onAddReport: !isAdmin
                      ? null
                      : (report) async {
                          await state.addReport(
                              _selectedId!, report);
                        },
                ),
        ),
      ],
    );
  }

  void _showAddPlayerDialog(BuildContext context, AppState state) {
    final nameCtrl = TextEditingController();
    final callCtrl = TextEditingController();
    final roleCtrl = TextEditingController();
    TeamType team = state.team;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => AlertDialog(
          title: const Text('ADD PLAYER'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(
                      labelText: 'Full Name')),
              const SizedBox(height: 8),
              TextField(
                  controller: callCtrl,
                  decoration: const InputDecoration(
                      labelText: 'Callsign')),
              const SizedBox(height: 8),
              TextField(
                  controller: roleCtrl,
                  decoration:
                      const InputDecoration(labelText: 'Role')),
              const SizedBox(height: 8),
              DropdownButtonFormField<TeamType>(
                value: team,
                decoration:
                    const InputDecoration(labelText: 'Team'),
                dropdownColor:
                    Theme.of(ctx).scaffoldBackgroundColor,
                items: TeamType.values
                    .map((t) => DropdownMenuItem(
                        value: t,
                        child: Text(t.displayName)))
                    .toList(),
                onChanged: (v) => setS(() => team = v!),
              ),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('CANCEL')),
            ElevatedButton(
              onPressed: () async {
                if (callCtrl.text.trim().isEmpty) return;
                await state.addPlayer(Player(
                  id: DateTime.now()
                      .millisecondsSinceEpoch
                      .toString(),
                  name: nameCtrl.text.trim(),
                  callsign: callCtrl.text.trim(),
                  team: team,
                  role: roleCtrl.text.trim(),
                ));
                if (ctx.mounted) Navigator.pop(ctx);
              },
              child: const Text('ADD'),
            ),
          ],
        ),
      ),
    );
  }
}

class _PlayerDetail extends StatelessWidget {
  const _PlayerDetail({
    required this.player,
    required this.isAdmin,
    this.onDelete,
    this.onAddReport,
  });
  final Player player;
  final bool isAdmin;
  final VoidCallback? onDelete;
  final void Function(PlayerReport)? onAddReport;

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: ext.iconGlowColor.withAlpha(40),
                child: Text(
                  player.callsign.isNotEmpty
                      ? player.callsign[0].toUpperCase()
                      : '?',
                  style: TextStyle(
                      color: ext.iconGlowColor,
                      fontSize: 22,
                      fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(player.callsign,
                        style: Theme.of(context)
                            .textTheme
                            .titleLarge),
                    Text(player.name,
                        style:
                            Theme.of(context).textTheme.bodyMedium),
                    Text(
                      '${player.team.displayName}${player.role.isNotEmpty ? '  •  ${player.role}' : ''}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              if (onDelete != null)
                IconButton(
                  icon: const Icon(Icons.delete_outline,
                      color: Colors.red),
                  onPressed: onDelete,
                ),
            ],
          ),

          const SizedBox(height: 20),
          Row(
            children: [
              Text('REPORTS',
                  style: TextStyle(
                      color: ext.accentColor,
                      fontSize: 10,
                      letterSpacing: 2)),
              const Spacer(),
              if (onAddReport != null)
                TextButton.icon(
                  onPressed: () =>
                      _showReportDialog(context),
                  icon: const Icon(Icons.add_comment, size: 14),
                  label: const Text('ADD REPORT'),
                ),
            ],
          ),
          const SizedBox(height: 8),

          if (player.reports.isEmpty)
            const Text('No reports on file.',
                style: TextStyle(
                    color: Colors.white38, fontSize: 12))
          else
            ...player.reports.reversed.map((r) => _ReportCard(r)),
        ],
      ),
    );
  }

  void _showReportDialog(BuildContext context) {
    ReportType type = ReportType.warning;
    final noteCtrl = TextEditingController();
    final byCtrl = TextEditingController(text: 'Admin');

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => AlertDialog(
          title: const Text('ADD REPORT'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<ReportType>(
                value: type,
                decoration:
                    const InputDecoration(labelText: 'Type'),
                dropdownColor:
                    Theme.of(ctx).scaffoldBackgroundColor,
                items: ReportType.values
                    .map((t) => DropdownMenuItem(
                        value: t,
                        child: Text(t.name.toUpperCase())))
                    .toList(),
                onChanged: (v) => setS(() => type = v!),
              ),
              const SizedBox(height: 8),
              TextField(
                  controller: noteCtrl,
                  maxLines: 3,
                  decoration:
                      const InputDecoration(labelText: 'Note')),
              const SizedBox(height: 8),
              TextField(
                  controller: byCtrl,
                  decoration:
                      const InputDecoration(labelText: 'Issued By')),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('CANCEL')),
            ElevatedButton(
              onPressed: () {
                onAddReport!(PlayerReport(
                  id: DateTime.now()
                      .millisecondsSinceEpoch
                      .toString(),
                  timestamp: DateTime.now(),
                  type: type,
                  note: noteCtrl.text.trim(),
                  issuedBy: byCtrl.text.trim(),
                ));
                Navigator.pop(ctx);
              },
              child: const Text('SUBMIT'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReportCard extends StatelessWidget {
  const _ReportCard(this.report);
  final PlayerReport report;

  @override
  Widget build(BuildContext context) {
    Color typeColor;
    IconData typeIcon;
    switch (report.type) {
      case ReportType.praise:
        typeColor = const Color(0xFF4CAF50);
        typeIcon = Icons.thumb_up_outlined;
        break;
      case ReportType.warning:
        typeColor = const Color(0xFFFF9800);
        typeIcon = Icons.warning_amber;
        break;
      case ReportType.incident:
        typeColor = const Color(0xFFF44336);
        typeIcon = Icons.gpp_bad_outlined;
        break;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: typeColor.withAlpha(20),
        border: Border.all(color: typeColor.withAlpha(80)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(typeIcon, size: 16, color: typeColor),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(report.type.name.toUpperCase(),
                        style: TextStyle(
                            color: typeColor,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1)),
                    const Spacer(),
                    Text(
                      '${report.timestamp.year}-${report.timestamp.month.toString().padLeft(2, '0')}-${report.timestamp.day.toString().padLeft(2, '0')}',
                      style: const TextStyle(
                          color: Colors.white38,
                          fontSize: 10),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(report.note,
                    style: const TextStyle(fontSize: 12)),
                Text('— ${report.issuedBy}',
                    style: const TextStyle(
                        color: Colors.white38,
                        fontSize: 10)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
