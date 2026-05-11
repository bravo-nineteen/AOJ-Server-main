import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/models.dart';
import '../theme/app_themes.dart';
import '../widgets/window_frame.dart';

class DevicesScreen extends StatelessWidget {
  const DevicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return WindowFrame(
      title: 'Devices & Props',
      onClose: () => Navigator.pop(context),
      child: const _DevicesBody(),
    );
  }
}

class _DevicesBody extends StatefulWidget {
  const _DevicesBody();

  @override
  State<_DevicesBody> createState() => _DevicesBodyState();
}

class _DevicesBodyState extends State<_DevicesBody> {
  String? _selectedId;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final devices = state.devices;
    final isAdmin = state.isAdmin;

    return Row(
      children: [
        // ── Device list ───────────────────────────────────────────────
        Container(
          width: 200,
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
                    Icon(Icons.router,
                        size: 14, color: ext.iconGlowColor),
                    const SizedBox(width: 6),
                    Text('DEVICES',
                        style: TextStyle(
                            color: ext.iconGlowColor,
                            fontSize: 11,
                            letterSpacing: 2)),
                    const Spacer(),
                    if (isAdmin)
                      IconButton(
                        icon: const Icon(Icons.add, size: 16),
                        color: ext.accentColor,
                        tooltip: 'Add Device',
                        onPressed: () =>
                            _showAddDialog(context, state),
                      ),
                  ],
                ),
              ),
              Expanded(
                child: devices.isEmpty
                    ? const Center(
                        child: Text('No devices.\nAdd one.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                                color: Colors.white38,
                                fontSize: 12)),
                      )
                    : ListView.builder(
                        itemCount: devices.length,
                        itemBuilder: (ctx, i) {
                          final d = devices[i];
                          return ListTile(
                            dense: true,
                            selected: _selectedId == d.id,
                            selectedTileColor:
                                ext.iconGlowColor.withAlpha(30),
                            leading: Icon(
                              _deviceIcon(d.typeName),
                              size: 18,
                              color: ext.iconGlowColor,
                            ),
                            title: Text(d.name,
                                style:
                                    const TextStyle(fontSize: 12)),
                            subtitle: Text(d.typeName,
                                style: const TextStyle(
                                    fontSize: 10)),
                            onTap: () => setState(
                                () => _selectedId = d.id),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),

        // ── Detail ────────────────────────────────────────────────────
        Expanded(
          child: _selectedId == null
              ? Center(
                  child: Icon(Icons.router_outlined,
                      size: 48,
                      color: ext.iconGlowColor.withAlpha(40)),
                )
              : _DeviceDetail(
                  device: devices
                      .cast<DeviceInfo?>()
                      .firstWhere((d) => d?.id == _selectedId,
                          orElse: () => null)!,
                  isAdmin: isAdmin,
                  onDelete: !isAdmin
                      ? null
                      : () async {
                          await state
                              .removeDevice(_selectedId!);
                          setState(() => _selectedId = null);
                        },
                ),
        ),
      ],
    );
  }

  IconData _deviceIcon(String type) {
    final t = type.toLowerCase();
    if (t.contains('mine') || t.contains('bomb')) return Icons.warning_amber;
    if (t.contains('flag')) return Icons.flag;
    if (t.contains('timer')) return Icons.timer;
    if (t.contains('buzzer') || t.contains('alarm')) return Icons.notifications;
    if (t.contains('camera')) return Icons.videocam;
    return Icons.router;
  }

  void _showAddDialog(BuildContext context, AppState state) {
    final nameCtrl = TextEditingController();
    final typeCtrl = TextEditingController();
    final descEnCtrl = TextEditingController();
    final descJaCtrl = TextEditingController();
    final useEnCtrl = TextEditingController();
    final useJaCtrl = TextEditingController();
    final funcCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('ADD DEVICE'),
        content: SizedBox(
          width: 360,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                    controller: nameCtrl,
                    decoration:
                        const InputDecoration(labelText: 'Name')),
                const SizedBox(height: 8),
                TextField(
                    controller: typeCtrl,
                    decoration: const InputDecoration(
                        labelText: 'Type (mine, flag, timer…)')),
                const SizedBox(height: 8),
                TextField(
                    controller: descEnCtrl,
                    maxLines: 2,
                    decoration: const InputDecoration(
                        labelText: 'Description (EN)')),
                const SizedBox(height: 8),
                TextField(
                    controller: descJaCtrl,
                    maxLines: 2,
                    decoration: const InputDecoration(
                        labelText: '説明 (JP)')),
                const SizedBox(height: 8),
                TextField(
                    controller: useEnCtrl,
                    maxLines: 2,
                    decoration: const InputDecoration(
                        labelText: 'How to Use (EN)')),
                const SizedBox(height: 8),
                TextField(
                    controller: useJaCtrl,
                    maxLines: 2,
                    decoration: const InputDecoration(
                        labelText: '使用方法 (JP)')),
                const SizedBox(height: 8),
                TextField(
                    controller: funcCtrl,
                    maxLines: 2,
                    decoration: const InputDecoration(
                        labelText: 'Functions / Notes')),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('CANCEL')),
          ElevatedButton(
            onPressed: () async {
              if (nameCtrl.text.trim().isEmpty) return;
              await state.addDevice(DeviceInfo(
                id: DateTime.now()
                    .millisecondsSinceEpoch
                    .toString(),
                name: nameCtrl.text.trim(),
                typeName: typeCtrl.text.trim(),
                descriptionEn: descEnCtrl.text.trim(),
                descriptionJa: descJaCtrl.text.trim(),
                howToUseEn: useEnCtrl.text.trim(),
                howToUseJa: useJaCtrl.text.trim(),
                functions: funcCtrl.text.trim(),
              ));
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('ADD'),
          ),
        ],
      ),
    );
  }
}

class _DeviceDetail extends StatelessWidget {
  const _DeviceDetail(
      {required this.device, required this.isAdmin, this.onDelete});
  final DeviceInfo device;
  final bool isAdmin;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;

    Widget section(String title, String enText, String jaText) {
      if (enText.isEmpty && jaText.isEmpty) return const SizedBox.shrink();
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 14),
          Text(title.toUpperCase(),
              style: TextStyle(
                  color: ext.accentColor,
                  fontSize: 10,
                  letterSpacing: 2)),
          const SizedBox(height: 6),
          if (enText.isNotEmpty)
            Text(enText,
                style: const TextStyle(
                    color: Colors.white70, fontSize: 13)),
          if (jaText.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(jaText,
                style: const TextStyle(
                    color: Colors.white38, fontSize: 12)),
          ],
        ],
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.router, size: 28, color: ext.iconGlowColor),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(device.name,
                        style:
                            Theme.of(context).textTheme.titleLarge),
                    Text(device.typeName,
                        style:
                            Theme.of(context).textTheme.bodySmall),
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
          section('Description', device.descriptionEn,
              device.descriptionJa),
          section('How to Use', device.howToUseEn,
              device.howToUseJa),
          if (device.functions.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text('FUNCTIONS',
                style: TextStyle(
                    color: ext.accentColor,
                    fontSize: 10,
                    letterSpacing: 2)),
            const SizedBox(height: 6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: ext.taskbarColor,
                border:
                    Border.all(color: ext.taskbarBorderColor),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(device.functions,
                  style: const TextStyle(
                      color: Colors.white60,
                      fontFamily: 'monospace',
                      fontSize: 12)),
            ),
          ],
        ],
      ),
    );
  }
}
