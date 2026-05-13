import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/models.dart';
import '../theme/app_themes.dart';
import '../widgets/window_frame.dart';

class MyComputerScreen extends StatelessWidget {
  const MyComputerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return WindowFrame(
      title: 'My Computer — Game Files',
      onClose: () => Navigator.pop(context),
      child: const _MyComputerBody(),
    );
  }
}

class _MyComputerBody extends StatefulWidget {
  const _MyComputerBody();

  @override
  State<_MyComputerBody> createState() => _MyComputerBodyState();
}

class _MyComputerBodyState extends State<_MyComputerBody> {
  String? _selected;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final files = state.gameFiles;
    final isAdmin = state.isAdmin;

    return Row(
      children: [
        // ── Sidebar: file list ────────────────────────────────────────
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
                      bottom: BorderSide(color: ext.taskbarBorderColor)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.folder, size: 16, color: ext.iconGlowColor),
                    const SizedBox(width: 6),
                    Text('GAME FILES',
                        style: TextStyle(
                            color: ext.iconGlowColor,
                            fontSize: 11,
                            letterSpacing: 2)),
                    const Spacer(),
                    if (isAdmin)
                      IconButton(
                        icon: const Icon(Icons.add, size: 18),
                        color: ext.accentColor,
                        tooltip: 'New Game File',
                        onPressed: () => _showNewFileDialog(context),
                      ),
                  ],
                ),
              ),
              Expanded(
                child: files.isEmpty
                    ? Center(
                        child: Text('No files.\nCreate one to begin.',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                                color: Colors.white38,
                                fontSize: 12)),
                      )
                    : ListView.builder(
                        itemCount: files.length,
                        itemBuilder: (ctx, i) {
                          final f = files[i];
                          final isActive =
                              state.activeGameFile?.id == f.id;
                          final isSel = _selected == f.id;
                          return ListTile(
                            dense: true,
                            selected: isSel,
                            selectedTileColor:
                                ext.iconGlowColor.withAlpha(30),
                            leading: Icon(
                              isActive
                                  ? Icons.folder_open
                                  : Icons.folder_outlined,
                              size: 20,
                              color: isActive
                                  ? ext.accentColor
                                  : ext.iconGlowColor,
                            ),
                            title: Text(f.name,
                                style: const TextStyle(
                                    fontSize: 12)),
                            subtitle: Text(
                              '${f.date.year}-${f.date.month.toString().padLeft(2, '0')}-${f.date.day.toString().padLeft(2, '0')}',
                              style: const TextStyle(fontSize: 10),
                            ),
                            trailing: isActive
                                ? Icon(Icons.radio_button_checked,
                                    size: 14,
                                    color: ext.accentColor)
                                : null,
                            onTap: () =>
                                setState(() => _selected = f.id),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),

        // ── Detail pane ───────────────────────────────────────────────
        Expanded(
          child: _selected == null
              ? _EmptyDetail(ext: ext)
              : _FileDetail(
                  file: files
                      .cast<GameFile?>()
                      .firstWhere((f) => f?.id == _selected,
                          orElse: () => null)!,
                  isAdmin: isAdmin,
                  isActive:
                      state.activeGameFile?.id == _selected,
                  onSetActive: () async {
                    await state.setActiveGameFile(
                        _selected == state.activeGameFile?.id
                            ? null
                            : _selected);
                  },
                  onDelete: !isAdmin
                      ? null
                      : () async {
                          await state
                              .removeGameFile(_selected!);
                          setState(() => _selected = null);
                        },
                ),
        ),
      ],
    );
  }

  void _showNewFileDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    final locEnCtrl = TextEditingController();
    final locJaCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('NEW GAME FILE'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
                controller: nameCtrl,
                decoration:
                    const InputDecoration(labelText: 'Event Name')),
            const SizedBox(height: 8),
            TextField(
                controller: locEnCtrl,
                decoration:
                    const InputDecoration(labelText: 'Location (EN)')),
            const SizedBox(height: 8),
            TextField(
                controller: locJaCtrl,
                decoration:
                    const InputDecoration(labelText: '場所 (JP)')),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('CANCEL')),
          ElevatedButton(
            onPressed: () async {
              if (nameCtrl.text.trim().isEmpty) return;
              final file = GameFile(
                id: DateTime.now().millisecondsSinceEpoch.toString(),
                name: nameCtrl.text.trim(),
                date: DateTime.now(),
                locationEn: locEnCtrl.text.trim(),
                locationJa: locJaCtrl.text.trim(),
              );
              await context.read<AppState>().addGameFile(file);
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('CREATE'),
          ),
        ],
      ),
    );
  }
}

class _EmptyDetail extends StatelessWidget {
  const _EmptyDetail({required this.ext});
  final AppThemeExtension ext;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.touch_app_outlined,
              size: 48, color: ext.iconGlowColor.withAlpha(60)),
          const SizedBox(height: 12),
          const Text('Select a game file',
              style: TextStyle(color: Colors.white38)),
        ],
      ),
    );
  }
}

class _FileDetail extends StatelessWidget {
  const _FileDetail({
    required this.file,
    required this.isAdmin,
    required this.isActive,
    required this.onSetActive,
    this.onDelete,
  });
  final GameFile file;
  final bool isAdmin;
  final bool isActive;
  final VoidCallback onSetActive;
  final VoidCallback? onDelete;

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
              Icon(Icons.folder_special,
                  size: 32, color: ext.iconGlowColor),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(file.name,
                        style: Theme.of(context)
                            .textTheme
                            .titleLarge),
                    Text(
                      '${file.date.year}-${file.date.month.toString().padLeft(2, '0')}-${file.date.day.toString().padLeft(2, '0')}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _Row('Location', '${file.locationEn}  ${file.locationJa}'),
          _Row('Sessions', '${file.sessions.length} recorded'),
          _Row('Schedule', '${file.schedule.length} entries'),
          _Row('Comms', '${file.commsLog.length} messages'),
          _Row('Map image', file.fieldMap.imagePath ?? 'Not set'),
          const SizedBox(height: 20),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              ElevatedButton.icon(
                onPressed: onSetActive,
                icon: Icon(isActive
                    ? Icons.radio_button_checked
                    : Icons.radio_button_unchecked),
                label: Text(
                    isActive ? 'DEACTIVATE' : 'SET ACTIVE'),
              ),
              if (onDelete != null)
                OutlinedButton.icon(
                  onPressed: () {
                    showDialog(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text('DELETE FILE'),
                        content: Text(
                            'Delete "${file.name}"? This cannot be undone.'),
                        actions: [
                          TextButton(
                              onPressed: () => Navigator.pop(ctx),
                              child: const Text('CANCEL')),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.red),
                            onPressed: () {
                              Navigator.pop(ctx);
                              onDelete!();
                            },
                            child: const Text('DELETE'),
                          ),
                        ],
                      ),
                    );
                  },
                  icon: const Icon(Icons.delete_outline,
                      color: Colors.red),
                  label: const Text('DELETE',
                      style: TextStyle(color: Colors.red)),
                  style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Colors.red)),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text('$label:',
                style: const TextStyle(
                    color: Colors.white38, fontSize: 12)),
          ),
          Expanded(
            child: Text(value,
                style: const TextStyle(
                    color: Colors.white70, fontSize: 12)),
          ),
        ],
      ),
    );
  }
}
