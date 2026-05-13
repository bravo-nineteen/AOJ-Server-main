import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/models.dart';
import '../theme/app_themes.dart';
import '../widgets/window_frame.dart';

class CommsLogScreen extends StatelessWidget {
  const CommsLogScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return WindowFrame(
      title: 'Comms Log',
      onClose: () => Navigator.pop(context),
      child: const _CommsBody(),
    );
  }
}

class _CommsBody extends StatefulWidget {
  const _CommsBody();

  @override
  State<_CommsBody> createState() => _CommsBodyState();
}

class _CommsBodyState extends State<_CommsBody> {
  final _msgCtrl = TextEditingController();
  final _senderCtrl = TextEditingController(text: 'Command');
  MessageType _type = MessageType.info;
  final _scrollCtrl = ScrollController();

  @override
  void dispose() {
    _msgCtrl.dispose();
    _senderCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _send(AppState state) async {
    final text = _msgCtrl.text.trim();
    if (text.isEmpty || state.activeGameFile == null) return;

    await state.addCommsMessage(
      state.activeGameFile!.id,
      CommsMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        timestamp: DateTime.now(),
        sender: _senderCtrl.text.trim().isNotEmpty
            ? _senderCtrl.text.trim()
            : 'Command',
        text: text,
        type: _type,
      ),
    );
    _msgCtrl.clear();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final file = state.activeGameFile;

    if (file == null) {
      return const Center(
        child: Text('No active game file.',
            style: TextStyle(color: Colors.white54)),
      );
    }

    final messages = file.commsLog;

    return Column(
      children: [
        // ── Message list ──────────────────────────────────────────────
        Expanded(
          child: messages.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.chat_bubble_outline,
                          size: 48,
                          color: ext.iconGlowColor.withAlpha(40)),
                      const SizedBox(height: 10),
                      const Text('No messages yet.',
                          style: TextStyle(color: Colors.white38)),
                    ],
                  ),
                )
              : ListView.builder(
                  controller: _scrollCtrl,
                  padding: const EdgeInsets.all(12),
                  itemCount: messages.length,
                  itemBuilder: (ctx, i) =>
                      _MessageTile(messages[i]),
                ),
        ),

        // ── Compose bar ───────────────────────────────────────────────
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: ext.taskbarColor,
            border: Border(
                top: BorderSide(color: ext.taskbarBorderColor)),
          ),
          child: Row(
            children: [
              // Sender name
              SizedBox(
                width: 110,
                child: TextField(
                  controller: _senderCtrl,
                  style: const TextStyle(fontSize: 12),
                  decoration: const InputDecoration(
                    labelText: 'From',
                    isDense: true,
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              // Message type
              DropdownButton<MessageType>(
                value: _type,
                dropdownColor:
                    Theme.of(context).scaffoldBackgroundColor,
                style:
                    const TextStyle(color: Colors.white, fontSize: 12),
                underline: Container(
                    height: 1, color: ext.iconGlowColor),
                items: MessageType.values
                    .map((t) => DropdownMenuItem(
                        value: t,
                        child: Row(
                          children: [
                            Icon(_typeIcon(t),
                                size: 14, color: _typeColor(t)),
                            const SizedBox(width: 4),
                            Text(t.name.toUpperCase(),
                                style: TextStyle(
                                    color: _typeColor(t),
                                    fontSize: 11)),
                          ],
                        )))
                    .toList(),
                onChanged: (v) => setState(() => _type = v!),
              ),
              const SizedBox(width: 8),
              // Text input
              Expanded(
                child: TextField(
                  controller: _msgCtrl,
                  style: const TextStyle(fontSize: 13),
                  decoration: const InputDecoration(
                    hintText: 'Message…',
                    isDense: true,
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  ),
                  onSubmitted: (_) => _send(state),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () => _send(state),
                icon: const Icon(Icons.send, size: 14),
                label: const Text('SEND'),
                style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 10)),
              ),
            ],
          ),
        ),
      ],
    );
  }

  IconData _typeIcon(MessageType t) {
    switch (t) {
      case MessageType.info:
        return Icons.info_outline;
      case MessageType.warning:
        return Icons.warning_amber;
      case MessageType.urgent:
        return Icons.priority_high;
    }
  }

  Color _typeColor(MessageType t) {
    switch (t) {
      case MessageType.info:
        return Colors.white70;
      case MessageType.warning:
        return const Color(0xFFFF9800);
      case MessageType.urgent:
        return const Color(0xFFF44336);
    }
  }
}

class _MessageTile extends StatelessWidget {
  const _MessageTile(this.msg);
  final CommsMessage msg;

  @override
  Widget build(BuildContext context) {
    Color col;
    IconData ico;
    switch (msg.type) {
      case MessageType.info:
        col = Colors.white54;
        ico = Icons.info_outline;
        break;
      case MessageType.warning:
        col = const Color(0xFFFF9800);
        ico = Icons.warning_amber;
        break;
      case MessageType.urgent:
        col = const Color(0xFFF44336);
        ico = Icons.priority_high;
        break;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: col.withAlpha(15),
        border: Border(left: BorderSide(color: col, width: 3)),
        borderRadius:
            const BorderRadius.horizontal(right: Radius.circular(4)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(ico, size: 14, color: col),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(msg.sender,
                        style: TextStyle(
                            color: col,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1)),
                    const Spacer(),
                    Text(
                      '${msg.timestamp.hour.toString().padLeft(2, '0')}:${msg.timestamp.minute.toString().padLeft(2, '0')}:${msg.timestamp.second.toString().padLeft(2, '0')}',
                      style: const TextStyle(
                          color: Colors.white24,
                          fontSize: 10,
                          fontFamily: 'monospace'),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(msg.text,
                    style: const TextStyle(
                        fontSize: 13, color: Colors.white70)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
