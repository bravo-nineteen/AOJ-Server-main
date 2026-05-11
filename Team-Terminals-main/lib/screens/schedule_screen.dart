import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/models.dart';
import '../theme/app_themes.dart';
import '../widgets/window_frame.dart';

class ScheduleScreen extends StatelessWidget {
  const ScheduleScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return WindowFrame(
      title: 'Schedule',
      onClose: () => Navigator.pop(context),
      child: const _ScheduleBody(),
    );
  }
}

class _ScheduleBody extends StatelessWidget {
  const _ScheduleBody();

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final ext = Theme.of(context).extension<AppThemeExtension>()!;

    if (state.activeGameFile == null) {
      return const Center(
        child: Text('No active game file selected.',
            style: TextStyle(color: Colors.white54)),
      );
    }

    final file = state.activeGameFile!;
    final isAdmin = state.isAdmin;

    return Column(
      children: [
        // ── Header ────────────────────────────────────────────────────
        Container(
          padding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: ext.taskbarColor,
            border: Border(
                bottom: BorderSide(color: ext.taskbarBorderColor)),
          ),
          child: Row(
            children: [
              Icon(Icons.calendar_today,
                  size: 16, color: ext.iconGlowColor),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${file.name}  •  ${file.date.year}-${file.date.month.toString().padLeft(2, '0')}-${file.date.day.toString().padLeft(2, '0')}',
                  style: TextStyle(
                      color: ext.iconGlowColor,
                      fontSize: 12,
                      letterSpacing: 1),
                ),
              ),
              if (isAdmin)
                ElevatedButton.icon(
                  onPressed: () => _showAddDialog(context, file.id, state),
                  icon: const Icon(Icons.add, size: 14),
                  label: const Text('ADD ENTRY'),
                  style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6)),
                ),
            ],
          ),
        ),

        // ── List ──────────────────────────────────────────────────────
        Expanded(
          child: file.schedule.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.event_note_outlined,
                          size: 48,
                          color: ext.iconGlowColor.withAlpha(60)),
                      const SizedBox(height: 12),
                      const Text('No schedule entries yet.',
                          style: TextStyle(color: Colors.white38)),
                    ],
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: file.schedule.length,
                  separatorBuilder: (_, __) => Divider(
                      color: ext.taskbarBorderColor.withAlpha(60)),
                  itemBuilder: (ctx, i) {
                    final entry = file.schedule[i];
                    return _ScheduleTile(
                      entry: entry,
                      isAdmin: isAdmin,
                      onDelete: () async {
                        file.schedule.removeAt(i);
                        await state.updateGameFile(file);
                      },
                    );
                  },
                ),
        ),
      ],
    );
  }

  void _showAddDialog(
      BuildContext context, String fileId, AppState state) {
    final titleEnCtrl = TextEditingController();
    final titleJaCtrl = TextEditingController();
    final timeCtrl = TextEditingController(text: '09:00');
    final notesCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('ADD SCHEDULE ENTRY'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: timeCtrl,
                decoration: const InputDecoration(
                    labelText: 'Time (e.g. 09:30)'),
              ),
              const SizedBox(height: 8),
              TextField(
                  controller: titleEnCtrl,
                  decoration: const InputDecoration(
                      labelText: 'Title (English)')),
              const SizedBox(height: 8),
              TextField(
                  controller: titleJaCtrl,
                  decoration:
                      const InputDecoration(labelText: 'タイトル (JP)')),
              const SizedBox(height: 8),
              TextField(
                  controller: notesCtrl,
                  maxLines: 2,
                  decoration:
                      const InputDecoration(labelText: 'Notes')),
            ],
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('CANCEL')),
          ElevatedButton(
            onPressed: () async {
              final file = state.gameFiles
                  .cast<GameFile?>()
                  .firstWhere((f) => f?.id == fileId,
                      orElse: () => null);
              if (file == null) return;
              final entry = ScheduleEntry(
                id: DateTime.now()
                    .millisecondsSinceEpoch
                    .toString(),
                titleEn: titleEnCtrl.text.trim(),
                titleJa: titleJaCtrl.text.trim(),
                timeLabel: timeCtrl.text.trim(),
                notes: notesCtrl.text.trim(),
              );
              file.schedule.add(entry);
              await state.updateGameFile(file);
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('ADD'),
          ),
        ],
      ),
    );
  }
}

class _ScheduleTile extends StatelessWidget {
  const _ScheduleTile({
    required this.entry,
    required this.isAdmin,
    required this.onDelete,
  });
  final ScheduleEntry entry;
  final bool isAdmin;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Time badge
        Container(
          width: 60,
          padding: const EdgeInsets.symmetric(vertical: 6),
          alignment: Alignment.center,
          child: Text(
            entry.timeLabel,
            style: TextStyle(
              color: ext.accentColor,
              fontWeight: FontWeight.bold,
              fontFamily: 'monospace',
              fontSize: 14,
            ),
          ),
        ),
        Container(
            width: 2,
            height: 50,
            color: ext.taskbarBorderColor.withAlpha(80),
            margin: const EdgeInsets.symmetric(horizontal: 10)),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(entry.titleEn,
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 14)),
              if (entry.titleJa.isNotEmpty)
                Text(entry.titleJa,
                    style: const TextStyle(
                        color: Colors.white54, fontSize: 12)),
              if (entry.notes.isNotEmpty)
                Text(entry.notes,
                    style: const TextStyle(
                        color: Colors.white38, fontSize: 11)),
            ],
          ),
        ),
        if (isAdmin)
          IconButton(
            icon: const Icon(Icons.delete_outline, size: 18),
            color: Colors.red.withAlpha(160),
            onPressed: onDelete,
          ),
      ],
    );
  }
}
