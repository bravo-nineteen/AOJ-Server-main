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

enum _MapEditMode { planning, marker, draw }

class _MapTabState extends State<_MapTab> {
  _MapEditMode _editMode = _MapEditMode.planning;
  Color _brushColor = Colors.red;
  double _brushWidth = 3.0;
  DrawStroke? _currentStroke;
  MapMarkerType _markerType = MapMarkerType.respawnA;
  TeamType _planningTeam = TeamType.taskForceOnyx;
  String? _selectedSquadId;
  bool _showLabels = true;
  String? _draggingMarkerId;
  String? _draggingSquadId;
  Offset? _draggingPosition;
  bool _hasDragMoved = false;
  bool _showGrid = true;
  bool _snapToGrid = false;
  int _gridDivisions = 12;
  bool _showGridCoords = true;

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
      squads: _map?.squads ?? [],
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

  List<SquadPlan> get _squads => _map?.squads ?? const [];

  List<SquadPlan> _teamSquads(TeamType team) =>
      _squads.where((s) => s.team == team).toList();

  SquadPlan? get _selectedSquad {
    if (_selectedSquadId == null) return null;
    return _squads.cast<SquadPlan?>().firstWhere(
        (s) => s?.id == _selectedSquadId,
        orElse: () => null);
  }

  void _syncSquadSelection() {
    if (_squads.isEmpty) {
      _selectedSquadId = null;
      return;
    }

    final stillExists = _selectedSquad != null;
    if (stillExists) return;

    final forTeam = _teamSquads(_planningTeam);
    final fallback = forTeam.isNotEmpty ? forTeam.first : _squads.first;
    _selectedSquadId = fallback.id;
    _planningTeam = fallback.team;
  }

  void _onPanStart(DragStartDetails d, Size canvasSize) {
    if (!_isAdmin) return;
    final norm = _normalize(d.localPosition, canvasSize);

    if (_editMode == _MapEditMode.marker) {
      final marker = _findMarkerNear(norm, canvasSize);
      if (marker != null) {
        setState(() {
          _draggingMarkerId = marker.id;
          _draggingSquadId = null;
          _draggingPosition = norm;
          _hasDragMoved = false;
        });
      }
      return;
    }

    if (_editMode == _MapEditMode.planning) {
      final squad = _findSquadNear(norm, canvasSize);
      if (squad != null) {
        setState(() {
          _draggingSquadId = squad.id;
          _draggingMarkerId = null;
          _draggingPosition = norm;
          _hasDragMoved = false;
          _selectedSquadId = squad.id;
          _planningTeam = squad.team;
        });
      }
      return;
    }

    if (_editMode != _MapEditMode.draw) return;

    setState(() {
      _currentStroke = DrawStroke(
          points: [norm], color: _brushColor, width: _brushWidth);
    });
  }

  void _onPanUpdate(DragUpdateDetails d, Size canvasSize) {
    if (!_isAdmin) return;

    if (_draggingMarkerId != null || _draggingSquadId != null) {
      var norm = _clampNormalized(_normalize(d.localPosition, canvasSize));
      if (_snapToGrid) {
        norm = _snapOffset(norm);
      }
      setState(() {
        _draggingPosition = norm;
        _hasDragMoved = true;
      });
      return;
    }

    if (_editMode != _MapEditMode.draw || _currentStroke == null) {
      return;
    }
    final norm = _normalize(d.localPosition, canvasSize);
    setState(() => _currentStroke!.points.add(norm));
  }

  Future<void> _onPanEnd(DragEndDetails _, Size canvasSize) async {
    if (!_isAdmin) return;

    if (_draggingMarkerId != null) {
      final markerId = _draggingMarkerId!;
      final pos = _draggingPosition;
      final moved = _hasDragMoved;
      setState(() {
        _draggingMarkerId = null;
        _draggingPosition = null;
        _hasDragMoved = false;
      });
      if (moved && pos != null) {
        final markers = List<MapMarker>.from(_map?.markers ?? []);
        final i = markers.indexWhere((m) => m.id == markerId);
        if (i >= 0) {
          markers[i].x = pos.dx;
          markers[i].y = pos.dy;
          await _saveMap(markers: markers);
        }
      }
      return;
    }

    if (_draggingSquadId != null) {
      final squadId = _draggingSquadId!;
      final pos = _draggingPosition;
      final moved = _hasDragMoved;
      setState(() {
        _draggingSquadId = null;
        _draggingPosition = null;
        _hasDragMoved = false;
      });
      if (moved && pos != null) {
        final squads = _squads.map(_cloneSquad).toList();
        final i = squads.indexWhere((s) => s.id == squadId);
        if (i >= 0) {
          squads[i].objectiveX = pos.dx;
          squads[i].objectiveY = pos.dy;
          await _saveMap(squads: squads);
        }
      }
      return;
    }

    if (_editMode != _MapEditMode.draw || _currentStroke == null) {
      return;
    }
    if (_fileId == null) return;
    final strokes = List<DrawStroke>.from(_map?.strokes ?? [])
      ..add(_currentStroke!);
    await _saveMap(strokes: strokes);
    setState(() => _currentStroke = null);
  }

  Future<void> _onTapOnMap(TapUpDetails d, Size canvasSize) async {
    if (!_isAdmin || _fileId == null) return;
    if (_hasDragMoved) return;
    var norm = _clampNormalized(_normalize(d.localPosition, canvasSize));
    if (_snapToGrid) {
      norm = _snapOffset(norm);
    }

    if (_editMode == _MapEditMode.marker) {
      _showMarkerDialog(norm);
      return;
    }

    if (_editMode == _MapEditMode.planning) {
      await _placeSquadObjective(norm);
    }
  }

  Future<void> _placeSquadObjective(Offset norm) async {
    final selected = _selectedSquad;
    if (selected == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Add/select a squad before placing objective.')),
      );
      return;
    }

    final squads = _squads.map(_cloneSquad).toList();
    final idx = squads.indexWhere((s) => s.id == selected.id);
    if (idx < 0) return;

    squads[idx].objectiveX = norm.dx;
    squads[idx].objectiveY = norm.dy;
    await _saveMap(squads: squads);

    if (!mounted) return;
    _editSquadDialog(squads[idx]);
  }

  SquadPlan _cloneSquad(SquadPlan squad) => SquadPlan(
        id: squad.id,
        name: squad.name,
        team: squad.team,
        objectiveEn: squad.objectiveEn,
        objectiveJa: squad.objectiveJa,
        objectiveX: squad.objectiveX,
        objectiveY: squad.objectiveY,
      );

  Future<void> _addSquadDialog() async {
    final nameCtrl = TextEditingController();
    TeamType team = _planningTeam;

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => AlertDialog(
          title: const Text('ADD SQUAD'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(labelText: 'Squad name'),
              ),
              const SizedBox(height: 10),
              DropdownButtonFormField<TeamType>(
                value: team,
                decoration: const InputDecoration(labelText: 'Team'),
                items: TeamType.values
                    .map((t) => DropdownMenuItem(
                        value: t, child: Text(t.displayName)))
                    .toList(),
                onChanged: (v) => setS(() => team = v ?? team),
              ),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('CANCEL')),
            ElevatedButton(
              onPressed: () async {
                final name = nameCtrl.text.trim();
                final squad = SquadPlan(
                  id: DateTime.now().millisecondsSinceEpoch.toString(),
                  name: name.isEmpty ? 'Squad ${_squads.length + 1}' : name,
                  team: team,
                );
                final squads = [..._squads.map(_cloneSquad), squad];
                await _saveMap(squads: squads);
                if (!mounted) return;
                setState(() {
                  _selectedSquadId = squad.id;
                  _planningTeam = team;
                });
                Navigator.pop(ctx);
              },
              child: const Text('ADD'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _removeSelectedSquad() async {
    final selected = _selectedSquad;
    if (selected == null) return;
    final squads = _squads.map(_cloneSquad).toList()
      ..removeWhere((s) => s.id == selected.id);
    await _saveMap(squads: squads);
    if (!mounted) return;
    setState(() {
      _selectedSquadId = null;
      _syncSquadSelection();
    });
  }

  Future<void> _editSquadDialog(SquadPlan squad) async {
    final nameCtrl = TextEditingController(text: squad.name);
    final enCtrl = TextEditingController(text: squad.objectiveEn);
    final jaCtrl = TextEditingController(text: squad.objectiveJa);
    TeamType team = squad.team;

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => AlertDialog(
          title: const Text('SQUAD OBJECTIVE'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(labelText: 'Squad name'),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<TeamType>(
                  value: team,
                  decoration: const InputDecoration(labelText: 'Team'),
                  items: TeamType.values
                      .map((t) => DropdownMenuItem(
                          value: t, child: Text(t.displayName)))
                      .toList(),
                  onChanged: (v) => setS(() => team = v ?? team),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: enCtrl,
                  maxLines: 2,
                  decoration:
                      const InputDecoration(labelText: 'Objective (English)'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: jaCtrl,
                  maxLines: 2,
                  decoration:
                      const InputDecoration(labelText: '目標 (Japanese)'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () async {
                final squads = _squads.map(_cloneSquad).toList();
                final idx = squads.indexWhere((s) => s.id == squad.id);
                if (idx < 0) return;
                squads[idx].objectiveX = null;
                squads[idx].objectiveY = null;
                await _saveMap(squads: squads);
                if (!mounted) return;
                Navigator.pop(ctx);
              },
              child: const Text('CLEAR PIN'),
            ),
            TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('CANCEL')),
            ElevatedButton(
              onPressed: () async {
                final squads = _squads.map(_cloneSquad).toList();
                final idx = squads.indexWhere((s) => s.id == squad.id);
                if (idx < 0) return;
                final updated = squads[idx];
                updated.name = nameCtrl.text.trim().isEmpty
                    ? updated.name
                    : nameCtrl.text.trim();
                updated.team = team;
                updated.objectiveEn = enCtrl.text.trim();
                updated.objectiveJa = jaCtrl.text.trim();
                await _saveMap(squads: squads);
                if (!mounted) return;
                setState(() {
                  _planningTeam = updated.team;
                  _selectedSquadId = updated.id;
                });
                Navigator.pop(ctx);
              },
              child: const Text('SAVE'),
            ),
          ],
        ),
      ),
    );
  }

  void _showMarkerDialog(Offset pos) {
    final labelEnCtrl = TextEditingController();
    final labelJaCtrl = TextEditingController();
    TeamType? team;
    MapMarkerType type = _markerType;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setS) {
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
    List<SquadPlan>? squads,
  }) async {
    if (_fileId == null) return;
    final current = _map ?? FieldMapData();
    final updated = FieldMapData(
      imagePath: current.imagePath,
      markers: markers ?? current.markers,
      strokes: strokes ?? current.strokes,
      squads: squads ?? current.squads,
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

  Offset _clampNormalized(Offset p) {
    final dx = p.dx.clamp(0.0, 1.0) as double;
    final dy = p.dy.clamp(0.0, 1.0) as double;
    return Offset(dx, dy);
  }

  Offset _snapOffset(Offset p) {
    final step = 1.0 / _gridDivisions;
    final sx = (p.dx / step).round() * step;
    final sy = (p.dy / step).round() * step;
    return _clampNormalized(Offset(sx, sy));
  }

  MapMarker? _findMarkerNear(Offset norm, Size canvasSize) {
    final markers = _map?.markers ?? const <MapMarker>[];
    const hitRadius = 0.045;
    final thresholdPx = hitRadius * canvasSize.shortestSide;
    for (int i = markers.length - 1; i >= 0; i--) {
      final m = markers[i];
      final p = Offset(m.x * canvasSize.width, m.y * canvasSize.height);
      final t = Offset(norm.dx * canvasSize.width, norm.dy * canvasSize.height);
      if ((p - t).distance <= thresholdPx) {
        return m;
      }
    }
    return null;
  }

  SquadPlan? _findSquadNear(Offset norm, Size canvasSize) {
    final squads = _squads.where((s) => s.hasObjective).toList();
    const hitRadius = 0.05;
    final thresholdPx = hitRadius * canvasSize.shortestSide;
    for (int i = squads.length - 1; i >= 0; i--) {
      final s = squads[i];
      final p = Offset(
        s.objectiveX! * canvasSize.width,
        s.objectiveY! * canvasSize.height,
      );
      final t = Offset(norm.dx * canvasSize.width, norm.dy * canvasSize.height);
      if ((p - t).distance <= thresholdPx) {
        return s;
      }
    }
    return null;
  }

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

    _syncSquadSelection();

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
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
              children: [
                ChoiceChip(
                  selected: _editMode == _MapEditMode.planning,
                  label: const Text('Planning'),
                  onSelected: (_) => setState(() => _editMode = _MapEditMode.planning),
                ),
                const SizedBox(width: 6),
                ChoiceChip(
                  selected: _editMode == _MapEditMode.marker,
                  label: const Text('Markers'),
                  onSelected: (_) => setState(() => _editMode = _MapEditMode.marker),
                ),
                const SizedBox(width: 6),
                ChoiceChip(
                  selected: _editMode == _MapEditMode.draw,
                  label: const Text('Draw'),
                  onSelected: (_) => setState(() => _editMode = _MapEditMode.draw),
                ),
                const SizedBox(width: 8),
                if (_editMode == _MapEditMode.draw) ...[
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
                  SizedBox(
                    width: 120,
                    child: Slider(
                      value: _brushWidth,
                      min: 1,
                      max: 12,
                      divisions: 11,
                      onChanged: (v) => setState(() => _brushWidth = v),
                      activeColor: ext.iconGlowColor,
                    ),
                  ),
                  _ToolBtn(
                    icon: Icons.delete_sweep,
                    label: 'Clear Drawing',
                    active: false,
                    color: Colors.orange,
                    onTap: _clearDrawing,
                  ),
                ] else if (_editMode == _MapEditMode.marker) ...[
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
                ] else ...[
                  DropdownButton<TeamType>(
                    value: _planningTeam,
                    dropdownColor: Theme.of(context).scaffoldBackgroundColor,
                    style: const TextStyle(color: Colors.white, fontSize: 12),
                    underline: Container(height: 1, color: ext.iconGlowColor),
                    items: TeamType.values
                        .map((t) => DropdownMenuItem(
                            value: t, child: Text(t.displayName)))
                        .toList(),
                    onChanged: (v) {
                      if (v == null) return;
                      setState(() {
                        _planningTeam = v;
                        final squads = _teamSquads(v);
                        if (squads.isNotEmpty) {
                          _selectedSquadId = squads.first.id;
                        }
                      });
                    },
                  ),
                  const SizedBox(width: 8),
                  _ToolBtn(
                    icon: Icons.group_add,
                    label: 'Add Squad',
                    active: false,
                    color: ext.iconGlowColor,
                    onTap: _addSquadDialog,
                  ),
                  const SizedBox(width: 6),
                  _ToolBtn(
                    icon: Icons.flag_outlined,
                    label: 'Edit Objective',
                    active: false,
                    color: ext.iconGlowColor,
                    onTap: () {
                      final selected = _selectedSquad;
                      if (selected == null) return;
                      _editSquadDialog(selected);
                    },
                  ),
                  const SizedBox(width: 6),
                  _ToolBtn(
                    icon: Icons.person_remove_outlined,
                    label: 'Remove Squad',
                    active: false,
                    color: Colors.orange,
                    onTap: _removeSelectedSquad,
                  ),
                ],
                const SizedBox(width: 8),
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
                const SizedBox(width: 8),
                Switch(
                  value: _showGrid,
                  onChanged: (v) => setState(() => _showGrid = v),
                  activeColor: ext.iconGlowColor,
                ),
                const Text('Grid',
                    style:
                        TextStyle(color: Colors.white54, fontSize: 11)),
                const SizedBox(width: 8),
                Switch(
                  value: _showGridCoords,
                  onChanged: (v) => setState(() => _showGridCoords = v),
                  activeColor: ext.iconGlowColor,
                ),
                const Text('Coords',
                    style:
                        TextStyle(color: Colors.white54, fontSize: 11)),
                const SizedBox(width: 8),
                Switch(
                  value: _snapToGrid,
                  onChanged: (v) => setState(() => _snapToGrid = v),
                  activeColor: ext.iconGlowColor,
                ),
                const Text('Snap',
                    style:
                        TextStyle(color: Colors.white54, fontSize: 11)),
                const SizedBox(width: 8),
                const Text('Cells',
                    style:
                        TextStyle(color: Colors.white54, fontSize: 11)),
                SizedBox(
                  width: 100,
                  child: Slider(
                    value: _gridDivisions.toDouble(),
                    min: 6,
                    max: 24,
                    divisions: 18,
                    onChanged: (v) {
                      setState(() {
                        _gridDivisions = v.round();
                      });
                    },
                    activeColor: ext.iconGlowColor,
                  ),
                ),
              ],
              ),
            ),
          ),

        if (isAdmin && _editMode == _MapEditMode.planning)
          Container(
            color: ext.taskbarColor.withAlpha(140),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  const Text(
                    'Planning: Select squad, tap to place objective, drag pin to adjust.',
                    style: TextStyle(color: Colors.white70, fontSize: 11),
                  ),
                  const SizedBox(width: 10),
                  ..._teamSquads(_planningTeam).map((s) {
                    final selected = s.id == _selectedSquadId;
                    final hasObjective = s.hasObjective;
                    final chipColor = s.team == TeamType.taskForceOnyx
                        ? const Color(0xFF4CAF50)
                        : const Color(0xFFC41E3A);
                    return Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: GestureDetector(
                        onLongPress: () => _editSquadDialog(s),
                        child: FilterChip(
                          selected: selected,
                          label: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(s.name),
                              const SizedBox(width: 4),
                              Icon(
                                hasObjective
                                    ? Icons.flag
                                    : Icons.flag_outlined,
                                size: 12,
                                color:
                                    hasObjective ? chipColor : Colors.white54,
                              ),
                            ],
                          ),
                          selectedColor: chipColor.withAlpha(60),
                          onSelected: (_) =>
                              setState(() => _selectedSquadId = s.id),
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
          ),

        // ── Map canvas ───────────────────────────────────────────────────
        Expanded(
          child: map == null ||
                  (map.imagePath == null &&
                      map.markers.isEmpty &&
                  map.strokes.isEmpty &&
                  map.squads.isEmpty)
              ? _NoMapImage(isAdmin: isAdmin, onUpload: _pickImage)
              : LayoutBuilder(
                  builder: (context, constraints) {
                    final size = Size(
                        constraints.maxWidth, constraints.maxHeight);
                    return GestureDetector(
                      onPanStart: (d) => _onPanStart(d, size),
                      onPanUpdate: (d) => _onPanUpdate(d, size),
                      onPanEnd: (d) => _onPanEnd(d, size),
                        onTapUp: (d) => _onTapOnMap(d, size),
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
                                squads: map.squads,
                                selectedSquadId: _selectedSquadId,
                                draggingMarkerId: _draggingMarkerId,
                                draggingSquadId: _draggingSquadId,
                                draggingPosition: _draggingPosition,
                                showGrid: _showGrid,
                                gridDivisions: _gridDivisions,
                                showGridCoords: _showGridCoords,
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
            const SizedBox(height: 6),
            const Text(
              'You can still use planning mode on a blank canvas.',
              style: TextStyle(color: Colors.white38, fontSize: 12)),
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
  final List<SquadPlan> squads;
  final String? selectedSquadId;
  final String? draggingMarkerId;
  final String? draggingSquadId;
  final Offset? draggingPosition;
  final bool showGrid;
  final int gridDivisions;
  final bool showGridCoords;
  final bool showLabels;

  _MapPainter({
    required this.strokes,
    required this.currentStroke,
    required this.markers,
    required this.squads,
    required this.selectedSquadId,
    required this.draggingMarkerId,
    required this.draggingSquadId,
    required this.draggingPosition,
    required this.showGrid,
    required this.gridDivisions,
    required this.showGridCoords,
    required this.showLabels,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (showGrid && gridDivisions > 0) {
      final gridPaint = Paint()
        ..color = const Color(0x88FFFFFF)
        ..strokeWidth = 0.6;
      final dx = size.width / gridDivisions;
      final dy = size.height / gridDivisions;

      for (int i = 0; i <= gridDivisions; i++) {
        final x = i * dx;
        canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
      }
      for (int i = 0; i <= gridDivisions; i++) {
        final y = i * dy;
        canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
      }

      if (showGridCoords) {
        final labelStyle = const TextStyle(
          color: Colors.white70,
          fontSize: 10,
          fontWeight: FontWeight.w600,
          shadows: [Shadow(color: Colors.black87, blurRadius: 3)],
        );

        // Column labels (A, B, C...) at the top center of each cell
        for (int col = 0; col < gridDivisions; col++) {
          final label = _columnLabel(col);
          final x = (col + 0.5) * dx;
          final tp = TextPainter(
            text: TextSpan(text: label, style: labelStyle),
            textDirection: TextDirection.ltr,
          )..layout();
          tp.paint(canvas, Offset(x - tp.width / 2, 4));
        }

        // Row labels (1,2,3...) at the left center of each cell
        for (int row = 0; row < gridDivisions; row++) {
          final label = (row + 1).toString();
          final y = (row + 0.5) * dy;
          final tp = TextPainter(
            text: TextSpan(text: label, style: labelStyle),
            textDirection: TextDirection.ltr,
          )..layout();
          tp.paint(canvas, Offset(4, y - tp.height / 2));
        }
      }
    }

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
      final pos = marker.id == draggingMarkerId && draggingPosition != null
          ? Offset(draggingPosition!.dx * size.width,
              draggingPosition!.dy * size.height)
          : Offset(marker.x * size.width, marker.y * size.height);
      _drawMarker(canvas, pos, marker);
    }

    // Draw squad objective pins
    for (final squad in squads) {
      if (!squad.hasObjective) continue;
      final pos = squad.id == draggingSquadId && draggingPosition != null
          ? Offset(draggingPosition!.dx * size.width,
              draggingPosition!.dy * size.height)
          : Offset(
              squad.objectiveX! * size.width,
              squad.objectiveY! * size.height,
            );
      _drawSquadObjective(canvas, pos, squad,
          selected: squad.id == selectedSquadId);
    }
  }

  void _drawMarker(Canvas canvas, Offset pos, MapMarker marker) {
    Color baseColor;

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

  String _columnLabel(int index) {
    // Excel-style labels: A..Z, AA..AZ, etc.
    var n = index;
    var s = '';
    while (n >= 0) {
      s = String.fromCharCode(65 + (n % 26)) + s;
      n = (n ~/ 26) - 1;
    }
    return s;
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

  void _drawSquadObjective(
    Canvas canvas,
    Offset pos,
    SquadPlan squad, {
    required bool selected,
  }) {
    final teamColor = squad.team == TeamType.taskForceOnyx
        ? const Color(0xFF4CAF50)
        : const Color(0xFFC41E3A);

    final haloRadius = selected ? 22.0 : 18.0;
    canvas.drawCircle(
      pos,
      haloRadius,
      Paint()..color = teamColor.withAlpha(selected ? 100 : 60),
    );

    final diamond = Path()
      ..moveTo(pos.dx, pos.dy - 13)
      ..lineTo(pos.dx + 13, pos.dy)
      ..lineTo(pos.dx, pos.dy + 13)
      ..lineTo(pos.dx - 13, pos.dy)
      ..close();
    canvas.drawPath(
      diamond,
      Paint()
        ..color = teamColor.withAlpha(220)
        ..style = PaintingStyle.fill,
    );
    canvas.drawPath(
      diamond,
      Paint()
        ..color = Colors.white
        ..strokeWidth = selected ? 2.2 : 1.6
        ..style = PaintingStyle.stroke,
    );

    final tp = TextPainter(
      text: TextSpan(
        text: squad.name,
        style: TextStyle(
          color: Colors.white,
          fontSize: selected ? 10 : 9,
          fontWeight: FontWeight.bold,
          shadows: const [Shadow(color: Colors.black, blurRadius: 4)],
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout(maxWidth: 110);
    tp.paint(canvas, Offset(pos.dx - tp.width / 2, pos.dy - 32));

    if (showLabels && squad.objectiveEn.isNotEmpty) {
      final sub = TextPainter(
        text: TextSpan(
          text: squad.objectiveEn,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 8,
            shadows: [Shadow(color: Colors.black, blurRadius: 3)],
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: 140);
      sub.paint(canvas, Offset(pos.dx - sub.width / 2, pos.dy + 18));
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
      squads: widget.map.squads,
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
