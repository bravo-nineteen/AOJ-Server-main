import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import '../providers/app_state.dart';
import '../models/models.dart';
import '../theme/app_themes.dart';
import '../widgets/window_frame.dart';

class FieldMapScreen extends StatefulWidget {
  const FieldMapScreen({super.key});

  @override
  State<FieldMapScreen> createState() => _FieldMapScreenState();
}

class _FieldMapScreenState extends State<FieldMapScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    return WindowFrame(
      title: 'Field Map',
      onClose: () => Navigator.pop(context),
      child: Column(
        children: [
          TabBar(
            controller: _tabs,
            indicatorColor: ext.iconGlowColor,
            labelColor: ext.iconGlowColor,
            unselectedLabelColor: Colors.white54,
            tabs: const [
              Tab(text: 'MAP & DRAWING'),
              Tab(text: 'RULES & BRIEFING'),
            ],
          ),
          Expanded(
            child: TabBarView(
              controller: _tabs,
              children: const [
                _MapTab(),
                _RulesTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── MAP TAB ─────────────────────────────────────────────────────────────────

class _MapTab extends StatefulWidget {
  const _MapTab();

  @override
  State<_MapTab> createState() => _MapTabState();
}

class _MapTabState extends State<_MapTab> {
  bool _drawMode = false;
  Color _brushColor = Colors.red;
  double _brushWidth = 3.0;
  DrawStroke? _currentStroke;
  MapMarkerType _markerType = MapMarkerType.respawnA;
  bool _showLabels = true;

  bool get _isAdmin => context.read<AppState>().isAdmin;
  String? get _fileId => context.read<AppState>().activeGameFile?.id;
  FieldMapData? get _map =>
      context.read<AppState>().activeGameFile?.fieldMap;

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final img = await picker.pickImage(source: ImageSource.gallery);
    if (img == null || _fileId == null) return;
    final updated = FieldMapData(
      imagePath: img.path,
      markers: _map?.markers ?? [],
      strokes: _map?.strokes ?? [],
      briefingEn: _map?.briefingEn ?? '',
      briefingJa: _map?.briefingJa ?? '',
      respawnRulesEn: _map?.respawnRulesEn ?? '',
      respawnRulesJa: _map?.respawnRulesJa ?? '',
      fireSelectorEn: _map?.fireSelectorEn ?? 'Semi-auto only',
      fireSelectorJa: _map?.fireSelectorJa ?? 'セミオートのみ',
      objectiveEn: _map?.objectiveEn ?? '',
      objectiveJa: _map?.objectiveJa ?? '',
    );
    await context.read<AppState>().updateFieldMap(_fileId!, updated);
  }

  void _onPanStart(DragStartDetails d, Size canvasSize) {
    if (!_drawMode || !_isAdmin) return;
    final norm = _normalize(d.localPosition, canvasSize);
    setState(() {
      _currentStroke = DrawStroke(
          points: [norm], color: _brushColor, width: _brushWidth);
    });
  }

  void _onPanUpdate(DragUpdateDetails d, Size canvasSize) {
    if (!_drawMode || !_isAdmin || _currentStroke == null) return;
    final norm = _normalize(d.localPosition, canvasSize);
    setState(() => _currentStroke!.points.add(norm));
  }

  Future<void> _onPanEnd(DragEndDetails _, Size canvasSize) async {
    if (!_drawMode || !_isAdmin || _currentStroke == null) return;
    if (_fileId == null) return;
    final strokes = List<DrawStroke>.from(_map?.strokes ?? [])
      ..add(_currentStroke!);
    await _saveMap(strokes: strokes);
    setState(() => _currentStroke = null);
  }

  Future<void> _onTapForMarker(
      TapDownDetails d, Size canvasSize) async {
    if (_drawMode || !_isAdmin || _fileId == null) return;
    final norm = _normalize(d.localPosition, canvasSize);
    _showMarkerDialog(norm);
  }

  void _showMarkerDialog(Offset pos) {
    final labelEnCtrl = TextEditingController();
    final labelJaCtrl = TextEditingController();
    TeamType? team;
    MapMarkerType type = _markerType;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setS) {
        final ext = Theme.of(ctx).extension<AppThemeExtension>()!;
        return AlertDialog(
          title: const Text('ADD MARKER'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<MapMarkerType>(
                  value: type,
                  decoration:
                      const InputDecoration(labelText: 'Marker Type'),
                  items: MapMarkerType.values
                      .map((t) => DropdownMenuItem(
                          value: t,
                          child: Text(_markerTypeLabel(t))))
                      .toList(),
                  onChanged: (v) => setS(() => type = v!),
                  dropdownColor: Theme.of(ctx).scaffoldBackgroundColor,
                ),
                const SizedBox(height: 10),
                if (type == MapMarkerType.respawnA ||
                    type == MapMarkerType.respawnB)
                  DropdownButtonFormField<TeamType>(
                    value: team,
                    decoration:
                        const InputDecoration(labelText: 'Team'),
                    items: TeamType.values
                        .map((t) => DropdownMenuItem(
                            value: t, child: Text(t.displayName)))
                        .toList(),
                    onChanged: (v) => setS(() => team = v),
                    dropdownColor:
                        Theme.of(ctx).scaffoldBackgroundColor,
                  ),
                const SizedBox(height: 10),
                TextField(
                  controller: labelEnCtrl,
                  decoration:
                      const InputDecoration(labelText: 'Label (English)'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: labelJaCtrl,
                  decoration:
                      const InputDecoration(labelText: 'ラベル (Japanese)'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('CANCEL')),
            ElevatedButton(
              onPressed: () async {
                Navigator.pop(ctx);
                final marker = MapMarker(
                  id: DateTime.now().millisecondsSinceEpoch.toString(),
                  x: pos.dx,
                  y: pos.dy,
                  type: type,
                  labelEn: labelEnCtrl.text.trim(),
                  labelJa: labelJaCtrl.text.trim(),
                  team: team,
                );
                final markers =
                    List<MapMarker>.from(_map?.markers ?? [])
                      ..add(marker);
                await _saveMap(markers: markers);
              },
              child: const Text('ADD'),
            ),
          ],
        );
      }),
    );
  }

  Future<void> _clearDrawing() async {
    await _saveMap(strokes: []);
  }

  Future<void> _clearMarkers() async {
    await _saveMap(markers: []);
  }

  Future<void> _saveMap({
    List<DrawStroke>? strokes,
    List<MapMarker>? markers,
  }) async {
    if (_fileId == null) return;
    final current = _map ?? FieldMapData();
    final updated = FieldMapData(
      imagePath: current.imagePath,
      markers: markers ?? current.markers,
      strokes: strokes ?? current.strokes,
      briefingEn: current.briefingEn,
      briefingJa: current.briefingJa,
      respawnRulesEn: current.respawnRulesEn,
      respawnRulesJa: current.respawnRulesJa,
      fireSelectorEn: current.fireSelectorEn,
      fireSelectorJa: current.fireSelectorJa,
      objectiveEn: current.objectiveEn,
      objectiveJa: current.objectiveJa,
    );
    await context.read<AppState>().updateFieldMap(_fileId!, updated);
    setState(() {});
  }

  Offset _normalize(Offset local, Size size) =>
      Offset(local.dx / size.width, local.dy / size.height);

  String _markerTypeLabel(MapMarkerType t) {
    switch (t) {
      case MapMarkerType.respawnA:
        return 'Respawn (A)';
      case MapMarkerType.respawnB:
        return 'Respawn (B)';
      case MapMarkerType.objective:
        return 'Objective';
      case MapMarkerType.extraction:
        return 'Extraction Zone';
      case MapMarkerType.danger:
        return 'Danger / No-Go';
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final ext = Theme.of(context).extension<AppThemeExtension>()!;
    final map = state.activeGameFile?.fieldMap;
    final isAdmin = state.isAdmin;

    if (state.activeGameFile == null) {
      return _NoFileSelected(isAdmin: isAdmin);
    }

    return Column(
      children: [
        // ── Toolbar ──────────────────────────────────────────────────────
        if (isAdmin)
          Container(
            color: ext.taskbarColor,
            padding:
                const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            child: Row(
              children: [
                // Draw / Select toggle
                _ToolBtn(
                  icon: _drawMode
                      ? Icons.touch_app
                      : Icons.edit,
                  label: _drawMode ? 'Place Marker' : 'Draw',
                  active: true,
                  color: ext.iconGlowColor,
                  onTap: () => setState(() => _drawMode = !_drawMode),
                ),
                const SizedBox(width: 8),
                if (_drawMode) ...[
                  // Brush colours
                  ...[Colors.red, Colors.green, Colors.blue, Colors.yellow, Colors.white]
                      .map((c) => GestureDetector(
                            onTap: () => setState(() => _brushColor = c),
                            child: Container(
                              width: 22,
                              height: 22,
                              margin:
                                  const EdgeInsets.symmetric(horizontal: 3),
                              decoration: BoxDecoration(
                                color: c,
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: _brushColor == c
                                      ? Colors.white
                                      : Colors.transparent,
                                  width: 2,
                                ),
                              ),
                            ),
                          )),
                  const SizedBox(width: 8),
                  // Brush width
                  const Text('Width:',
                      style: TextStyle(
                          color: Colors.white54, fontSize: 11)),
                  Slider(
                    value: _brushWidth,
                    min: 1,
                    max: 12,
                    divisions: 11,
                    onChanged: (v) =>
                        setState(() => _brushWidth = v),
                    activeColor: ext.iconGlowColor,
                  ),
                  _ToolBtn(
                    icon: Icons.delete_sweep,
                    label: 'Clear Drawing',
                    active: false,
                    color: Colors.orange,
                    onTap: _clearDrawing,
                  ),
                ] else ...[
                  // Marker type selector
                  DropdownButton<MapMarkerType>(
                    value: _markerType,
                    dropdownColor:
                        Theme.of(context).scaffoldBackgroundColor,
                    style: const TextStyle(
                        color: Colors.white, fontSize: 12),
                    underline: Container(
                        height: 1, color: ext.iconGlowColor),
                    items: MapMarkerType.values
                        .map((t) => DropdownMenuItem(
                            value: t,
                            child: Text(_markerTypeLabel(t))))
                        .toList(),
                    onChanged: (v) =>
                        setState(() => _markerType = v!),
                  ),
                  const SizedBox(width: 8),
                  _ToolBtn(
                    icon: Icons.layers_clear,
                    label: 'Clear Markers',
                    active: false,
                    color: Colors.orange,
                    onTap: _clearMarkers,
                  ),
                ],
                const Spacer(),
                _ToolBtn(
                  icon: Icons.image_outlined,
                  label: 'Upload Map',
                  active: false,
                  color: ext.accentColor,
                  onTap: _pickImage,
                ),
                Switch(
                  value: _showLabels,
                  onChanged: (v) => setState(() => _showLabels = v),
                  activeColor: ext.iconGlowColor,
                ),
                const Text('Labels',
                    style:
                        TextStyle(color: Colors.white54, fontSize: 11)),
              ],
            ),
          ),

        // ── Map canvas ───────────────────────────────────────────────────
        Expanded(
          child: map == null ||
                  (map.imagePath == null &&
                      map.markers.isEmpty &&
                      map.strokes.isEmpty)
              ? _NoMapImage(isAdmin: isAdmin, onUpload: _pickImage)
              : LayoutBuilder(
                  builder: (context, constraints) {
                    final size = Size(
                        constraints.maxWidth, constraints.maxHeight);
                    return GestureDetector(
                      onPanStart: (d) => _onPanStart(d, size),
                      onPanUpdate: (d) => _onPanUpdate(d, size),
                      onPanEnd: (d) => _onPanEnd(d, size),
                      onTapDown: (d) =>
                          _onTapForMarker(d, size),
                      child: Stack(
                        children: [
                          // Map image
                          if (map.imagePath != null)
                            Positioned.fill(
                              child: Image.file(
                                File(map.imagePath!),
                                fit: BoxFit.contain,
                                errorBuilder: (_, __, ___) =>
                                    const Center(
                                        child: Icon(Icons.broken_image,
                                            size: 60,
                                            color: Colors.white24)),
                              ),
                            )
                          else
                            Container(color: const Color(0xFF0A180A)),

                          // Strokes + markers overlay
                          Positioned.fill(
                            child: CustomPaint(
                              painter: _MapPainter(
                                strokes: map.strokes,
                                currentStroke: _currentStroke,
                                markers: map.markers,
                                showLabels: _showLabels,
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }
}

class _ToolBtn extends StatelessWidget {
  const _ToolBtn({
    required this.icon,
    required this.label,
    required this.active,
    required this.color,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final bool active;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: 4),
            Text(label,
                style: TextStyle(color: color, fontSize: 11)),
          ],
        ),
      ),
    );
  }
}

class _NoFileSelected extends StatelessWidget {
  const _NoFileSelected({required this.isAdmin});
  final bool isAdmin;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.folder_off_outlined,
              size: 56, color: Colors.white24),
          const SizedBox(height: 12),
          const Text('No active game file selected.',
              style: TextStyle(color: Colors.white54)),
          const SizedBox(height: 8),
          const Text(
              'Go to My Computer and set a game file as active.',
              style: TextStyle(color: Colors.white38, fontSize: 12)),
        ],
      ),
    );
  }
}

class _NoMapImage extends StatelessWidget {
  const _NoMapImage({required this.isAdmin, required this.onUpload});
  final bool isAdmin;
  final VoidCallback onUpload;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.map_outlined, size: 56, color: Colors.white24),
          const SizedBox(height: 12),
          const Text('No map image uploaded.',
              style: TextStyle(color: Colors.white54)),
          if (isAdmin) ...[
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: onUpload,
              icon: const Icon(Icons.upload),
              label: const Text('UPLOAD MAP IMAGE'),
            ),
          ],
        ],
      ),
    );
  }
}

// ─── MAP PAINTER ─────────────────────────────────────────────────────────────

class _MapPainter extends CustomPainter {
  final List<DrawStroke> strokes;
  final DrawStroke? currentStroke;
  final List<MapMarker> markers;
  final bool showLabels;

  _MapPainter({
    required this.strokes,
    required this.currentStroke,
    required this.markers,
    required this.showLabels,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Draw completed strokes
    for (final stroke in [...strokes, if (currentStroke != null) currentStroke!]) {
      if (stroke.points.length < 2) continue;
      final paint = Paint()
        ..color = stroke.color
        ..strokeWidth = stroke.width
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..style = PaintingStyle.stroke;
      final path = Path();
      final pts = stroke.points
          .map((p) => Offset(p.dx * size.width, p.dy * size.height))
          .toList();
      path.moveTo(pts.first.dx, pts.first.dy);
      for (int i = 1; i < pts.length; i++) {
        path.lineTo(pts[i].dx, pts[i].dy);
      }
      canvas.drawPath(path, paint);
    }

    // Draw markers
    for (final marker in markers) {
      final pos = Offset(marker.x * size.width, marker.y * size.height);
      _drawMarker(canvas, pos, marker);
    }
  }

  void _drawMarker(Canvas canvas, Offset pos, MapMarker marker) {
    Color baseColor;
    IconData? symbol;

    if (marker.team != null) {
      baseColor = marker.team == TeamType.taskForceOnyx
          ? const Color(0xFF4CAF50)
          : const Color(0xFFC41E3A);
    } else {
      switch (marker.type) {
        case MapMarkerType.respawnA:
          baseColor = const Color(0xFF4CAF50);
          break;
        case MapMarkerType.respawnB:
          baseColor = const Color(0xFFFF9800);
          break;
        case MapMarkerType.objective:
          baseColor = const Color(0xFFFFEB3B);
          break;
        case MapMarkerType.extraction:
          baseColor = const Color(0xFF00BCD4);
          break;
        case MapMarkerType.danger:
          baseColor = const Color(0xFFF44336);
          break;
      }
    }

    // Outer glow
    canvas.drawCircle(
      pos,
      22,
      Paint()..color = baseColor.withAlpha(50)..style = PaintingStyle.fill,
    );

    // Fill
    canvas.drawCircle(
      pos,
      18,
      Paint()..color = baseColor.withAlpha(200)..style = PaintingStyle.fill,
    );

    // Border
    canvas.drawCircle(
      pos,
      18,
      Paint()
        ..color = Colors.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );

    // Label
    if (showLabels) {
      final label = marker.labelEn.isNotEmpty
          ? marker.labelEn
          : _markerShortName(marker.type);
      final tp = TextPainter(
        text: TextSpan(
          text: label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 9,
            fontWeight: FontWeight.bold,
            shadows: [Shadow(color: Colors.black, blurRadius: 3)],
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: 60);
      tp.paint(canvas,
          Offset(pos.dx - tp.width / 2, pos.dy - tp.height / 2));

      // Japanese sub-label below circle
      if (marker.labelJa.isNotEmpty) {
        final tpJa = TextPainter(
          text: TextSpan(
            text: marker.labelJa,
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 8,
              shadows: [Shadow(color: Colors.black, blurRadius: 3)],
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout(maxWidth: 80);
        tpJa.paint(canvas,
            Offset(pos.dx - tpJa.width / 2, pos.dy + 20));
      }
    }
  }

  String _markerShortName(MapMarkerType t) {
    switch (t) {
      case MapMarkerType.respawnA:
        return 'RS-A';
      case MapMarkerType.respawnB:
        return 'RS-B';
      case MapMarkerType.objective:
        return 'OBJ';
      case MapMarkerType.extraction:
        return 'EXT';
      case MapMarkerType.danger:
        return '⚠';
    }
  }

  @override
  bool shouldRepaint(_MapPainter old) => true;
}

// ─── RULES TAB ───────────────────────────────────────────────────────────────

class _RulesTab extends StatelessWidget {
  const _RulesTab();

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    if (state.activeGameFile == null) {
      return const Center(
        child: Text('No active game file.',
            style: TextStyle(color: Colors.white54)),
      );
    }
    final map = state.activeGameFile!.fieldMap;
    final isAdmin = state.isAdmin;

    return _RulesEditor(
      map: map,
      isAdmin: isAdmin,
      fileId: state.activeGameFile!.id,
    );
  }
}

class _RulesEditor extends StatefulWidget {
  const _RulesEditor(
      {required this.map, required this.isAdmin, required this.fileId});
  final FieldMapData map;
  final bool isAdmin;
  final String fileId;

  @override
  State<_RulesEditor> createState() => _RulesEditorState();
}

class _RulesEditorState extends State<_RulesEditor> {
  late TextEditingController _briefEn;
  late TextEditingController _briefJa;
  late TextEditingController _respawnEn;
  late TextEditingController _respawnJa;
  late TextEditingController _firEn;
  late TextEditingController _firJa;
  late TextEditingController _objEn;
  late TextEditingController _objJa;

  @override
  void initState() {
    super.initState();
    final m = widget.map;
    _briefEn = TextEditingController(text: m.briefingEn);
    _briefJa = TextEditingController(text: m.briefingJa);
    _respawnEn = TextEditingController(text: m.respawnRulesEn);
    _respawnJa = TextEditingController(text: m.respawnRulesJa);
    _firEn = TextEditingController(text: m.fireSelectorEn);
    _firJa = TextEditingController(text: m.fireSelectorJa);
    _objEn = TextEditingController(text: m.objectiveEn);
    _objJa = TextEditingController(text: m.objectiveJa);
  }

  @override
  void dispose() {
    for (final c in [
      _briefEn, _briefJa, _respawnEn, _respawnJa,
      _firEn, _firJa, _objEn, _objJa
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final updated = FieldMapData(
      imagePath: widget.map.imagePath,
      markers: widget.map.markers,
      strokes: widget.map.strokes,
      briefingEn: _briefEn.text.trim(),
      briefingJa: _briefJa.text.trim(),
      respawnRulesEn: _respawnEn.text.trim(),
      respawnRulesJa: _respawnJa.text.trim(),
      fireSelectorEn: _firEn.text.trim(),
      fireSelectorJa: _firJa.text.trim(),
      objectiveEn: _objEn.text.trim(),
      objectiveJa: _objJa.text.trim(),
    );
    await context
        .read<AppState>()
        .updateFieldMap(widget.fileId, updated);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Rules saved.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ext = Theme.of(context).extension<AppThemeExtension>()!;

    Widget field(String labelEn, String labelJa,
        TextEditingController ctrlEn, TextEditingController ctrlJa,
        {int maxLines = 2}) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(labelEn.toUpperCase(),
              style: TextStyle(
                  color: ext.accentColor,
                  fontSize: 10,
                  letterSpacing: 1.5)),
          const SizedBox(height: 6),
          TextField(
            controller: ctrlEn,
            maxLines: maxLines,
            readOnly: !widget.isAdmin,
            decoration: InputDecoration(
              hintText: 'English',
              suffixIcon: !widget.isAdmin
                  ? null
                  : const Icon(Icons.edit, size: 14),
            ),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: ctrlJa,
            maxLines: maxLines,
            readOnly: !widget.isAdmin,
            decoration: InputDecoration(
              hintText: '日本語',
              suffixIcon: !widget.isAdmin
                  ? null
                  : const Icon(Icons.edit, size: 14),
            ),
          ),
          const SizedBox(height: 16),
        ],
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          field('Mission Briefing', '任務ブリーフィング', _briefEn, _briefJa,
              maxLines: 4),
          field('Objective', '目標', _objEn, _objJa, maxLines: 3),
          field('Respawn Rules', 'リスポーンルール', _respawnEn, _respawnJa),
          field('Fire Selector', 'ファイアセレクター', _firEn, _firJa,
              maxLines: 1),
          if (widget.isAdmin) ...[
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _save,
                icon: const Icon(Icons.save),
                label: const Text('SAVE RULES'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
