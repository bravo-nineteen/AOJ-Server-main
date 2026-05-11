import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/models.dart';

/// HTTP REST client for communicating with AOJ Command OS server
/// Supports team roster, game sessions, schedule, and comms log sync
class ServerIntegrationService {
  late String baseUrl;
  late String teamName;
  String? sessionToken; // For future authentication

  ServerIntegrationService(String serverHost, {int port = 8000}) {
    baseUrl = 'http://$serverHost:$port/api';
  }

  // ── Connection ────────────────────────────────────────────────────────────

  /// Test connection to server
  Future<bool> testConnection() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/../health'))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Roster / Players ──────────────────────────────────────────────────────

  /// Get all players for a team
  Future<List<Player>> getPlayers(String teamId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/players?team_id=$teamId'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        return list
            .map((p) => _playerFromServer(p as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {}
    return [];
  }

  /// Add/update a player on the roster
  Future<bool> syncPlayer(Player player) async {
    try {
      final body = jsonEncode({
        'id': player.id,
        'username': player.name,
        'callsign': player.callsign,
        'team': player.team.name,
        'role': player.role,
      });

      final response = await http.post(
        Uri.parse('$baseUrl/players'),
        headers: {'Content-Type': 'application/json'},
        body: body,
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 201 || response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Game Sessions ─────────────────────────────────────────────────────────

  /// Get active game sessions
  Future<List<GameSession>> getGameSessions() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/game-sessions'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        return list
            .map((s) => _sessionFromServer(s as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {}
    return [];
  }

  /// Start a new game session
  Future<GameSession?> startGameSession({
    required String gameModeName,
    required Map<TeamType, int> respawnLimits,
  }) async {
    try {
      final body = jsonEncode({
        'game_mode': gameModeName,
        'respawn_limits': respawnLimits.map((k, v) => MapEntry(k.name, v)),
      });

      final response = await http.post(
        Uri.parse('$baseUrl/game-sessions'),
        headers: {'Content-Type': 'application/json'},
        body: body,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 201) {
        return _sessionFromServer(
            jsonDecode(response.body) as Map<String, dynamic>);
      }
    } catch (_) {}
    return null;
  }

  /// Record a respawn event
  Future<bool> recordRespawn({
    required String sessionId,
    required TeamType team,
  }) async {
    try {
      final body = jsonEncode({
        'session_id': sessionId,
        'team': team.name,
      });

      final response = await http.post(
        Uri.parse('$baseUrl/game-sessions/$sessionId/respawn'),
        headers: {'Content-Type': 'application/json'},
        body: body,
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// End a game session
  Future<bool> endGameSession(String sessionId) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/game-sessions/$sessionId/end'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Schedule ──────────────────────────────────────────────────────────────

  /// Get schedule for a mission
  Future<List<ScheduleEntry>> getSchedule(String missionId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/missions/$missionId/schedule'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        return list
            .map((s) => _scheduleFromServer(s as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {}
    return [];
  }

  // ── Game Events ───────────────────────────────────────────────────────────

  /// Record a game event (objective capture, etc)
  Future<bool> recordGameEvent({
    required String sessionId,
    required String eventType,
    required String description,
    String? teamId,
    String? playerId,
  }) async {
    try {
      final body = jsonEncode({
        'game_session_id': sessionId,
        'event_type': eventType,
        'description': description,
        'team_id': teamId,
        'player_id': playerId,
        'metadata': '{}',
      });

      final response = await http.post(
        Uri.parse('$baseUrl/game-events'),
        headers: {'Content-Type': 'application/json'},
        body: body,
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 201;
    } catch (_) {
      return false;
    }
  }

  /// Record score for a player
  Future<bool> recordScore({
    required String sessionId,
    required String teamId,
    required String playerId,
    required int points,
    required String reason,
  }) async {
    try {
      final body = jsonEncode({
        'game_session_id': sessionId,
        'team_id': teamId,
        'player_id': playerId,
        'points': points,
        'reason': reason,
      });

      final response = await http.post(
        Uri.parse('$baseUrl/scores'),
        headers: {'Content-Type': 'application/json'},
        body: body,
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 201;
    } catch (_) {
      return false;
    }
  }

  // ── Announcements ─────────────────────────────────────────────────────────

  /// Get current announcements
  Future<List<CommsMessage>> getAnnouncements({int limit = 50}) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/announcements/christy?limit=$limit'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        return list
            .map((a) => _announcementToComms(a as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {}
    return [];
  }

  /// Post a team comms message
  Future<bool> postCommsMessage({
    required String sessionId,
    required String sender,
    required String text,
    String messageType = 'info',
  }) async {
    try {
      final body = jsonEncode({
        'sender': sender,
        'text': text,
        'type': messageType,
      });

      // Note: Requires a comms endpoint on the server
      // This is a placeholder for demonstration
      return true;
    } catch (_) {
      return false;
    }
  }

  // ── System / Health ───────────────────────────────────────────────────────

  /// Get server health status
  Future<Map<String, dynamic>?> getSystemStatus() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/../health'))
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  /// Convert server player response to Team Terminals Player model
  Player _playerFromServer(Map<String, dynamic> data) {
    return Player(
      id: data['id'] as String? ?? '',
      name: data['username'] as String? ?? data['name'] as String? ?? '',
      callsign: data['callsign'] as String? ?? '',
      team: (data['team'] as String?).let((t) => TeamType.values.byName(t)) ??
          TeamType.taskForceOnyx,
      role: data['role'] as String? ?? '',
    );
  }

  /// Convert server session response to Team Terminals GameSession model
  GameSession _sessionFromServer(Map<String, dynamic> data) {
    final respawnCounts = <TeamType, int>{};
    final respawnLimits = <TeamType, int>{};
    final objectivesCaptured = <TeamType, int>{};

    if (data['respawn_counts'] is Map) {
      (data['respawn_counts'] as Map<String, dynamic>).forEach((k, v) {
        respawnCounts[TeamType.values.byName(k)] = v as int;
      });
    }

    if (data['respawn_limits'] is Map) {
      (data['respawn_limits'] as Map<String, dynamic>).forEach((k, v) {
        respawnLimits[TeamType.values.byName(k)] = v as int;
      });
    }

    return GameSession(
      id: data['id'] as String? ?? '',
      gameModeName: data['game_mode'] as String? ?? data['game_mode_name'] as String? ?? '',
      respawnCounts: respawnCounts,
      respawnLimits: respawnLimits,
      isActive: data['is_active'] as bool? ?? false,
      startTime: data['started_at'] != null
          ? DateTime.parse(data['started_at'] as String)
          : null,
      endTime: data['ended_at'] != null
          ? DateTime.parse(data['ended_at'] as String)
          : null,
      notes: data['notes'] as String? ?? '',
      objectivesCaptured: objectivesCaptured,
    );
  }

  ScheduleEntry _scheduleFromServer(Map<String, dynamic> data) {
    return ScheduleEntry(
      id: data['id'] as String? ?? '',
      titleEn: data['title'] as String? ?? '',
      titleJa: data['title_ja'] as String? ?? '',
      timeLabel: data['time_label'] as String? ?? '',
      notes: data['notes'] as String? ?? '',
    );
  }

  CommsMessage _announcementToComms(Map<String, dynamic> data) {
    return CommsMessage(
      id: data['id'] as String? ?? '',
      timestamp: data['created_at'] != null
          ? DateTime.parse(data['created_at'] as String)
          : DateTime.now(),
      sender: 'System',
      text: data['content'] as String? ?? data['message'] as String? ?? '',
      type: MessageType.info,
    );
  }
}

/// Null-coalescing extension helper
extension<T> on T? {
  R? let<R>(R Function(T) f) => this != null ? f(this as T) : null;
}
