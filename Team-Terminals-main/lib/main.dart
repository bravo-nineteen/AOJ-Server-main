import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'providers/app_state.dart';
import 'theme/app_themes.dart';
import 'screens/desktop_screen.dart';
import 'screens/admin/team_setup_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Lock to landscape — tablets only
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);

  // Full immersive: hide status + nav bars for a true desktop feel
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);

  final appState = AppState();
  await appState.init();

  runApp(
    ChangeNotifierProvider.value(
      value: appState,
      child: const TeamTerminalsApp(),
    ),
  );
}

class TeamTerminalsApp extends StatelessWidget {
  const TeamTerminalsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, state, _) {
        return MaterialApp(
          title: 'Team Terminals',
          debugShowCheckedModeBanner: false,
          theme: state.team == TeamType.taskForceOnyx
              ? AppThemes.onyxTheme
              : AppThemes.blackTalonTheme,
          home: state.isFirstRun
              ? const TeamSetupScreen()
              : const DesktopScreen(),
        );
      },
    );
  }
}
