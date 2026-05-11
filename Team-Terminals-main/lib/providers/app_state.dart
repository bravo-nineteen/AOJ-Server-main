import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/models.dart';
import '../services/server_integration_service.dart';

class AppState extends ChangeNotifier {
  // ── Identity ──────────────────────────────────────────────────────────────
  TeamType _team = TeamType.taskForceOnyx;
  bool _isFirstRun = true;
  bool _isAdmin = false;
  String _adminPin = '0000'; // stored locally; change via admin panel

  // ── Data ──────────────────────────────────────────────────────────────────
  List<Player> _players = [];
  List<DeviceInfo> _devices = [];
  List<GameFile> _gameFiles = [];
  String? _activeGameFileId;
  String _serverHost = '127.0.0.1';
  bool _serverConnected = false;
  bool _serverSyncEnabled = true;
  ServerIntegrationService? _server;

  // ── Getters ───────────────────────────────────────────────────────────────
  TeamType get team => _team;
  bool get isFirstRun => _isFirstRun;
  bool get isAdmin => _isAdmin;
  bool get serverConnected => _serverConnected;
  bool get serverSyncEnabled => _serverSyncEnabled;
  String get serverHost => _serverHost;
  List<Player> get players => List.unmodifiable(_players);
  List<DeviceInfo> get devices => List.unmodifiable(_devices);
  List<GameFile> get gameFiles => List.unmodifiable(_gameFiles);

  GameFile? get activeGameFile =>
      _activeGameFileId == null
          ? null
          : _gameFiles.cast<GameFile?>().firstWhere(
              (f) => f?.id == _activeGameFileId,
              orElse: () => null);

  // ── Init ──────────────────────────────────────────────────────────────────
  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();

    _isFirstRun = prefs.getBool('isFirstRun') ?? true;
    _adminPin = prefs.getString('adminPin') ?? '0000';

    final teamName = prefs.getString('team');
    if (teamName != null) {
      _team = TeamType.values.byName(teamName);
    }

    final playersJson = prefs.getString('players');
    if (playersJson != null) {
      final list = jsonDecode(playersJson) as List<dynamic>;
      _players = list
          .map((e) => Player.fromJson(e as Map<String, dynamic>))
          .toList();
    }

    final devicesJson = prefs.getString('devices');
    if (devicesJson != null) {
      final list = jsonDecode(devicesJson) as List<dynamic>;
      _devices = list
          .map((e) => DeviceInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }

    final filesJson = prefs.getString('gameFiles');
    if (filesJson != null) {
      final list = jsonDecode(filesJson) as List<dynamic>;
      _gameFiles = list
          .map((e) => GameFile.fromJson(e as Map<String, dynamic>))
          .toList();
    }

    _activeGameFileId = prefs.getString('activeGameFileId');
    _serverHost = prefs.getString('serverHost') ?? '127.0.0.1';
    _serverSyncEnabled = prefs.getBool('serverSyncEnabled') ?? true;

    if (_serverSyncEnabled) {
      await connectToServer(_serverHost);
      await refreshPlayersFromServer();
    }
  }

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('isFirstRun', _isFirstRun);
    await prefs.setString('team', _team.name);
    await prefs.setString('adminPin', _adminPin);
    await prefs.setString(
        'players', jsonEncode(_players.map((p) => p.toJson()).toList()));
    await prefs.setString(
        'devices', jsonEncode(_devices.map((d) => d.toJson()).toList()));
    await prefs.setString(
        'gameFiles', jsonEncode(_gameFiles.map((f) => f.toJson()).toList()));
    if (_activeGameFileId != null) {
      await prefs.setString('activeGameFileId', _activeGameFileId!);
    }
    await prefs.setString('serverHost', _serverHost);
    await prefs.setBool('serverSyncEnabled', _serverSyncEnabled);
  }

  // ── Server Integration ───────────────────────────────────────────────────
  Future<bool> connectToServer(String host, {int port = 8000}) async {
    _serverHost = host;
    _server = ServerIntegrationService(host, port: port);
    _serverSyncEnabled = true;
    _serverConnected = await _server!.testConnection();
    await _persist();
    notifyListeners();
    return _serverConnected;
  }

  Future<void> disableServerSync() async {
    _serverConnected = false;
    _serverSyncEnabled = false;
    _server = null;
    await _persist();
    notifyListeners();
  }

  Future<void> refreshPlayersFromServer() async {
    if (!_serverSyncEnabled || _server == null) return;
    final remotePlayers = await _server!.getPlayers();
    if (remotePlayers.isNotEmpty) {
      _players = remotePlayers;
      await _persist();
      notifyListeners();
    }
  }

  // ── Team / First Run ──────────────────────────────────────────────────────
  Future<void> completeFirstRunSetup({
    required TeamType team,
    required String pin,
    String? serverHost,
  }) async {
    _team = team;
    _adminPin = pin;
    _isFirstRun = false;
    _isAdmin = true;
    if (serverHost != null && serverHost.trim().isNotEmpty) {
      _serverHost = serverHost.trim();
    }
    await _persist();
    if (_serverSyncEnabled) {
      await connectToServer(_serverHost);
      await refreshPlayersFromServer();
    }
    notifyListeners();
  }

  // ── Admin Auth ────────────────────────────────────────────────────────────
  bool login(String pin) {
    if (pin == _adminPin) {
      _isAdmin = true;
      notifyListeners();
      return true;
    }
    return false;
  }

  void logout() {
    _isAdmin = false;
    notifyListeners();
  }

  Future<void> changePin(String newPin) async {
    _adminPin = newPin;
    await _persist();
    notifyListeners();
  }

  Future<void> setTeam(TeamType team) async {
    _team = team;
    await _persist();
    notifyListeners();
  }

  // ── Players ───────────────────────────────────────────────────────────────
  Future<void> addPlayer(Player p) async {
    _players.add(p);
    await _persist();
    if (_serverSyncEnabled && _server != null) {
      await _server!.syncPlayer(p);
    }
    notifyListeners();
  }

  Future<void> updatePlayer(Player p) async {
    final i = _players.indexWhere((x) => x.id == p.id);
    if (i >= 0) _players[i] = p;
    await _persist();
    if (_serverSyncEnabled && _server != null) {
      await _server!.syncPlayer(p);
    }
    notifyListeners();
  }

  Future<void> removePlayer(String id) async {
    _players.removeWhere((p) => p.id == id);
    await _persist();
    notifyListeners();
  }

  Future<void> addReport(String playerId, PlayerReport report) async {
    final player = _players.cast<Player?>().firstWhere(
        (p) => p?.id == playerId,
        orElse: () => null);
    if (player != null) {
      player.reports.add(report);
      await _persist();
      notifyListeners();
    }
  }

  // ── Devices ───────────────────────────────────────────────────────────────
  Future<void> addDevice(DeviceInfo d) async {
    _devices.add(d);
    await _persist();
    notifyListeners();
  }

  Future<void> updateDevice(DeviceInfo d) async {
    final i = _devices.indexWhere((x) => x.id == d.id);
    if (i >= 0) _devices[i] = d;
    await _persist();
    notifyListeners();
  }

  Future<void> removeDevice(String id) async {
    _devices.removeWhere((d) => d.id == id);
    await _persist();
    notifyListeners();
  }

  // ── Game Files ────────────────────────────────────────────────────────────
  Future<void> addGameFile(GameFile f) async {
    _gameFiles.add(f);
    await _persist();
    notifyListeners();
  }

  Future<void> updateGameFile(GameFile f) async {
    final i = _gameFiles.indexWhere((x) => x.id == f.id);
    if (i >= 0) _gameFiles[i] = f;
    await _persist();
    notifyListeners();
  }

  Future<void> removeGameFile(String id) async {
    _gameFiles.removeWhere((f) => f.id == id);
    if (_activeGameFileId == id) _activeGameFileId = null;
    await _persist();
    notifyListeners();
  }

  Future<void> setActiveGameFile(String? id) async {
    _activeGameFileId = id;
    await _persist();
    notifyListeners();
  }

  // ── Game Sessions ─────────────────────────────────────────────────────────
  Future<void> startSession(String gameFileId, GameSession session) async {
    final file = _gameFiles.cast<GameFile?>().firstWhere(
        (f) => f?.id == gameFileId,
        orElse: () => null);
    if (file != null) {
      session.isActive = true;
      session.startTime = DateTime.now();
      file.sessions.add(session);
      _activeGameFileId = gameFileId;
      await _persist();
      if (_serverSyncEnabled && _server != null) {
        await _server!.recordGameEvent(
          sessionId: session.id,
          eventType: 'session_start',
          description: 'Session started: ${session.gameModeName}',
        );
      }
      notifyListeners();
    }
  }

  Future<void> endSession(String gameFileId, String sessionId) async {
    final file = _gameFiles.cast<GameFile?>().firstWhere(
        (f) => f?.id == gameFileId,
        orElse: () => null);
    if (file != null) {
      final session = file.sessions.cast<GameSession?>().firstWhere(
          (s) => s?.id == sessionId,
          orElse: () => null);
      if (session != null) {
        session.isActive = false;
        session.endTime = DateTime.now();
        await _persist();
        if (_serverSyncEnabled && _server != null) {
          await _server!.recordGameEvent(
            sessionId: session.id,
            eventType: 'session_end',
            description: 'Session ended: ${session.gameModeName}',
          );
        }
        notifyListeners();
      }
    }
  }

  Future<void> incrementRespawn(
      String gameFileId, String sessionId, TeamType team) async {
    final file = _gameFiles.cast<GameFile?>().firstWhere(
        (f) => f?.id == gameFileId,
        orElse: () => null);
    if (file != null) {
      final session = file.sessions.cast<GameSession?>().firstWhere(
          (s) => s?.id == sessionId,
          orElse: () => null);
      if (session != null) {
        session.respawnCounts[team] =
            (session.respawnCounts[team] ?? 0) + 1;
        await _persist();
        if (_serverSyncEnabled && _server != null) {
          await _server!.recordGameEvent(
            sessionId: session.id,
            eventType: 'respawn_activated',
            description: 'Respawn: ${team.displayName}',
          );
        }
        notifyListeners();
      }
    }
  }

  // ── Field Map ─────────────────────────────────────────────────────────────
  Future<void> updateFieldMap(String gameFileId, FieldMapData map) async {
    final file = _gameFiles.cast<GameFile?>().firstWhere(
        (f) => f?.id == gameFileId,
        orElse: () => null);
    if (file != null) {
      file.fieldMap = map;
      await _persist();
      notifyListeners();
    }
  }

  // ── Comms ─────────────────────────────────────────────────────────────────
  Future<void> addCommsMessage(
      String gameFileId, CommsMessage msg) async {
    final file = _gameFiles.cast<GameFile?>().firstWhere(
        (f) => f?.id == gameFileId,
        orElse: () => null);
    if (file != null) {
      file.commsLog.add(msg);
      await _persist();
      if (_serverSyncEnabled && _server != null) {
        await _server!.postCommsMessage(
          sender: msg.sender,
          text: msg.text,
          messageType: msg.type.name,
        );
      }
      notifyListeners();
    }
  }
}
