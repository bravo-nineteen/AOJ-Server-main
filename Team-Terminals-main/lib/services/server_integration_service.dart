import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/models.dart';

/// HTTP REST client for AOJ Command OS backend.
///
/// This client is intentionally conservative: only endpoints that exist on the
/// current backend are used, and all calls fail-soft to keep the tablet app
/// usable offline.
class ServerIntegrationService {
  ServerIntegrationService(String serverHost, {int port = 8000})
      : baseUrl = 'http://$serverHost:$port/api';

  final String baseUrl;

  // ── Connection ────────────────────────────────────────────────────────────

  /// Test connection to server.
  Future<bool> testConnection() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Load member profiles and map them into tablet-side Player models.
  ///
  /// Returns null on connectivity/API failure so the caller can preserve local
  /// cache instead of accidentally clearing data.
  Future<List<Player>?> getPlayers() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/members'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        return list
            .map((p) => _playerFromServer(p as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {}
    return null;
  }

  /// Create or update member profile from a Player.
  ///
  /// On duplicate name (409), the existing member is looked up and patched.
  Future<bool> syncPlayer(Player player) async {
    try {
      final body = jsonEncode({
        'name': player.name,
        'callsign': player.callsign,
        'team': player.team.name,
        'notes': player.role,
      });

      var response = await http.post(
        Uri.parse('$baseUrl/members'),
        headers: {'Content-Type': 'application/json'},
        body: body,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 409) {
        final members = await _fetchMembersRaw();
        final existing = members.cast<Map<String, dynamic>?>().firstWhere(
            (m) => m?['name'] == player.name,
            orElse: () => null);
        if (existing == null) return false;

        final id = existing['id'];
        response = await http.patch(
          Uri.parse('$baseUrl/members/$id'),
          headers: {'Content-Type': 'application/json'},
          body: body,
        ).timeout(const Duration(seconds: 10));
      }

      return response.statusCode == 201 || response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Schedule ──────────────────────────────────────────────────────────────

  /// Get today's schedule items.
  Future<List<ScheduleEntry>> getTodaySchedule() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/schedule/items'),
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

  /// Record game event (objective capture, session state change, respawn, etc).
  Future<bool> recordGameEvent({
    required String sessionId,
    required String eventType,
    required String description,
    int? teamId,
    int? playerId,
  }) async {
    try {
      final parsedSessionId = int.tryParse(sessionId);
      if (parsedSessionId == null) {
        return false;
      }

      final body = jsonEncode({
        'game_session_id': parsedSessionId,
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

  /// Record score event.
  Future<bool> recordScore({
    required String sessionId,
    required int teamId,
    int? playerId,
    required int points,
    required String eventType,
    String reason = '',
  }) async {
    try {
      final parsedSessionId = int.tryParse(sessionId);
      if (parsedSessionId == null) {
        return false;
      }

      final body = jsonEncode({
        'game_session_id': parsedSessionId,
        'team_id': teamId,
        'player_id': playerId,
        'points': points,
        'event_type': eventType,
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

  /// Post an announcement into server announcement timeline.
  Future<bool> postCommsMessage({
    required String sender,
    required String text,
    String messageType = 'general',
  }) async {
    try {
      final body = jsonEncode({
        'type': messageType,
        'content': '[$sender] $text',
      });

      final response = await http.post(
        Uri.parse('$baseUrl/announcements/create-christy'),
        headers: {'Content-Type': 'application/json'},
        body: body,
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200 || response.statusCode == 201;
    } catch (_) {
      return false;
    }
  }

  // ── System / Health ───────────────────────────────────────────────────────

  /// Get server health status
  Future<Map<String, dynamic>?> getSystemStatus() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  /// Convert MemberProfile to tablet Player model.
  Player _playerFromServer(Map<String, dynamic> data) {
    final teamName = data['team'] as String?;
    final team = teamName == TeamType.blackTalon.name
        ? TeamType.blackTalon
        : TeamType.taskForceOnyx;

    return Player(
      id: (data['id'] ?? '').toString(),
      name: data['name'] as String? ?? '',
      callsign: data['callsign'] as String? ?? '',
      team: team,
      role: data['notes'] as String? ?? '',
    );
  }

  ScheduleEntry _scheduleFromServer(Map<String, dynamic> data) {
    final start = data['start_time'] as String?;
    String timeLabel = '';
    if (start != null) {
      final dt = DateTime.tryParse(start);
      if (dt != null) {
        timeLabel =
            '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
      }
    }

    return ScheduleEntry(
      id: (data['id'] ?? '').toString(),
      titleEn: data['title'] as String? ?? '',
      titleJa: data['title'] as String? ?? '',
      timeLabel: timeLabel,
      notes: data['details'] as String? ?? '',
    );
  }

  CommsMessage _announcementToComms(Map<String, dynamic> data) {
    return CommsMessage(
      id: (data['id'] ?? '').toString(),
      timestamp: data['created_at'] != null
          ? DateTime.parse(data['created_at'] as String)
          : DateTime.now(),
      sender: 'System',
      text: data['content'] as String? ?? '',
      type: MessageType.info,
    );
  }

  Future<List<dynamic>> _fetchMembersRaw() async {
    final response = await http.get(Uri.parse('$baseUrl/members'));
    if (response.statusCode != 200) {
      return [];
    }
    return jsonDecode(response.body) as List<dynamic>;
  }
}
