import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/models.dart';
import '../theme/app_themes.dart';
import '../widgets/window_frame.dart';

class IntelScreen extends StatelessWidget {
  const IntelScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return WindowFrame(
      title: 'Intel Briefing',
      onClose: () => Navigator.pop(context),
      child: const _IntelBody(),
    );
  }
}

class _IntelBody extends StatelessWidget {
  const _IntelBody();

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    if (state.activeGameFile == null) {
      return const Center(
          child: Text('No active game file.',
              style: TextStyle(color: Colors.white54)));
    }
    final map = state.activeGameFile!.fieldMap;
    final ext = Theme.of(context).extension<AppThemeExtension>()!;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Mission header
          Row(
            children: [
              Icon(Icons.article_outlined,
                  size: 28, color: ext.iconGlowColor),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      state.activeGameFile!.name.toUpperCase(),
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    Text(
                      '${state.activeGameFile!.locationEn}  ${state.activeGameFile!.locationJa}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
          Divider(
              color: ext.taskbarBorderColor,
              height: 28,
              thickness: 1),

          _Section(
            title: 'MISSION BRIEFING',
            enText: map.briefingEn,
            jaText: map.briefingJa,
            icon: Icons.assignment_outlined,
            ext: ext,
          ),
          _Section(
            title: 'OBJECTIVE',
            enText: map.objectiveEn,
            jaText: map.objectiveJa,
            icon: Icons.gps_fixed,
            ext: ext,
          ),
          _Section(
            title: 'RESPAWN RULES',
            enText: map.respawnRulesEn,
            jaText: map.respawnRulesJa,
            icon: Icons.loop,
            ext: ext,
          ),
          _Section(
            title: 'FIRE SELECTOR',
            enText: map.fireSelectorEn,
            jaText: map.fireSelectorJa,
            icon: Icons.local_fire_department_outlined,
            ext: ext,
          ),

          const SizedBox(height: 8),
          Text(
            'Edit these fields via Field Map → Rules & Briefing.',
            style: TextStyle(
                color: ext.iconGlowColor.withAlpha(60),
                fontSize: 11,
                fontStyle: FontStyle.italic),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    required this.enText,
    required this.jaText,
    required this.icon,
    required this.ext,
  });
  final String title;
  final String enText;
  final String jaText;
  final IconData icon;
  final AppThemeExtension ext;

  @override
  Widget build(BuildContext context) {
    if (enText.isEmpty && jaText.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: ext.accentColor),
            const SizedBox(width: 6),
            Text(title,
                style: TextStyle(
                    color: ext.accentColor,
                    fontSize: 10,
                    letterSpacing: 2,
                    fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        if (enText.isNotEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: ext.taskbarColor,
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: ext.taskbarBorderColor),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(enText,
                    style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 14,
                        height: 1.5)),
                if (jaText.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(jaText,
                      style: const TextStyle(
                          color: Colors.white38,
                          fontSize: 13,
                          height: 1.4)),
                ],
              ],
            ),
          ),
        const SizedBox(height: 16),
      ],
    );
  }
}
