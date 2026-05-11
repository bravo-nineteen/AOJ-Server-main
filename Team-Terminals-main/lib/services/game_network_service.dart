import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// Simple UDP + TCP service for syncing respawn counts between two tablets
/// on the same WiFi network.
///
/// Usage:
///   - One tablet calls [startServer] (listens on [tcpPort]).
///   - The other calls [discover] to find the server via UDP broadcast,
///     then [connectToServer] with the discovered address.
///   - Both sides can call [sendRespawn] / [requestSync].
///   - Listen to [events] stream for incoming messages.

const int _udpPort = 47730;
const int tcpPort = 47731;

enum NetEventType { respawn, sessionStart, sessionEnd, syncState, ping }

class NetEvent {
  final NetEventType type;
  final Map<String, dynamic> payload;
  NetEvent(this.type, this.payload);
}

class GameNetworkService {
  RawDatagramSocket? _udp;
  ServerSocket? _server;
  Socket? _client;
  final _controller = StreamController<NetEvent>.broadcast();

  Stream<NetEvent> get events => _controller.stream;
  bool get isServer => _server != null;
  bool get isConnected => _client != null;

  // ── Server ────────────────────────────────────────────────────────────────
  Future<void> startServer() async {
    _server = await ServerSocket.bind(InternetAddress.anyIPv4, tcpPort);
    _server!.listen((socket) {
      _client = socket;
      _listenOnSocket(socket);
    });

    // UDP beacon so clients can discover us
    _udp = await RawDatagramSocket.bind(InternetAddress.anyIPv4, _udpPort);
    _udp!.broadcastEnabled = true;
    _udp!.listen((event) {
      if (event == RawSocketEvent.read) {
        final dg = _udp!.receive();
        if (dg != null) {
          final msg = utf8.decode(dg.data);
          if (msg == 'TT_DISCOVER') {
            _udp!.send(
                utf8.encode('TT_HERE'),
                dg.address,
                _udpPort);
          }
        }
      }
    });
  }

  // ── Client ────────────────────────────────────────────────────────────────

  /// Returns the IP address of the first server found, or null on timeout.
  Future<String?> discover({Duration timeout = const Duration(seconds: 5)}) async {
    final udp =
        await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
    udp.broadcastEnabled = true;

    final completer = Completer<String?>();

    udp.listen((event) {
      if (event == RawSocketEvent.read) {
        final dg = udp.receive();
        if (dg != null && utf8.decode(dg.data) == 'TT_HERE') {
          if (!completer.isCompleted) {
            completer.complete(dg.address.address);
          }
        }
      }
    });

    udp.send(
        utf8.encode('TT_DISCOVER'),
        InternetAddress('255.255.255.255'),
        _udpPort);

    Future.delayed(timeout, () {
      if (!completer.isCompleted) completer.complete(null);
      udp.close();
    });

    return completer.future;
  }

  Future<bool> connectToServer(String host) async {
    try {
      final socket = await Socket.connect(host, tcpPort,
          timeout: const Duration(seconds: 5));
      _client = socket;
      _listenOnSocket(socket);
      return true;
    } catch (_) {
      return false;
    }
  }

  // ── Send ──────────────────────────────────────────────────────────────────
  void sendRespawn(String team) => _send('respawn', {'team': team});
  void sendSessionStart(Map<String, dynamic> session) =>
      _send('sessionStart', session);
  void sendSessionEnd(String sessionId) =>
      _send('sessionEnd', {'id': sessionId});
  void sendSync(Map<String, dynamic> state) => _send('syncState', state);
  void sendPing() => _send('ping', {});

  void _send(String type, Map<String, dynamic> payload) {
    if (_client == null) return;
    final msg = jsonEncode({'type': type, ...payload}) + '\n';
    _client!.write(msg);
  }

  // ── Receive ───────────────────────────────────────────────────────────────
  void _listenOnSocket(Socket socket) {
    socket.transform(utf8.decoder).transform(const LineSplitter()).listen(
      (line) {
        try {
          final data = jsonDecode(line) as Map<String, dynamic>;
          final typeStr = data['type'] as String;
          final type = NetEventType.values
              .firstWhere((e) => e.name == typeStr,
                  orElse: () => NetEventType.ping);
          _controller.add(NetEvent(type, data));
        } catch (_) {}
      },
      onError: (_) => _cleanup(),
      onDone: _cleanup,
    );
  }

  void _cleanup() {
    _client = null;
  }

  // ── Dispose ───────────────────────────────────────────────────────────────
  Future<void> dispose() async {
    _client?.destroy();
    _server?.close();
    _udp?.close();
    await _controller.close();
  }
}
