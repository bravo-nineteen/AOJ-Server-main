import 'package:flutter/material.dart';

// ─── ENUMS ────────────────────────────────────────────────────────────────────

enum TeamType { taskForceOnyx, blackTalon }

extension TeamTypeExt on TeamType {
  String get displayName =>
      this == TeamType.taskForceOnyx ? 'Task Force Onyx' : 'Black Talon';
  String get displayNameJa =>
      this == TeamType.taskForceOnyx ? 'タスクフォース・オニキス' : 'ブラック・タロン';
}

enum ReportType { praise, warning, incident }

enum MapMarkerType { respawnA, respawnB, objective, extraction, danger }

enum MessageType { info, warning, urgent }

// ─── PLAYER ───────────────────────────────────────────────────────────────────

class PlayerReport {
  final String id;
  final DateTime timestamp;
  final ReportType type;
  final String note;
  final String issuedBy;

  PlayerReport({
    required this.id,
    required this.timestamp,
    required this.type,
    required this.note,
    required this.issuedBy,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'timestamp': timestamp.toIso8601String(),
        'type': type.name,
        'note': note,
        'issuedBy': issuedBy,
      };

  factory PlayerReport.fromJson(Map<String, dynamic> j) => PlayerReport(
        id: j['id'] as String,
        timestamp: DateTime.parse(j['timestamp'] as String),
        type: ReportType.values.byName(j['type'] as String),
        note: j['note'] as String,
        issuedBy: j['issuedBy'] as String,
      );
}

class Player {
  final String id;
  String name;
  String callsign;
  TeamType team;
  String role;
  List<PlayerReport> reports;

  Player({
    required this.id,
    required this.name,
    required this.callsign,
    required this.team,
    this.role = '',
    List<PlayerReport>? reports,
  }) : reports = reports ?? [];

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'callsign': callsign,
        'team': team.name,
        'role': role,
        'reports': reports.map((r) => r.toJson()).toList(),
      };

  factory Player.fromJson(Map<String, dynamic> j) => Player(
        id: j['id'] as String,
        name: j['name'] as String,
        callsign: j['callsign'] as String,
        team: TeamType.values.byName(j['team'] as String),
        role: j['role'] as String? ?? '',
        reports: (j['reports'] as List<dynamic>)
            .map((r) => PlayerReport.fromJson(r as Map<String, dynamic>))
            .toList(),
      );
}

// ─── SCHEDULE ─────────────────────────────────────────────────────────────────

class ScheduleEntry {
  final String id;
  String titleEn;
  String titleJa;
  String timeLabel;
  String notes;

  ScheduleEntry({
    required this.id,
    required this.titleEn,
    required this.titleJa,
    required this.timeLabel,
    this.notes = '',
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'titleEn': titleEn,
        'titleJa': titleJa,
        'timeLabel': timeLabel,
        'notes': notes,
      };

  factory ScheduleEntry.fromJson(Map<String, dynamic> j) => ScheduleEntry(
        id: j['id'] as String,
        titleEn: j['titleEn'] as String,
        titleJa: j['titleJa'] as String,
        timeLabel: j['timeLabel'] as String,
        notes: j['notes'] as String? ?? '',
      );
}

// ─── DEVICES ──────────────────────────────────────────────────────────────────

class DeviceInfo {
  final String id;
  String name;
  String typeName;
  String descriptionEn;
  String descriptionJa;
  String howToUseEn;
  String howToUseJa;
  String functions;

  DeviceInfo({
    required this.id,
    required this.name,
    required this.typeName,
    required this.descriptionEn,
    required this.descriptionJa,
    this.howToUseEn = '',
    this.howToUseJa = '',
    this.functions = '',
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'typeName': typeName,
        'descriptionEn': descriptionEn,
        'descriptionJa': descriptionJa,
        'howToUseEn': howToUseEn,
        'howToUseJa': howToUseJa,
        'functions': functions,
      };

  factory DeviceInfo.fromJson(Map<String, dynamic> j) => DeviceInfo(
        id: j['id'] as String,
        name: j['name'] as String,
        typeName: j['typeName'] as String,
        descriptionEn: j['descriptionEn'] as String,
        descriptionJa: j['descriptionJa'] as String,
        howToUseEn: j['howToUseEn'] as String? ?? '',
        howToUseJa: j['howToUseJa'] as String? ?? '',
        functions: j['functions'] as String? ?? '',
      );
}

// ─── FIELD MAP ────────────────────────────────────────────────────────────────

class MapMarker {
  final String id;
  double x; // normalized 0..1
  double y;
  MapMarkerType type;
  String labelEn;
  String labelJa;
  TeamType? team;

  MapMarker({
    required this.id,
    required this.x,
    required this.y,
    required this.type,
    this.labelEn = '',
    this.labelJa = '',
    this.team,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'x': x,
        'y': y,
        'type': type.name,
        'labelEn': labelEn,
        'labelJa': labelJa,
        'team': team?.name,
      };

  factory MapMarker.fromJson(Map<String, dynamic> j) => MapMarker(
        id: j['id'] as String,
        x: (j['x'] as num).toDouble(),
        y: (j['y'] as num).toDouble(),
        type: MapMarkerType.values.byName(j['type'] as String),
        labelEn: j['labelEn'] as String? ?? '',
        labelJa: j['labelJa'] as String? ?? '',
        team: j['team'] != null
            ? TeamType.values.byName(j['team'] as String)
            : null,
      );
}

class DrawStroke {
  /// Stored as normalized points (0..1 relative to canvas size)
  List<Offset> points;
  Color color;
  double width;

  DrawStroke({
    required this.points,
    required this.color,
    this.width = 3.0,
  });

  Map<String, dynamic> toJson() => {
        'points': points.map((p) => {'x': p.dx, 'y': p.dy}).toList(),
        'color': color.value,
        'width': width,
      };

  factory DrawStroke.fromJson(Map<String, dynamic> j) => DrawStroke(
        points: (j['points'] as List<dynamic>)
            .map((p) => Offset(
                  ((p as Map<String, dynamic>)['x'] as num).toDouble(),
                  (p['y'] as num).toDouble(),
                ))
            .toList(),
        color: Color(j['color'] as int),
        width: (j['width'] as num).toDouble(),
      );
}

class SquadPlan {
  final String id;
  String name;
  TeamType team;
  String objectiveEn;
  String objectiveJa;
  double? objectiveX;
  double? objectiveY;

  SquadPlan({
    required this.id,
    required this.name,
    required this.team,
    this.objectiveEn = '',
    this.objectiveJa = '',
    this.objectiveX,
    this.objectiveY,
  });

  bool get hasObjective => objectiveX != null && objectiveY != null;

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'team': team.name,
        'objectiveEn': objectiveEn,
        'objectiveJa': objectiveJa,
        'objectiveX': objectiveX,
        'objectiveY': objectiveY,
      };

  factory SquadPlan.fromJson(Map<String, dynamic> j) => SquadPlan(
        id: j['id'] as String,
        name: j['name'] as String,
        team: TeamType.values.byName(j['team'] as String),
        objectiveEn: j['objectiveEn'] as String? ?? '',
        objectiveJa: j['objectiveJa'] as String? ?? '',
        objectiveX:
            j['objectiveX'] != null ? (j['objectiveX'] as num).toDouble() : null,
        objectiveY:
            j['objectiveY'] != null ? (j['objectiveY'] as num).toDouble() : null,
      );
}

class FieldMapData {
  String? imagePath;
  List<MapMarker> markers;
  List<DrawStroke> strokes;
  List<SquadPlan> squads;
  String briefingEn;
  String briefingJa;
  String respawnRulesEn;
  String respawnRulesJa;
  String fireSelectorEn;
  String fireSelectorJa;
  String objectiveEn;
  String objectiveJa;

  FieldMapData({
    this.imagePath,
    List<MapMarker>? markers,
    List<DrawStroke>? strokes,
    List<SquadPlan>? squads,
    this.briefingEn = '',
    this.briefingJa = '',
    this.respawnRulesEn = '',
    this.respawnRulesJa = '',
    this.fireSelectorEn = 'Semi-auto only',
    this.fireSelectorJa = 'セミオートのみ',
    this.objectiveEn = '',
    this.objectiveJa = '',
  })  : markers = markers ?? [],
      strokes = strokes ?? [],
      squads = squads ?? [];

  Map<String, dynamic> toJson() => {
        'imagePath': imagePath,
        'markers': markers.map((m) => m.toJson()).toList(),
        'strokes': strokes.map((s) => s.toJson()).toList(),
        'squads': squads.map((s) => s.toJson()).toList(),
        'briefingEn': briefingEn,
        'briefingJa': briefingJa,
        'respawnRulesEn': respawnRulesEn,
        'respawnRulesJa': respawnRulesJa,
        'fireSelectorEn': fireSelectorEn,
        'fireSelectorJa': fireSelectorJa,
        'objectiveEn': objectiveEn,
        'objectiveJa': objectiveJa,
      };

  factory FieldMapData.fromJson(Map<String, dynamic> j) => FieldMapData(
        imagePath: j['imagePath'] as String?,
        markers: (j['markers'] as List<dynamic>)
            .map((m) => MapMarker.fromJson(m as Map<String, dynamic>))
            .toList(),
        strokes: (j['strokes'] as List<dynamic>)
            .map((s) => DrawStroke.fromJson(s as Map<String, dynamic>))
            .toList(),
        squads: ((j['squads'] as List<dynamic>?) ?? const [])
          .map((s) => SquadPlan.fromJson(s as Map<String, dynamic>))
          .toList(),
        briefingEn: j['briefingEn'] as String? ?? '',
        briefingJa: j['briefingJa'] as String? ?? '',
        respawnRulesEn: j['respawnRulesEn'] as String? ?? '',
        respawnRulesJa: j['respawnRulesJa'] as String? ?? '',
        fireSelectorEn: j['fireSelectorEn'] as String? ?? 'Semi-auto only',
        fireSelectorJa: j['fireSelectorJa'] as String? ?? 'セミオートのみ',
        objectiveEn: j['objectiveEn'] as String? ?? '',
        objectiveJa: j['objectiveJa'] as String? ?? '',
      );
}

// ─── GAME SESSION ─────────────────────────────────────────────────────────────

class GameSession {
  final String id;
  String gameModeName;
  Map<TeamType, int> respawnCounts;
  Map<TeamType, int> respawnLimits;
  bool isActive;
  DateTime? startTime;
  DateTime? endTime;
  String notes;
  Map<TeamType, int> objectivesCaptured;

  GameSession({
    required this.id,
    required this.gameModeName,
    Map<TeamType, int>? respawnCounts,
    Map<TeamType, int>? respawnLimits,
    this.isActive = false,
    this.startTime,
    this.endTime,
    this.notes = '',
    Map<TeamType, int>? objectivesCaptured,
  })  : respawnCounts = respawnCounts ??
            {TeamType.taskForceOnyx: 0, TeamType.blackTalon: 0},
        respawnLimits = respawnLimits ??
            {TeamType.taskForceOnyx: 20, TeamType.blackTalon: 20},
        objectivesCaptured = objectivesCaptured ??
            {TeamType.taskForceOnyx: 0, TeamType.blackTalon: 0};

  Map<String, dynamic> toJson() => {
        'id': id,
        'gameModeName': gameModeName,
        'respawnCounts': respawnCounts.map((k, v) => MapEntry(k.name, v)),
        'respawnLimits': respawnLimits.map((k, v) => MapEntry(k.name, v)),
        'isActive': isActive,
        'startTime': startTime?.toIso8601String(),
        'endTime': endTime?.toIso8601String(),
        'notes': notes,
        'objectivesCaptured':
            objectivesCaptured.map((k, v) => MapEntry(k.name, v)),
      };

  factory GameSession.fromJson(Map<String, dynamic> j) => GameSession(
        id: j['id'] as String,
        gameModeName: j['gameModeName'] as String,
        respawnCounts: (j['respawnCounts'] as Map<String, dynamic>)
            .map((k, v) => MapEntry(TeamType.values.byName(k), v as int)),
        respawnLimits: (j['respawnLimits'] as Map<String, dynamic>)
            .map((k, v) => MapEntry(TeamType.values.byName(k), v as int)),
        isActive: j['isActive'] as bool? ?? false,
        startTime: j['startTime'] != null
            ? DateTime.parse(j['startTime'] as String)
            : null,
        endTime: j['endTime'] != null
            ? DateTime.parse(j['endTime'] as String)
            : null,
        notes: j['notes'] as String? ?? '',
        objectivesCaptured: (j['objectivesCaptured'] as Map<String, dynamic>)
            .map((k, v) => MapEntry(TeamType.values.byName(k), v as int)),
      );
}

// ─── COMMS ────────────────────────────────────────────────────────────────────

class CommsMessage {
  final String id;
  final DateTime timestamp;
  final String sender;
  final String text;
  final MessageType type;

  CommsMessage({
    required this.id,
    required this.timestamp,
    required this.sender,
    required this.text,
    this.type = MessageType.info,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'timestamp': timestamp.toIso8601String(),
        'sender': sender,
        'text': text,
        'type': type.name,
      };

  factory CommsMessage.fromJson(Map<String, dynamic> j) => CommsMessage(
        id: j['id'] as String,
        timestamp: DateTime.parse(j['timestamp'] as String),
        sender: j['sender'] as String,
        text: j['text'] as String,
        type: MessageType.values.byName(j['type'] as String? ?? 'info'),
      );
}

// ─── GAME FILE ────────────────────────────────────────────────────────────────

class GameFile {
  final String id;
  String name;
  DateTime date;
  String locationEn;
  String locationJa;
  FieldMapData fieldMap;
  List<ScheduleEntry> schedule;
  List<GameSession> sessions;
  List<CommsMessage> commsLog;

  GameFile({
    required this.id,
    required this.name,
    required this.date,
    this.locationEn = '',
    this.locationJa = '',
    FieldMapData? fieldMap,
    List<ScheduleEntry>? schedule,
    List<GameSession>? sessions,
    List<CommsMessage>? commsLog,
  })  : fieldMap = fieldMap ?? FieldMapData(),
        schedule = schedule ?? [],
        sessions = sessions ?? [],
        commsLog = commsLog ?? [];

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'date': date.toIso8601String(),
        'locationEn': locationEn,
        'locationJa': locationJa,
        'fieldMap': fieldMap.toJson(),
        'schedule': schedule.map((s) => s.toJson()).toList(),
        'sessions': sessions.map((s) => s.toJson()).toList(),
        'commsLog': commsLog.map((m) => m.toJson()).toList(),
      };

  factory GameFile.fromJson(Map<String, dynamic> j) => GameFile(
        id: j['id'] as String,
        name: j['name'] as String,
        date: DateTime.parse(j['date'] as String),
        locationEn: j['locationEn'] as String? ?? '',
        locationJa: j['locationJa'] as String? ?? '',
        fieldMap:
            FieldMapData.fromJson(j['fieldMap'] as Map<String, dynamic>),
        schedule: (j['schedule'] as List<dynamic>)
            .map((s) => ScheduleEntry.fromJson(s as Map<String, dynamic>))
            .toList(),
        sessions: (j['sessions'] as List<dynamic>)
            .map((s) => GameSession.fromJson(s as Map<String, dynamic>))
            .toList(),
        commsLog: (j['commsLog'] as List<dynamic>)
            .map((m) => CommsMessage.fromJson(m as Map<String, dynamic>))
            .toList(),
      );
}
