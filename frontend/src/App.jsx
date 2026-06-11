import { useEffect, useMemo, useRef, useState } from 'react';
import { AdminCustomTeams } from './components/AdminCustomTeams';
import { AdminGameModes } from './components/AdminGameModes';
import { AdminKnowledgeBase } from './components/AdminKnowledgeBase';
import { AdminThemeEditor } from './components/AdminThemeEditor';
import { AdminAISettings } from './components/AdminAISettings';

const APPS = [
  { id: 'overview', title: 'Overview', subtitle: 'Today plan, team posture, and IoT readiness', badge: 'OV' },
  { id: 'mission-control', title: 'Mission Control', subtitle: 'Live objectives, results, and squad directives', badge: 'MC' },
  { id: 'prop-network', title: 'Prop Network', subtitle: 'Field devices, relays, and trigger nodes', badge: 'PN' },
  { id: 'schedule', title: 'Schedule', subtitle: 'Operations timeline and event sequencing', badge: 'SC' },
  { id: 'system-monitor', title: 'System Monitor', subtitle: 'Runtime health and resource telemetry', badge: 'SM' },
  { id: 'ai-assistant', title: 'AI Assistant', subtitle: 'Command aide for planning and analysis', badge: 'AI' },
  { id: 'update-center', title: 'Update Center', subtitle: 'Node sync, package state, firmware rollout', badge: 'UP' },
  { id: 'logs', title: 'Logs', subtitle: 'Audit stream and anomaly events', badge: 'LG' },
  { id: 'settings', title: 'Settings', subtitle: 'Teams, game modes, themes, AI, and system controls', badge: 'ST' },
];

const DESKTOP_LAYOUT_COLUMNS = 3;
const DESKTOP_LAYOUT_ROWS = 3;
const DESKTOP_LAYOUT_STORAGE_KEY = 'aoj-command-os.desktop-layout.v1';
const UI_PREFS_STORAGE_KEY = 'aoj-command-os.ui-prefs.v1';

const DEFAULT_UI_PREFS = {
  showLiveFeed: false,
};

function createDefaultDesktopLayout() {
  return APPS.reduce((layout, app, index) => {
    layout[app.id] = {
      col: index % DESKTOP_LAYOUT_COLUMNS,
      row: Math.floor(index / DESKTOP_LAYOUT_COLUMNS),
    };
    return layout;
  }, {});
}

function clampCell(value, max) {
  return Math.max(0, Math.min(max, value));
}

function normalizeDesktopLayout(layout) {
  const fallback = createDefaultDesktopLayout();
  if (!layout || typeof layout !== 'object') {
    return fallback;
  }

  const normalized = { ...fallback };
  const taken = new Set();

  APPS.forEach((app) => {
    const item = layout[app.id];
    const col = clampCell(Number(item?.col ?? fallback[app.id].col), DESKTOP_LAYOUT_COLUMNS - 1);
    const row = clampCell(Number(item?.row ?? fallback[app.id].row), DESKTOP_LAYOUT_ROWS - 1);
    const key = `${col}:${row}`;
    if (!taken.has(key)) {
      normalized[app.id] = { col, row };
      taken.add(key);
    }
  });

  APPS.forEach((app) => {
    const current = normalized[app.id];
    let key = `${current.col}:${current.row}`;
    if (taken.has(key)) {
      return;
    }
    for (let row = 0; row < DESKTOP_LAYOUT_ROWS; row += 1) {
      for (let col = 0; col < DESKTOP_LAYOUT_COLUMNS; col += 1) {
        key = `${col}:${row}`;
        if (!taken.has(key)) {
          normalized[app.id] = { col, row };
          taken.add(key);
          return;
        }
      }
    }
  });

  return normalized;
}

function loadDesktopLayout() {
  if (typeof window === 'undefined') {
    return createDefaultDesktopLayout();
  }

  try {
    const raw = window.localStorage.getItem(DESKTOP_LAYOUT_STORAGE_KEY);
    if (!raw) {
      return createDefaultDesktopLayout();
    }
    return normalizeDesktopLayout(JSON.parse(raw));
  } catch {
    return createDefaultDesktopLayout();
  }
}

function loadUiPrefs() {
  if (typeof window === 'undefined') {
    return { ...DEFAULT_UI_PREFS };
  }

  try {
    const raw = window.localStorage.getItem(UI_PREFS_STORAGE_KEY);
    if (!raw) {
      return { ...DEFAULT_UI_PREFS };
    }
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_UI_PREFS,
      ...parsed,
    };
  } catch {
    return { ...DEFAULT_UI_PREFS };
  }
}

function swapDesktopCell(layout, movingAppId, targetCol, targetRow) {
  const next = { ...layout };
  const source = next[movingAppId] || { col: 0, row: 0 };
  const targetKey = `${targetCol}:${targetRow}`;
  const occupiedApp = APPS.find((app) => {
    const slot = next[app.id];
    return app.id !== movingAppId && slot && `${slot.col}:${slot.row}` === targetKey;
  });

  next[movingAppId] = { col: targetCol, row: targetRow };

  if (occupiedApp) {
    next[occupiedApp.id] = source;
  }

  return normalizeDesktopLayout(next);
}

const WINDOW_CONTENT = {
  'prop-network': ['12 props registered on subnet', '2 relays in maintenance state', 'Latency envelope: 18ms average'],
  schedule: ['14:00 Briefing', '14:20 Session Alpha launch', '15:10 Mission reset and scoreboard review'],
  'system-monitor': ['CPU Load: 27%', 'Memory: 41%', 'Storage: 66% used'],
  'ai-assistant': ['Suggested route: flank eastern treeline', 'Probability of hold success: 76%', 'Reinforcement advice ready'],
  'update-center': ['Core package sync: completed', 'Firmware queue: 2 pending', 'Last rollout: 08:43 local'],
  logs: ['INFO mission channel established', 'WARN prop relay-03 unstable', 'INFO schedule item accepted'],
  settings: ['LAN mode: enabled', 'WebSocket endpoint: armed', 'Operator profile: command-admin'],
};

const DEFAULT_MISSION_STATE = {
  mission_id: null,
  mission_title: 'No mission loaded',
  game_mode: 'Skirmish',
  state: 'idle',
  main_timer_seconds: 0,
  phase_timer_seconds: 0,
  red_team_score: 0,
  blue_team_score: 0,
  objectives: [],
  props_needed: [],
  prop_settings: {},
  event_feed: [],
  updated_at: '',
};

const DEFAULT_GAME_MODES = ['Skirmish', 'Domination', 'Capture Point', 'Hostage Rescue'];
const ACTIVITY_TYPES = [
  'Safety Brief',
  'Game',
  'Break',
  'Lunch',
  'Pickup',
  'Drop Off',
  'Setup',
  'Pack Down',
  'Custom',
];
const WINNER_OPTIONS = ['Red', 'Blue', 'Draw', 'Cancelled'];
const PROP_TYPES = [
  'Bomb',
  'Bomb Vest',
  'Briefcase Bomb',
  'Domination Point',
  'Respawn Station',
  'Game Master Unit',
  'Control Panel Unit',
];
const FIRMWARE_PROP_TYPE_TO_NAME = {
  Bomb: 'prop_bomb',
  'Bomb Vest': 'Bomb_Vest',
  'Briefcase Bomb': 'Briefcase_Bomb',
  'Domination Point': 'domination_point',
  'Respawn Station': 'respawn_station',
  'Game Master Unit': 'GM_Unit',
  'Control Panel Unit': 'CP_Unit',
};
const ALWAYS_INCLUDED_PROP_NAMES = new Set(['CP_Unit_TF', 'CP_Unit_BF', 'GM_Unit']);
const LOG_LEVELS = ['ALL', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
const LOG_CATEGORIES = ['ALL', 'SYSTEM', 'MISSION', 'PROP', 'LORA', 'WIFI', 'AI', 'UPDATE'];
const AI_QUICK_PROMPTS = [
  'Suggest a game for 16 players',
  'Build domination rules for 20 players',
  'Create marshal briefing',
  'Summarize results',
  'Check schedule delay',
  'Handle team handicap of 30%',
];

const DEFAULT_SYSTEM_STATUS = {
  status: 'online',
  uptime_seconds: 0,
  connected_clients: 0,
  active_game_sessions: 0,
  entity_counts: {},
  backend_version: '0.1.0',
  platform_mode: 'mock',
  cpu_temperature_c: 0,
  cpu_usage_percent: 0,
  ram_usage_percent: 0,
  disk_usage_percent: 0,
  lora_service_status: 'unknown',
  database_status: 'unknown',
};

const DEFAULT_UPDATE_CENTER_STATUS = {
  system_version: '0.1.0',
  frontend_version: 'unknown',
  backend_version: 'unknown',
  database_version: 'unknown',
  database_path: '',
  latest_backup: null,
  firmware_packages_count: 0,
  last_firmware_rollout: null,
  changelog: [],
};

function formatDuration(totalSeconds) {
  const safe = Math.max(0, Number(totalSeconds) || 0);
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function toDateTimeInputValue(isoDate) {
  if (!isoDate) {
    return '';
  }
  const date = new Date(isoDate);
  const pad = (value) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatUptime(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m ${secs}s`;
  }
  return `${hours}h ${minutes}m ${secs}s`;
}

function toTodayIsoFromTime(timeValue) {
  if (!timeValue) {
    return null;
  }
  const [hRaw, mRaw] = String(timeValue).split(':');
  const hours = Number(hRaw);
  const minutes = Number(mRaw);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) {
    return null;
  }
  // Build a naive local datetime string (no timezone suffix) so the backend stores
  // exactly the time the user entered, regardless of timezone.
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const hh = String(hours).padStart(2, '0');
  const mi = String(minutes).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}:00`;
}

function addMinutesLocal(localIso, mins) {
  const dt = new Date(localIso);
  dt.setMinutes(dt.getMinutes() + mins);
  const yyyy = dt.getFullYear();
  const mm = String(dt.getMonth() + 1).padStart(2, '0');
  const dd = String(dt.getDate()).padStart(2, '0');
  const hh = String(dt.getHours()).padStart(2, '0');
  const mi = String(dt.getMinutes()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}:00`;
}

function militaryTime(date) {
  if (!date) return 'TBD';
  const d = typeof date === 'string' ? new Date(date) : date;
  const h = String(d.getHours()).padStart(2, '0');
  const m = String(d.getMinutes()).padStart(2, '0');
  return `${h}${m} hours`;
}

function toTimeInputValue(isoDate) {
  if (!isoDate) {
    return '';
  }
  const dt = new Date(isoDate);
  const h = String(dt.getHours()).padStart(2, '0');
  const m = String(dt.getMinutes()).padStart(2, '0');
  return `${h}:${m}`;
}

function formatFeedTime(value = new Date()) {
  return value.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

function normalizeFirmwarePropName(item) {
  const canonical = FIRMWARE_PROP_TYPE_TO_NAME[item.prop_type];
  if (!canonical) {
    return null;
  }

  if (canonical !== 'CP_Unit') {
    return canonical;
  }

  const lookup = `${item.name || ''} ${item.device_id || ''}`.toLowerCase();
  if (lookup.includes('tf')) {
    return 'CP_Unit_TF';
  }
  if (lookup.includes('bf') || lookup.includes('bt')) {
    return 'CP_Unit_BF';
  }
  return null;
}

function normalizeFirmwareProps(list) {
  return list
    .map((item) => {
      const normalizedName = normalizeFirmwarePropName(item);
      if (!normalizedName) {
        return null;
      }
      return {
        ...item,
        name: normalizedName,
      };
    })
    .filter(Boolean);
}

function App() {
  const host = window.location.hostname || 'localhost';
  const isSecure = window.location.protocol === 'https:';
  // In GitHub Codespaces (and similar tunnels) each port gets its own hostname,
  // e.g. crispy-engine-...-5173.app.github.dev → crispy-engine-...-8000.app.github.dev
  const backendHost = useMemo(() => {
    if (isSecure && host.includes('-5173.')) {
      return host.replace('-5173.', '-8000.');
    }
    return host;
  }, [host, isSecure]);
  const apiBase = useMemo(() => {
    // When frontend is served by backend on :8000, use same-origin API paths.
    if (window.location.port === '8000') {
      return '/api';
    }
    // When on Vite dev server (port 5173), use the Vite proxy (same-origin).
    // This avoids CORS and mixed-protocol issues in Codespaces/tunnels.
    if (window.location.port === '5173' || window.location.port === '') {
      return '/api';
    }
    const scheme = isSecure ? 'https' : 'http';
    const port = isSecure ? '' : ':8000';
    return `${scheme}://${backendHost}${port}/api`;
  }, [backendHost, isSecure]);
  const wsUrl = useMemo(() => {
    // Use same-origin WebSocket when proxied through Vite dev server.
    if (window.location.port === '5173' || (isSecure && window.location.port === '')) {
      const wsScheme = isSecure ? 'wss' : 'ws';
      return `${wsScheme}://${window.location.host}/ws/live`;
    }
    const scheme = isSecure ? 'wss' : 'ws';
    const port = isSecure ? '' : ':8000';
    return `${scheme}://${backendHost}${port}/ws/live`;
  }, [backendHost, isSecure]);
  const apiOrigin = useMemo(() => {
    return apiBase.endsWith('/api') ? apiBase.slice(0, -4) : apiBase;
  }, [apiBase]);

  const [networkStatus, setNetworkStatus] = useState('CONNECTING');
  const [events, setEvents] = useState([]);
  const [selectedApp, setSelectedApp] = useState(APPS[0].id);
  const [windowOpen, setWindowOpen] = useState(true);
  const [windowMinimized, setWindowMinimized] = useState(false);
  const [desktopLayout, setDesktopLayout] = useState(() => loadDesktopLayout());
  const [draggedAppId, setDraggedAppId] = useState(null);
  const [hoverCell, setHoverCell] = useState(null);
  const [uiPrefs, setUiPrefs] = useState(() => loadUiPrefs());
  const [clock, setClock] = useState(new Date());
  const [currentTheme, setCurrentTheme] = useState(null);
  const [customTeams, setCustomTeams] = useState([]);
  const [customGameModes, setCustomGameModes] = useState([]);
  const [settingsTab, setSettingsTab] = useState('general');
  const [selectedScheduleGame, setSelectedScheduleGame] = useState(null);
  const [missionState, setMissionState] = useState(DEFAULT_MISSION_STATE);
  const [manualScoreDelta, setManualScoreDelta] = useState({ red: 10, blue: 10 });
  const [teamReadyState, setTeamReadyState] = useState({ red: false, blue: false });
  const [countdown, setCountdown] = useState(null);
  const [gameModeOptions, setGameModeOptions] = useState(DEFAULT_GAME_MODES);
  const [missionForm, setMissionForm] = useState({
    title: 'Operation Echo',
    description: 'Field objective sequence for Sector Echo.',
    game_mode: DEFAULT_GAME_MODES[0],
    main_timer_minutes: 30,
    phase_timer_minutes: 5,
    objectivesText: 'Capture Relay,Hold HQ,Extract VIP',
    props_needed: [],
    prop_settings: {},
  });
  const [scheduleItems, setScheduleItems] = useState([]);
  const [scheduleOverview, setScheduleOverview] = useState({
    current_activity: null,
    next_activity: null,
    delay_warning: null,
  });
  const [editingScheduleId, setEditingScheduleId] = useState(null);
  const [scheduleSaveError, setScheduleSaveError] = useState('');
  const [scheduleForm, setScheduleForm] = useState({
    title: 'Safety Briefing',
    details: 'Operator brief and radio checks.',
    activity_type: 'Safety Brief',
    game_mode: '',
    props_needed: [],
    start_time: '',
    is_complete: false,
  });
  const [recordingResultForItemId, setRecordingResultForItemId] = useState(null);
  const [quickResultForm, setQuickResultForm] = useState({
    winner: 'Draw',
    red_points: 0,
    blue_points: 0,
    notes: '',
  });
  const [presetSaveStatus, setPresetSaveStatus] = useState('');
  const [resultsHistory, setResultsHistory] = useState([]);
  const [resultsSummary, setResultsSummary] = useState({
    total_red_wins: 0,
    total_blue_wins: 0,
    total_draws: 0,
    total_cancelled: 0,
    total_red_points: 0,
    total_blue_points: 0,
  });
  const [propsList, setPropsList] = useState([]);
  const [editingPropId, setEditingPropId] = useState(null);
  const [propSaveError, setPropSaveError] = useState('');
  const [announcementRules, setAnnouncementRules] = useState([]);
  const [editingRuleId, setEditingRuleId] = useState(null);
  const [ruleForm, setRuleForm] = useState({
    name: '',
    enabled: true,
    trigger_activity_types: '',
    trigger_minutes_before: 15,
    message_template: '',
  });
  const [issuedPropTokens, setIssuedPropTokens] = useState({});
  const [propForm, setPropForm] = useState({
    device_id: '',
    name: '',
    prop_type: 'Custom',
    location: '',
    firmware_version: '',
    auth_token: '',
  });
  const [systemLogs, setSystemLogs] = useState([]);
  const [logFilters, setLogFilters] = useState({ level: 'ALL', category: 'ALL' });
  const [systemStatus, setSystemStatus] = useState(DEFAULT_SYSTEM_STATUS);
  const [aiInput, setAiInput] = useState('');
  const [aiConversationId, setAiConversationId] = useState(null);
  const [aiTyping, setAiTyping] = useState(false);
  const aiChatEndRef = useRef(null);
  const [announcementText, setAnnouncementText] = useState('');
  const [aiMessages, setAiMessages] = useState([]);
  const [updateCenterStatus, setUpdateCenterStatus] = useState(DEFAULT_UPDATE_CENTER_STATUS);
  const [updateMessage, setUpdateMessage] = useState('');
  const [selectedUpdatePackage, setSelectedUpdatePackage] = useState(null);
  const [firmwarePackages, setFirmwarePackages] = useState([]);
  const [firmwareVersion, setFirmwareVersion] = useState('');
  const [firmwareNotes, setFirmwareNotes] = useState('');
  const [selectedFirmwarePackageId, setSelectedFirmwarePackageId] = useState('');
  const [selectedFirmwarePropIds, setSelectedFirmwarePropIds] = useState([]);
  const [firmwareRollouts, setFirmwareRollouts] = useState([]);
  const [scoreTrend, setScoreTrend] = useState([]);
  const [deviceHealthTrend, setDeviceHealthTrend] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState('');
  const [voiceNote, setVoiceNote] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [aiAudioSettings, setAiAudioSettings] = useState({
    voice_enabled: false,
    speech_to_text_enabled: false,
    text_to_speech_enabled: false,
  });
  const recognitionRef = useRef(null);
  const currentAudioRef = useRef(null);
  const currentAudioUrlRef = useRef(null);
  const desktopSurfaceRef = useRef(null);
  const desktopLayoutRef = useRef(desktopLayout);
  const desktopDragRef = useRef(null);
  const suppressDesktopClickRef = useRef(false);

  const speechRecognitionCtor = useMemo(() => {
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }, []);

  const speechInputSupported = Boolean(speechRecognitionCtor);
  const speechOutputSupported = typeof window.Audio !== 'undefined';
  const aiVoiceInputEnabled = aiAudioSettings.voice_enabled && aiAudioSettings.speech_to_text_enabled;
  const aiVoiceOutputEnabled = aiAudioSettings.voice_enabled && aiAudioSettings.text_to_speech_enabled;

  useEffect(() => {
    desktopLayoutRef.current = desktopLayout;
    try {
      window.localStorage.setItem(DESKTOP_LAYOUT_STORAGE_KEY, JSON.stringify(desktopLayout));
    } catch {
      // Ignore storage failures on restricted browsers.
    }
  }, [desktopLayout]);

  useEffect(() => {
    try {
      window.localStorage.setItem(UI_PREFS_STORAGE_KEY, JSON.stringify(uiPrefs));
    } catch {
      // Ignore storage failures on restricted browsers.
    }
  }, [uiPrefs]);

  useEffect(() => {
    function handlePointerMove(event) {
      const drag = desktopDragRef.current;
      const surface = desktopSurfaceRef.current;
      if (!drag || !surface) {
        return;
      }

      const dx = Math.abs(event.clientX - drag.startX);
      const dy = Math.abs(event.clientY - drag.startY);
      if (Math.max(dx, dy) > 8) {
        drag.moved = true;
      }

      const rect = surface.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) {
        return;
      }

      const cellWidth = rect.width / DESKTOP_LAYOUT_COLUMNS;
      const cellHeight = rect.height / DESKTOP_LAYOUT_ROWS;
      const targetCol = clampCell(Math.floor((event.clientX - rect.left) / cellWidth), DESKTOP_LAYOUT_COLUMNS - 1);
      const targetRow = clampCell(Math.floor((event.clientY - rect.top) / cellHeight), DESKTOP_LAYOUT_ROWS - 1);
      drag.target = { col: targetCol, row: targetRow };
      setHoverCell(drag.target);
    }

    function handlePointerUp() {
      const drag = desktopDragRef.current;
      if (!drag) {
        return;
      }

      if (drag.moved && drag.target) {
        suppressDesktopClickRef.current = true;
        setDesktopLayout((current) => swapDesktopCell(current, drag.appId, drag.target.col, drag.target.row));
        window.setTimeout(() => {
          suppressDesktopClickRef.current = false;
        }, 0);
      }

      desktopDragRef.current = null;
      setDraggedAppId(null);
      setHoverCell(null);
    }

    if (!draggedAppId) {
      return undefined;
    }

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);
    window.addEventListener('pointercancel', handlePointerUp);

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
      window.removeEventListener('pointercancel', handlePointerUp);
    };
  }, [draggedAppId]);

  function handleDesktopPointerDown(event, appId) {
    if (event.button !== 0 && event.pointerType !== 'touch') {
      return;
    }

    const surface = desktopSurfaceRef.current;
    if (!surface) {
      return;
    }

    event.preventDefault();
    const origin = desktopLayoutRef.current[appId] || { col: 0, row: 0 };
    desktopDragRef.current = {
      appId,
      startX: event.clientX,
      startY: event.clientY,
      moved: false,
      origin,
      target: origin,
    };
    setDraggedAppId(appId);
    setHoverCell(origin);
  }

  function handleDesktopIconClick(event, appId) {
    if (suppressDesktopClickRef.current) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    setSelectedApp(appId);
    setWindowOpen(true);
    setWindowMinimized(false);
  }

  function resetDesktopLayout() {
    setDesktopLayout(createDefaultDesktopLayout());
  }

  function openDesktopWindow(appId) {
    setSelectedApp(appId);
    setWindowOpen(true);
    setWindowMinimized(false);
  }

  function closeDesktopWindow() {
    setWindowOpen(false);
    setWindowMinimized(false);
  }

  function minimizeDesktopWindow() {
    if (!windowOpen) {
      return;
    }
    setWindowMinimized(true);
  }

  function restoreDesktopWindow() {
    setWindowOpen(true);
    setWindowMinimized(false);
  }

  const redTeamLabel = customTeams[0]?.name || 'Red Team';
  const blueTeamLabel = customTeams[1]?.name || 'Blue Team';

  function resolveTeamLogoUrl(icon) {
    if (!icon || typeof icon !== 'string') {
      return '';
    }
    if (icon.startsWith('http://') || icon.startsWith('https://') || icon.startsWith('data:')) {
      return icon;
    }
    if (icon.startsWith('/')) {
      return `${apiOrigin}${icon}`;
    }
    return `${apiOrigin}/${icon}`;
  }

  async function fetchMissionState() {
    const response = await fetch(`${apiBase}/mission-control/state`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setMissionState(payload);
    setEvents(payload.event_feed ?? []);
  }

  async function fetchGameModeOptions() {
    try {
      const response = await fetch(`${apiBase}/custom/game-modes`);
      if (!response.ok) {
        setGameModeOptions(DEFAULT_GAME_MODES);
        setCustomGameModes([]);
        return;
      }

      const rows = await response.json();
      const activeRows = rows.filter((mode) => mode.active);
      setCustomGameModes(activeRows);
      const activeCustomModes = rows
        .filter((mode) => mode.active)
        .map((mode) => mode.name)
        .filter((name) => typeof name === 'string' && name.trim().length > 0);

      if (activeCustomModes.length === 0) {
        setGameModeOptions(DEFAULT_GAME_MODES);
        return;
      }

      const merged = Array.from(new Set([...activeCustomModes, ...DEFAULT_GAME_MODES]));
      setGameModeOptions(merged);
      setMissionForm((current) => {
        if (merged.includes(current.game_mode)) {
          return current;
        }
        return { ...current, game_mode: merged[0] };
      });
    } catch {
      setGameModeOptions(DEFAULT_GAME_MODES);
      setCustomGameModes([]);
    }
  }

  async function fetchCustomTeams() {
    try {
      const response = await fetch(`${apiBase}/custom/teams`);
      if (!response.ok) {
        setCustomTeams([]);
        return;
      }
      const rows = await response.json();
      const activeTeams = rows.filter((team) => team.active);
      setCustomTeams(activeTeams);
    } catch {
      setCustomTeams([]);
    }
  }

  async function fetchAiSettings() {
    try {
      const response = await fetch(`${apiBase}/ai/settings`);
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      setAiAudioSettings({
        voice_enabled: Boolean(payload.voice_enabled),
        speech_to_text_enabled: Boolean(payload.speech_to_text_enabled),
        text_to_speech_enabled: Boolean(payload.text_to_speech_enabled),
      });
    } catch {
      // Keep current settings on fetch failure.
    }
  }

  async function postMissionAction(path, body) {
    const response = await fetch(`${apiBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setMissionState(payload);
    setEvents(payload.event_feed ?? []);
    if (path === '/mission-control/end') {
      fetchResultsData();
    }
  }

  async function applyManualScore(team, direction = 1) {
    const raw = Number.parseInt(String(manualScoreDelta[team] ?? 0), 10);
    const amount = Number.isFinite(raw) ? Math.abs(raw) : 0;
    if (!amount) {
      return;
    }
    await postMissionAction('/mission-control/score', {
      team,
      delta: direction * amount,
      reason: 'manual',
    });
  }

  async function markTeamReady(team) {
    await fetch(`${apiBase}/mission-control/ready`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team }),
    });
  }

  async function resetReady() {
    await fetch(`${apiBase}/mission-control/ready`, { method: 'DELETE' });
  }

  function applyThemeToDOM(theme) {
    if (!theme) return;
    
    const root = document.documentElement;
    root.style.setProperty('--primary-color', theme.primary_color || '#000000');
    root.style.setProperty('--secondary-color', theme.secondary_color || '#ffffff');
    root.style.setProperty('--accent-color', theme.accent_color || '#ff0000');
    root.style.setProperty('--background-color', theme.background_color || '#1a1a1a');
    root.style.setProperty('--panel-color', theme.panel_color || '#2a2a2a');
    root.style.setProperty('--text-color', theme.text_color || '#ffffff');
    root.style.setProperty('--warning-color', theme.warning_color || '#ffaa00');
    root.style.setProperty('--danger-color', theme.danger_color || '#ff3333');
    root.style.setProperty('--success-color', theme.success_color || '#00ff00');
    root.style.setProperty('--border-radius', theme.border_radius || '4px');
    root.style.setProperty('--font-family', theme.font_family || 'Arial, sans-serif');
    root.style.setProperty('--density', theme.density || 'normal');
    // Keep legacy variables in sync for existing styles.
    root.style.setProperty('--ink-0', theme.background_color || '#1a1a1a');
    root.style.setProperty('--ink-1', theme.primary_color || '#000000');
    root.style.setProperty('--ink-2', theme.panel_color || '#2a2a2a');
    root.style.setProperty('--line', theme.secondary_color || '#ffffff');
    root.style.setProperty('--line-bright', theme.accent_color || '#ff0000');
    root.style.setProperty('--hud', theme.accent_color || '#ff0000');
    root.style.setProperty('--warn', theme.warning_color || '#ffaa00');
    root.style.setProperty('--text-main', theme.text_color || '#ffffff');
  }

  function startVoiceInput() {
    if (!aiVoiceInputEnabled) {
      setSpeechError('Voice input is disabled in AI settings.');
      return;
    }
    if (!speechRecognitionCtor) {
      setSpeechError('Speech input is not supported by this browser.');
      return;
    }

    setSpeechError('');
    setVoiceNote('Listening...');

    const recognition = new speechRecognitionCtor();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => {
      setIsListening(false);
      setVoiceNote('');
    };
    recognition.onerror = (event) => {
      setSpeechError(`Speech input error: ${event.error || 'unknown'}`);
      setIsListening(false);
      setVoiceNote('');
    };
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim() || '';
      if (!transcript) return;
      setAiInput(transcript);
      askAI(transcript);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }

  function stopVoiceInput() {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  }

  function stopAudioPlayback() {
    const activeAudio = currentAudioRef.current;
    if (activeAudio) {
      activeAudio.pause();
      activeAudio.currentTime = 0;
      activeAudio.onended = null;
      activeAudio.onerror = null;
    }
    if (currentAudioUrlRef.current) {
      URL.revokeObjectURL(currentAudioUrlRef.current);
    }
    currentAudioRef.current = null;
    currentAudioUrlRef.current = null;
    setIsSpeaking(false);
  }

  async function playTtsText(rawText, { showDisabledError = false } = {}) {
    const clean = stripSpeechSymbols(rawText || '');
    if (!clean) {
      return false;
    }
    if (!aiVoiceOutputEnabled) {
      if (showDisabledError) {
        setSpeechError('Voice output is disabled in AI settings.');
      }
      return false;
    }

    stopAudioPlayback();
    setSpeechError('');

    try {
      const resp = await fetch(`${apiBase}/tts/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: clean }),
      });
      if (!resp.ok) {
        throw new Error('tts_unavailable');
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      currentAudioUrlRef.current = url;
      currentAudioRef.current = audio;
      setIsSpeaking(true);

      audio.onended = () => {
        if (currentAudioUrlRef.current) {
          URL.revokeObjectURL(currentAudioUrlRef.current);
        }
        currentAudioRef.current = null;
        currentAudioUrlRef.current = null;
        setIsSpeaking(false);
      };
      audio.onerror = () => {
        stopAudioPlayback();
      };

      await audio.play();
      return true;
    } catch {
      stopAudioPlayback();
      setSpeechError('Christy voice unavailable. Check backend TTS service.');
      return false;
    }
  }

  function stopSpeakingNow() {
    stopAudioPlayback();
  }

  function stripSpeechSymbols(text) {
    return text
      .replace(/\[CONFIRM_ACTION:[^\]]+\]/g, '')
      .replace(/\*{1,3}([^*]*)\*{1,3}/g, '$1')
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/^\s*[-*+•]\s+/gm, '')
      .replace(/^\s*\d+\.\s+/gm, '')
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/[*#_~`^|<>{}\\]/g, '')
      .replace(/\n{2,}/g, '. ')
        .replace(/\n/g, '. ')
      .replace(/\s{2,}/g, ' ')
      .trim();
  }

  async function speakLatestAssistantMessage() {
    const latestAssistant = [...aiMessages].reverse().find((msg) => msg.role === 'assistant' && msg.text);
    if (!latestAssistant) {
      setSpeechError('No assistant response available to speak.');
      return;
    }
    await playTtsText(latestAssistant.text, { showDisabledError: true });
  }

  async function speakAnnouncementText() {
    if (!stripSpeechSymbols(announcementText || '')) {
      setSpeechError('Type a message first, then click Announce Aloud.');
      return;
    }
    await playTtsText(announcementText, { showDisabledError: true });
  }

  async function fetchActiveTheme() {
    try {
      const response = await fetch(`${apiBase}/custom/themes/active`);
      if (!response.ok) {
        return;
      }
      const theme = await response.json();
      setCurrentTheme(theme);
      applyThemeToDOM(theme);
    } catch (err) {
      console.warn('Failed to load active theme:', err);
    }
  }

  async function fetchAnnouncementRules() {
    const res = await fetch(`${apiBase}/announcement-rules`);
    if (res.ok) setAnnouncementRules(await res.json());
  }

  async function saveAnnouncementRule() {
    if (!ruleForm.name.trim() || !ruleForm.message_template.trim()) return;
    const path = editingRuleId
      ? `${apiBase}/announcement-rules/${editingRuleId}`
      : `${apiBase}/announcement-rules`;
    const method = editingRuleId ? 'PUT' : 'POST';
    const res = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...ruleForm,
        trigger_minutes_before: Number(ruleForm.trigger_minutes_before) || 15,
      }),
    });
    if (!res.ok) return;
    setEditingRuleId(null);
    setRuleForm({ name: '', enabled: true, trigger_activity_types: '', trigger_minutes_before: 15, message_template: '' });
    fetchAnnouncementRules();
  }

  async function toggleAnnouncementRule(rule) {
    await fetch(`${apiBase}/announcement-rules/${rule.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...rule, enabled: !rule.enabled }),
    });
    fetchAnnouncementRules();
  }

  async function deleteAnnouncementRule(id) {
    await fetch(`${apiBase}/announcement-rules/${id}`, { method: 'DELETE' });
    if (editingRuleId === id) {
      setEditingRuleId(null);
      setRuleForm({ name: '', enabled: true, trigger_activity_types: '', trigger_minutes_before: 15, message_template: '' });
    }
    fetchAnnouncementRules();
  }

  function startEditRule(rule) {
    setEditingRuleId(rule.id);
    setRuleForm({
      name: rule.name,
      enabled: rule.enabled,
      trigger_activity_types: rule.trigger_activity_types,
      trigger_minutes_before: rule.trigger_minutes_before,
      message_template: rule.message_template,
    });
  }

  async function fetchScheduleData() {
    const [itemsRes, overviewRes] = await Promise.all([
      fetch(`${apiBase}/schedule/items`),
      fetch(`${apiBase}/schedule/overview`),
    ]);

    if (itemsRes.ok) {
      const payload = await itemsRes.json();
      setScheduleItems(payload);
    }

    if (overviewRes.ok) {
      const payload = await overviewRes.json();
      setScheduleOverview(payload);
    }
  }

  async function fetchResultsData() {
    const [historyRes, summaryRes] = await Promise.all([
      fetch(`${apiBase}/results/history`),
      fetch(`${apiBase}/results/summary`),
    ]);

    if (historyRes.ok) {
      const payload = await historyRes.json();
      setResultsHistory(payload);
    }

    if (summaryRes.ok) {
      const payload = await summaryRes.json();
      setResultsSummary(payload);
    }
  }

  async function fetchPropsData() {
    const response = await fetch(`${apiBase}/props`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setPropsList(normalizeFirmwareProps(payload));
  }

  async function fetchSystemLogs(filters = logFilters) {
    const params = new URLSearchParams();
    if (filters.level !== 'ALL') {
      params.set('level', filters.level);
    }
    if (filters.category !== 'ALL') {
      params.set('category', filters.category);
    }
    const query = params.toString();
    const response = await fetch(`${apiBase}/logs${query ? `?${query}` : ''}`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setSystemLogs(payload);
  }

  async function fetchSystemStatus() {
    const response = await fetch(`${apiBase}/system/status`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setSystemStatus(payload);
  }

  async function fetchUpdateCenterStatus() {
    const response = await fetch(`${apiBase}/update-center/status`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setUpdateCenterStatus(payload);
  }

  async function fetchFirmwarePackages() {
    const response = await fetch(`${apiBase}/update-center/firmware-packages`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setFirmwarePackages(payload);
    if (!selectedFirmwarePackageId && payload.length > 0) {
      setSelectedFirmwarePackageId(payload[0].id);
    }
  }

  async function fetchFirmwareRollouts() {
    const response = await fetch(`${apiBase}/update-center/firmware-rollouts`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setFirmwareRollouts(payload);
  }

  async function runUpdateCenterAction(path, body) {
    const response = await fetch(`${apiBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      setUpdateMessage('Update Center action failed.');
      return;
    }
    const payload = await response.json();
    setUpdateMessage(payload.message);
    fetchUpdateCenterStatus();
  }

  async function uploadFirmwarePackage() {
    if (!selectedUpdatePackage) {
      setUpdateMessage('Select a firmware file first.');
      return;
    }
    if (!firmwareVersion.trim()) {
      setUpdateMessage('Enter a firmware version before upload.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedUpdatePackage);
    formData.append('version', firmwareVersion.trim());
    formData.append('notes', firmwareNotes.trim());

    const response = await fetch(`${apiBase}/update-center/firmware-upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      setUpdateMessage('Firmware upload failed.');
      return;
    }

    const payload = await response.json();
    setUpdateMessage(`Firmware package uploaded: ${payload.filename} (${payload.version})`);
    setSelectedFirmwarePackageId(payload.id);
    fetchFirmwarePackages();
    fetchFirmwareRollouts();
    fetchUpdateCenterStatus();
  }

  async function applyFirmwarePackage() {
    if (!selectedFirmwarePackageId) {
      setUpdateMessage('Select a firmware package to apply.');
      return;
    }

    const response = await fetch(`${apiBase}/update-center/firmware-apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        package_id: selectedFirmwarePackageId,
        prop_ids: selectedFirmwarePropIds,
        apply_all: selectedFirmwarePropIds.length === 0,
      }),
    });

    if (!response.ok) {
      setUpdateMessage('Firmware apply failed.');
      return;
    }

    const payload = await response.json();
    setUpdateMessage(payload.message);
    fetchPropsData();
    fetchFirmwareRollouts();
    fetchUpdateCenterStatus();
  }

  function toggleFirmwareTargetProp(propId) {
    setSelectedFirmwarePropIds((current) => {
      if (current.includes(propId)) {
        return current.filter((id) => id !== propId);
      }
      return [...current, propId];
    });
  }

  // Ensure a conversation exists and return its id.
  async function ensureAiConversation() {
    if (aiConversationId) return aiConversationId;
    try {
      const res = await fetch(`${apiBase}/ai/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Field Advisor Session' }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      setAiConversationId(data.id);
      return data.id;
    } catch {
      return null;
    }
  }

  async function askAI(prompt) {
    const cleanedPrompt = prompt.trim();
    if (!cleanedPrompt || aiTyping) return;

    setAiMessages((current) => [...current, { role: 'user', text: cleanedPrompt }]);
    setAiTyping(true);

    try {
      const convId = await ensureAiConversation();
      if (!convId) throw new Error('no_conversation');

      const response = await fetch(`${apiBase}/ai/conversations/${convId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: cleanedPrompt }),
      });

      if (!response.ok) throw new Error('api_error');

      const payload = await response.json();
      // Strip the internal [CONFIRM_ACTION:...] tag from displayed text.
      const displayText = payload.answer.replace(/\[CONFIRM_ACTION:[^\]]+\]/g, '').trim();
      if (displayText) {
        setAiMessages((current) => [
          ...current,
          {
            role: 'assistant',
            text: displayText,
            awaiting_confirm: payload.requires_admin_confirmation && payload.blocked_actions.length === 0,
          },
        ]);
      }
      if (displayText) {
        await playTtsText(displayText);
      }
    } catch {
      setAiMessages((current) => [
        ...current,
        { role: 'assistant', text: 'AI route unavailable. Check backend connectivity.', meta: 'error' },
      ]);
    } finally {
      setAiTyping(false);
    }
  }

  function clearAiConversation() {
    stopAudioPlayback();
    setAiMessages([]);
    setAiConversationId(null);
  }

  async function clearSystemLogs() {
    const response = await fetch(`${apiBase}/logs`, { method: 'DELETE' });
    if (!response.ok) {
      return;
    }
    fetchSystemLogs();
  }

  function exportSystemLogsCsv() {
    const params = new URLSearchParams();
    if (logFilters.level !== 'ALL') {
      params.set('level', logFilters.level);
    }
    if (logFilters.category !== 'ALL') {
      params.set('category', logFilters.category);
    }
    const query = params.toString();
    window.open(`${apiBase}/logs/export/csv${query ? `?${query}` : ''}`, '_blank');
  }

  async function saveProp() {
    setPropSaveError('');
    if (!propForm.device_id.trim() || !propForm.name.trim()) {
      setPropSaveError('Device ID and Name are required.');
      return;
    }

    const body = { ...propForm };
    // Backend requires auth_token to be null (not empty string) when not set
    if (!body.auth_token) body.auth_token = null;

    const path = editingPropId ? `${apiBase}/props/${editingPropId}` : `${apiBase}/props`;
    const method = editingPropId ? 'PUT' : 'POST';
    const response = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      let msg = `Save failed (${response.status})`;
      try {
        const err = await response.json();
        if (err.detail) msg = typeof err.detail === 'string' ? err.detail : (err.detail.message || msg);
      } catch {}
      setPropSaveError(msg);
      return;
    }

    setEditingPropId(null);
    setPropForm({
      device_id: '',
      name: '',
      prop_type: 'Custom',
      location: '',
      firmware_version: '',
      auth_token: '',
    });
    fetchPropsData();
  }

  function startEditProp(item) {
    setEditingPropId(item.id);
    setPropForm({
      device_id: item.device_id,
      name: item.name,
      prop_type: item.prop_type,
      location: item.location,
      firmware_version: item.firmware_version,
      auth_token: '',
    });
  }

  async function rotatePropToken(id) {
    const response = await fetch(`${apiBase}/props/${id}/token/rotate`, {
      method: 'POST',
    });
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setIssuedPropTokens((current) => ({
      ...current,
      [id]: payload.token,
    }));
  }

  async function copyToken(token) {
    try {
      await navigator.clipboard.writeText(token);
    } catch {
      // no-op fallback for restricted clipboard contexts
    }
  }

  async function deleteProp(id) {
    const response = await fetch(`${apiBase}/props/${id}`, { method: 'DELETE' });
    if (!response.ok) {
      return;
    }
    if (editingPropId === id) {
      setEditingPropId(null);
    }
    fetchPropsData();
  }

  async function sendPropCommand(id, command) {
    const response = await fetch(`${apiBase}/props/${id}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    });
    if (!response.ok) {
      return;
    }
    fetchPropsData();
  }

  function exportResultsCsv() {
    window.open(`${apiBase}/results/export/csv`, '_blank');
  }

  async function saveScheduleItem() {
    setScheduleSaveError('');
    if (!scheduleForm.start_time || !scheduleForm.title.trim()) {
      setScheduleSaveError('Title and start time are required.');
      return;
    }

    const startIso = toTodayIsoFromTime(scheduleForm.start_time);
    if (!startIso) {
      return;
    }

    const body = {
      title: scheduleForm.title,
      details: scheduleForm.details,
      activity_type: scheduleForm.activity_type,
      game_mode: scheduleForm.activity_type === 'Game' ? scheduleForm.game_mode : '',
      props_needed: scheduleForm.activity_type === 'Game' ? (scheduleForm.props_needed || []) : [],
      start_time: startIso,
      end_time: null,
      is_complete: scheduleForm.is_complete,
    };

    const path = editingScheduleId
      ? `${apiBase}/schedule/items/${editingScheduleId}`
      : `${apiBase}/schedule/items`;
    const method = editingScheduleId ? 'PUT' : 'POST';

    let response = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    // Compatibility fallback: older backend still requires end_time and lacks newer activity types.
    if (!response.ok && response.status === 422) {
      const compatBody = {
        ...body,
        end_time: addMinutesLocal(startIso, 30),
        activity_type: ['Pickup', 'Drop Off'].includes(body.activity_type) ? 'Custom' : body.activity_type,
      };
      response = await fetch(path, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(compatBody),
      });
    }

    if (!response.ok) {
      let msg = `Schedule save failed (${response.status})`;
      try {
        const err = await response.json();
        if (err.detail) {
          msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
        }
      } catch {}
      setScheduleSaveError(msg);
      return;
    }

    setEditingScheduleId(null);
    setScheduleForm({
      title: '',
      details: '',
      activity_type: 'Custom',
      game_mode: '',
      props_needed: [],
      start_time: '',
      is_complete: false,
    });
    fetchScheduleData();
  }

  async function deleteScheduleItem(itemId) {
    const response = await fetch(`${apiBase}/schedule/items/${itemId}`, { method: 'DELETE' });
    if (!response.ok) {
      return;
    }
    if (editingScheduleId === itemId) {
      setEditingScheduleId(null);
    }
    fetchScheduleData();
  }

  async function completeScheduleItem(itemId) {
    const response = await fetch(`${apiBase}/schedule/items/${itemId}/complete`, { method: 'POST' });
    if (!response.ok) {
      return;
    }
    fetchScheduleData();
  }

  function editScheduleItem(item) {
    setEditingScheduleId(item.id);
    setScheduleForm({
      title: item.title,
      details: item.details,
      activity_type: item.activity_type,
      game_mode: item.game_mode || '',
      props_needed: item.props_needed || [],
      start_time: toTimeInputValue(item.start_time),
      is_complete: item.is_complete,
    });
  }

  async function quickRecordResult(item) {
    const body = {
      session_name: item.title,
      winner: quickResultForm.winner,
      red_points: Number(quickResultForm.red_points),
      blue_points: Number(quickResultForm.blue_points),
      notes: quickResultForm.notes,
      schedule_item_id: item.id,
    };
    const response = await fetch(`${apiBase}/results`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (response.ok) {
      setRecordingResultForItemId(null);
      setQuickResultForm({ winner: 'Draw', red_points: 0, blue_points: 0, notes: '' });
      fetchResultsData();
    }
  }

  async function resetTodayResults() {
    const today = new Date().toLocaleDateString('en-CA');
    const ok = window.confirm(`Reset all saved results for ${today}? This cannot be undone.`);
    if (!ok) return;

    const response = await fetch(`${apiBase}/results/reset-day`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ day: today }),
    });
    if (response.ok) {
      fetchResultsData();
    }
  }

  async function saveMissionAsPreset() {
    setPresetSaveStatus('Saving...');
    const body = {
      name: missionForm.title,
      description: missionForm.description || '',
      default_duration_minutes: Number(missionForm.main_timer_minutes) || 30,
      objectives_json: (missionForm.objectivesText || '')
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      required_props_json: missionForm.props_needed || [],
      active: true,
    };
    const response = await fetch(`${apiBase}/custom/game-modes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (response.ok) {
      setPresetSaveStatus('Preset saved!');
      fetchGameModeOptions();
      setTimeout(() => setPresetSaveStatus(''), 3000);
    } else {
      setPresetSaveStatus('Save failed.');
      setTimeout(() => setPresetSaveStatus(''), 3000);
    }
  }

  useEffect(() => {
    const timer = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // Load active theme on app startup
    fetchActiveTheme();
    
    // Refresh theme every 30 seconds in case it was changed in admin panel
    const themeInterval = setInterval(fetchActiveTheme, 30000);
    return () => clearInterval(themeInterval);
  }, [apiBase]);

  useEffect(() => {
    if (aiChatEndRef.current) {
      aiChatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [aiMessages, aiTyping]);

  useEffect(() => {
    fetchMissionState();
    fetchGameModeOptions();
    fetchCustomTeams();
    fetchScheduleData();
    fetchResultsData();
    fetchPropsData();
    fetchSystemLogs();
    fetchSystemStatus();
    fetchUpdateCenterStatus();
    fetchFirmwarePackages();
    fetchFirmwareRollouts();
    fetchAiSettings();
    fetchAnnouncementRules();
  }, [apiBase]);

  useEffect(() => {
    if (selectedApp === 'mission-control') {
      fetchGameModeOptions();
      fetchCustomTeams();
    }
  }, [selectedApp, apiBase]);

  useEffect(() => {
    const handleCustomDataChanged = () => {
      fetchGameModeOptions();
      fetchCustomTeams();
      fetchActiveTheme();
      fetchAiSettings();
    };

    window.addEventListener('custom-data-changed', handleCustomDataChanged);
    return () => {
      window.removeEventListener('custom-data-changed', handleCustomDataChanged);
    };
  }, [apiBase]);

  useEffect(() => {
    if (!aiVoiceOutputEnabled && isSpeaking) {
      stopAudioPlayback();
    }
    if (!aiVoiceInputEnabled && isListening) {
      stopVoiceInput();
    }
  }, [aiVoiceOutputEnabled, aiVoiceInputEnabled, isSpeaking, isListening]);

  useEffect(() => {
    return () => {
      stopAudioPlayback();
      stopVoiceInput();
    };
  }, []);

  useEffect(() => {
    const intervalId = setInterval(() => {
      fetchSystemStatus();
    }, 5000);
    return () => clearInterval(intervalId);
  }, [apiBase]);

  useEffect(() => {
    fetchSystemLogs(logFilters);
  }, [logFilters]);

  useEffect(() => {
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => setNetworkStatus('ONLINE');
    socket.onclose = () => setNetworkStatus('OFFLINE');
    socket.onerror = () => setNetworkStatus('ERROR');
    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data);
        if (data.event === 'mission_control.state' && data.payload) {
          setMissionState(data.payload);
          setEvents(data.payload.event_feed ?? []);
          return;
        }
        if (data.event === 'prop.status_report' && data.payload?.device_id) {
          setPropsList((current) => current.map((item) => {
            if (item.device_id !== data.payload.device_id) {
              return item;
            }
            return {
              ...item,
              status: data.payload.status ?? item.status,
              battery_level: Number.isFinite(data.payload.battery_level)
                ? data.payload.battery_level
                : item.battery_level,
              signal_strength: Number.isFinite(data.payload.signal_strength)
                ? data.payload.signal_strength
                : item.signal_strength,
              last_seen: data.payload.last_status_report || item.last_seen,
            };
          }));
        }
        // Team ready / countdown events
        if (data.event === 'game.team_ready' && data.payload?.ready_state) {
          setTeamReadyState(data.payload.ready_state);
          return;
        }
        if (data.event === 'game.countdown' && data.payload != null) {
          setCountdown(data.payload.seconds_remaining);
          if (data.payload.seconds_remaining === 0) {
            setTimeout(() => setCountdown(null), 1500);
          }
          return;
        }
        if (data.event === 'game.ready_reset') {
          setTeamReadyState({ red: false, blue: false });
          setCountdown(null);
          return;
        }
        // Christy proactive announcements
        if (data.event === 'christy.announcement' && data.payload?.content) {
          if (data.payload?.type === 'mode_suggestion') {
            return;
          }
          const announcementText = data.payload.content;
          setAiMessages((current) => [
            ...current,
            { role: 'assistant', text: announcementText, meta: 'announcement' },
          ]);
          playTtsText(announcementText).catch(() => {});
          return;
        }
        const line = `${formatFeedTime()} :: ${JSON.stringify(data)}`;
        // Only show game/mission/warning/error events in the live feed
        const eventStr = (data.event || '').toLowerCase();
        const isImportant = eventStr.includes('mission') || eventStr.includes('game') || eventStr.includes('score')
          || eventStr.includes('warn') || eventStr.includes('error') || eventStr.includes('alarm')
          || eventStr.includes('start') || eventStr.includes('end') || eventStr.includes('result');
        if (isImportant) {
          setEvents((previous) => [line, ...previous].slice(0, 20));
        }
      } catch {
        const line = `${formatFeedTime()} :: ${message.data}`;
        const isImportant = /warn|error|alarm|mission|game|score|result/i.test(line);
        if (isImportant) {
          setEvents((previous) => [line, ...previous].slice(0, 20));
        }
      }
    };

    return () => socket.close();
  }, [wsUrl, apiBase, aiVoiceOutputEnabled]);

  const activeApp = APPS.find((app) => app.id === selectedApp) ?? APPS[0];
  const isOverview = activeApp.id === 'overview';

  const isMissionControl = activeApp.id === 'mission-control';
  const isSchedule = activeApp.id === 'schedule';
  const isPropNetwork = activeApp.id === 'prop-network';
  const isLogs = activeApp.id === 'logs';
  const isSystemMonitor = activeApp.id === 'system-monitor';
  const isAIAssistant = activeApp.id === 'ai-assistant';
  const isUpdateCenter = activeApp.id === 'update-center';
  const isSettings = activeApp.id === 'settings';
  const showLiveFeed = Boolean(uiPrefs.showLiveFeed);

  const gameModeByName = useMemo(() => {
    const rows = customGameModes.filter((mode) => mode && typeof mode.name === 'string');
    return Object.fromEntries(rows.map((mode) => [mode.name, mode]));
  }, [customGameModes]);

  const propNameOptions = useMemo(() => {
    return Array.from(new Set(propsList.map((item) => item.name).filter(Boolean))).sort((a, b) => a.localeCompare(b));
  }, [propsList]);

  function getDefaultPropsForGameMode(modeName) {
    const mode = gameModeByName[modeName];
    if (!mode || !Array.isArray(mode.required_props_json)) {
      return [];
    }
    return mode.required_props_json.filter(Boolean);
  }

  function buildDefaultPropSettings(propNames, mainMinutes, phaseMinutes) {
    return Object.fromEntries(
      (propNames || []).map((name) => [
        name,
        {
          enabled: true,
          game_time_seconds: Math.max(0, Number(mainMinutes) || 0) * 60,
          phase_time_seconds: Math.max(0, Number(phaseMinutes) || 0) * 60,
          notes: '',
        },
      ])
    );
  }

  const todayScheduleItems = useMemo(() => {
    const today = new Date().toDateString();
    const todays = scheduleItems.filter((item) => {
      if (!item.start_time) {
        return false;
      }
      return new Date(item.start_time).toDateString() === today;
    });
    return todays.length > 0 ? todays : scheduleItems.slice(0, 6);
  }, [scheduleItems]);

  const alertCount = useMemo(() => {
    if (typeof systemStatus.alert_count === 'number') {
      return systemStatus.alert_count;
    }
    return systemLogs.filter((log) => ['WARNING', 'ERROR', 'CRITICAL'].includes((log.level || '').toUpperCase())).length;
  }, [systemStatus.alert_count, systemLogs]);

  const connectedDeviceCount = useMemo(() => {
    if (typeof systemStatus.prop_count === 'number' && systemStatus.prop_count > 0) {
      return systemStatus.prop_count;
    }
    return propsList.length;
  }, [systemStatus.prop_count, propsList]);

  const plannedGames = useMemo(() => {
    return todayScheduleItems
      .filter((item) => item.activity_type === 'Game')
      .map((item) => ({
        key: `schedule-${item.id}`,
        name: item.game_mode || item.title,
        requiredProps: (item.props_needed && item.props_needed.length > 0)
          ? item.props_needed
          : getDefaultPropsForGameMode(item.game_mode || item.title),
      }))
      .filter((g) => g.name)
      .slice(0, 6);
  }, [todayScheduleItems, gameModeByName]);

  const usedPropsToday = useMemo(() => {
    // Always include CP_Unit_TF, CP_Unit_BF, and GM_Unit when present.
    const alwaysOn = propsList.filter((item) => ALWAYS_INCLUDED_PROP_NAMES.has(item.name));

    // Collect props from schedule items (if they have props_needed field) and planned games
    const plannedNeedles = todayScheduleItems
      .filter((item) => item.activity_type === 'Game')
      .flatMap((item) => {
        const scheduled = item.props_needed || [];
        const game = plannedGames.find((g) => g.name === (item.game_mode || item.title));
        const gameDef = game ? (game.requiredProps || []) : [];
        return [...scheduled, ...gameDef];
      })
      .map((value) => String(value).toLowerCase());

    // Combine always-on CP units with any game-assigned props.
    let result = [...alwaysOn];

    if (plannedNeedles.length > 0) {
      const assigned = propsList.filter((item) => {
        const hay = `${item.name} ${item.device_id} ${item.prop_type}`.toLowerCase();
        return plannedNeedles.some((needle) => hay.includes(needle)) && !alwaysOn.some((fixed) => fixed.id === item.id);
      });
      result = [...result, ...assigned];
    }

    // If we have game-assigned props or CP units, use those; otherwise show available firmware props.
    if (result.length > 0) {
      return result.slice(0, 12);
    }

    return propsList.slice(0, 12);
  }, [propsList, plannedGames, todayScheduleItems]);

  const todayResultsPoints = useMemo(() => {
    const todayStr = new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD local
    const todayResults = resultsHistory.filter((r) => {
      if (!r.created_at) return false;
      // created_at may be UTC ISO or naive local — extract the date part directly
      const datePart = String(r.created_at).slice(0, 10); // "YYYY-MM-DD"
      return datePart === todayStr;
    });
    const redPoints = todayResults.reduce((sum, r) => sum + (Number(r.red_points) || 0), 0);
    const bluePoints = todayResults.reduce((sum, r) => sum + (Number(r.blue_points) || 0), 0);
    const redWins = todayResults.filter((r) => r.winner === 'Red').length;
    const blueWins = todayResults.filter((r) => r.winner === 'Blue').length;
    return { redPoints, bluePoints, redWins, blueWins, gamesPlayed: todayResults.length };
  }, [resultsHistory]);

  const teamOverviewRows = useMemo(() => {
    const missionInProgress = missionState.state === 'running' || missionState.state === 'paused';
    return customTeams.slice(0, 6).map((team, index) => {
      let liveScore = 0;
      let dayPoints = 0;
      let dayWins = 0;
      if (index === 0) {
        liveScore = missionState.red_team_score;
        dayPoints = todayResultsPoints.redPoints;
        dayWins = todayResultsPoints.redWins;
      } else if (index === 1) {
        liveScore = missionState.blue_team_score;
        dayPoints = todayResultsPoints.bluePoints;
        dayWins = todayResultsPoints.blueWins;
      }
      const showLive = missionInProgress && index < 2;
      const status = missionState.state === 'running' && index < 2 ? 'Engaged' : 'Ready';
      return {
        ...team,
        score: liveScore,
        displayPoints: dayPoints + (showLive ? liveScore : 0),
        showLive,
        dayPoints,
        dayWins,
        status,
        logoUrl: resolveTeamLogoUrl(team.icon),
      };
    });
  }, [customTeams, missionState.red_team_score, missionState.blue_team_score, missionState.state, todayResultsPoints, apiOrigin]);

  useEffect(() => {
    const total = Math.max(1, connectedDeviceCount);
    const online = typeof systemStatus.online_prop_count === 'number'
      ? systemStatus.online_prop_count
      : propsList.filter((p) => ['online', 'armed', 'disarmed', 'alarm'].includes((p.status || '').toLowerCase())).length;
    const ratio = Math.round((online / total) * 100);

    setDeviceHealthTrend((current) => [...current.slice(-19), ratio]);
  }, [systemStatus.online_prop_count, connectedDeviceCount, propsList]);

  useEffect(() => {
    const spread = Number(missionState.red_team_score || 0) - Number(missionState.blue_team_score || 0);
    setScoreTrend((current) => [...current.slice(-19), spread]);
  }, [missionState.red_team_score, missionState.blue_team_score]);

  function handleCreateMission() {
    const objectives = missionForm.objectivesText
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);

    const selectedProps = (missionForm.props_needed || []).filter(Boolean);
    const propSettings = Object.fromEntries(
      selectedProps.map((name) => [name, {
        ...(missionForm.prop_settings?.[name] || {}),
        enabled: missionForm.prop_settings?.[name]?.enabled !== false,
      }])
    );

    postMissionAction('/mission-control/mission', {
      title: missionForm.title,
      description: missionForm.description,
      game_mode: missionForm.game_mode,
      main_timer_seconds: Number(missionForm.main_timer_minutes) * 60,
      phase_timer_seconds: Number(missionForm.phase_timer_minutes) * 60,
      objectives,
      props_needed: selectedProps,
      prop_settings: propSettings,
    });
  }

  function buildNextAgendaAnnouncement() {
    const nextItem = scheduleOverview.next_activity;
    if (!nextItem) {
      return '';
    }
    const start = nextItem.start_time
      ? militaryTime(nextItem.start_time)
      : 'soon';
    return `Next on the agenda is ${nextItem.title}, which should start from ${start}.`;
  }

  async function announceNextAgendaNow() {
    const text = buildNextAgendaAnnouncement();
    if (!text) {
      setSpeechError('No next agenda item found.');
      return;
    }
    setAnnouncementText(text);
    await playTtsText(text, { showDisabledError: true });
  }

  function askAiForNextAgendaBrief() {
    const nextItem = scheduleOverview.next_activity;
    if (!nextItem) {
      setAiInput('Create a short agenda brief for the next activity.');
      return;
    }
    const start = nextItem.start_time
      ? militaryTime(nextItem.start_time)
      : 'soon';
    setAiInput(`Draft a short marshal brief for next on the agenda: ${nextItem.title} at ${start}.`);
  }

  return (
    <div className="desktop-shell">
      <header className="top-bar desktop-panel">
        <div className="brand-block">
          <button type="button" className="brand-mark desktop-activities" onClick={() => openDesktopWindow('overview')}>
            Activities
          </button>
          <div>
            <h1>Command OS</h1>
            <p>AOJ Tactical Field Console</p>
          </div>
        </div>

        <div className="status-cluster">
          <div className={`indicator net-${networkStatus.toLowerCase()}`}>
            Network {networkStatus}
          </div>
          <button type="button" className="indicator" onClick={() => openDesktopWindow('logs')}>
            Alerts {alertCount}
          </button>
          <button type="button" className="indicator" onClick={() => openDesktopWindow('prop-network')}>
            Devices {connectedDeviceCount}
          </button>
          <div className="clock">{militaryTime(clock)}</div>
        </div>
      </header>

      <main className="desktop-grid linux-desktop-grid">
        <aside className="desktop-dock" aria-label="Application Dock">
          {APPS.map((app) => (
            <button
              key={`dock-${app.id}`}
              type="button"
              className={`dock-item${selectedApp === app.id ? ' active' : ''}`}
              onClick={() => {
                setSelectedApp(app.id);
                openDesktopWindow(app.id);
              }}
              title={app.title}
            >
              <span className="dock-item-glyph">{app.badge}</span>
              <span className="dock-item-label">{app.title}</span>
            </button>
          ))}
        </aside>

        <section className={`window-stack${showLiveFeed ? ' with-feed' : ''}`}>
          {windowOpen && !windowMinimized ? (
            <article className="window primary-window">
              <div className="window-content">
              {isOverview ? (
                <section className="overview-module">
                  <div className="overview-grid">
                    <div className="overview-card overview-hero">
                      <h3>Operations Snapshot</h3>
                      <div className="overview-hero-row">
                        <div>
                          <p className="overview-kicker">Mission</p>
                          <strong>{missionState.mission_title}</strong>
                        </div>
                        <div>
                          <p className="overview-kicker">Mode</p>
                          <strong>{missionState.game_mode}</strong>
                        </div>
                        <div>
                          <p className="overview-kicker">State</p>
                          <strong>{missionState.state.toUpperCase()}</strong>
                        </div>
                      </div>
                      <div className="overview-score-strip">
                        <div className="overview-score-pill red">{redTeamLabel}: {missionState.red_team_score}</div>
                        <div className="overview-score-pill blue">{blueTeamLabel}: {missionState.blue_team_score}</div>
                        <div className="overview-score-pill neutral">Main {formatDuration(missionState.main_timer_seconds)}</div>
                        <div className="overview-score-pill neutral">Phase {formatDuration(missionState.phase_timer_seconds)}</div>
                      </div>
                    </div>

                    <div className="overview-card">
                      <h3>Schedule Today</h3>
                      {todayScheduleItems.length === 0 ? <p className="muted">No schedule items yet.</p> : null}
                      {todayScheduleItems.slice(0, 6).map((item) => (
                        <div className="overview-row" key={item.id}>
                          <strong>{item.title}</strong>
                          <span>{item.start_time ? militaryTime(item.start_time) : 'TBD'}</span>
                        </div>
                      ))}
                    </div>

                    <div className="overview-card">
                      <h3>Planned Games</h3>
                      {plannedGames.length === 0 ? <p className="muted">No planned games detected.</p> : null}
                      {plannedGames.map((game) => (
                        <div className="overview-row" key={game.key}>
                          <strong>{game.name}</strong>
                          <span>
                            {(game.requiredProps || []).length > 0
                              ? `Needs: ${game.requiredProps.slice(0, 2).join(', ')}`
                              : 'Planned'}
                          </span>
                        </div>
                      ))}
                    </div>

                    <div className="overview-card">
                      <h3>Props In Use Today</h3>
                      {usedPropsToday.length === 0 ? <p className="muted">No props registered.</p> : null}
                      {usedPropsToday.map((item) => (
                        <div className="overview-row" key={item.id}>
                          <strong>{item.name}</strong>
                          <span>{item.status}</span>
                        </div>
                      ))}
                    </div>

                    <div className="overview-card overview-team-card">
                      <h3>Team Standing — Today</h3>
                      {teamOverviewRows.length === 0 ? <p className="muted">No active teams configured.</p> : null}
                      {(() => {
                        const maxDay = Math.max(...teamOverviewRows.map((t) => Number(t.displayPoints || 0)));
                        return teamOverviewRows.map((team) => {
                          const isLeader = Number(team.displayPoints || 0) > 0 && Number(team.displayPoints || 0) === maxDay;
                          return (
                            <div className="overview-team-row" key={team.id}>
                              <div className="overview-team-left">
                                {team.logoUrl ? (
                                  <img className="overview-team-logo" src={team.logoUrl} alt={`${team.name} logo`} />
                                ) : (
                                  <span className="overview-team-color" style={{ backgroundColor: team.color }} />
                                )}
                                <div>
                                  <strong>{team.name} {isLeader ? '🏆' : ''}</strong>
                                  <p>{team.status}</p>
                                </div>
                              </div>
                              <div className="overview-team-score">
                                <span style={{ fontSize: '1.1rem' }}>{team.displayPoints} pts</span>
                                <span style={{ fontSize: '0.75rem', opacity: 0.65, marginLeft: '0.4rem' }}>{team.dayWins}W</span>
                                {team.showLive ? (
                                  <span style={{ fontSize: '0.75rem', opacity: 0.5, marginLeft: '0.3rem' }}>(today: {team.dayPoints})</span>
                                ) : null}
                              </div>
                            </div>
                          );
                        });
                      })()}
                      {(() => {
                        const gamesLeft = todayScheduleItems.filter((i) => i.activity_type === 'Game').length - todayResultsPoints.gamesPlayed;
                        const diff = Math.abs(todayResultsPoints.redPoints - todayResultsPoints.bluePoints);
                        const isImbalanced = gamesLeft > 0 && diff >= 20 && todayResultsPoints.gamesPlayed > 0;
                        if (!isImbalanced) return null;
                        const leadingTeam = todayResultsPoints.redPoints > todayResultsPoints.bluePoints ? redTeamLabel : blueTeamLabel;
                        const trailingTeam = todayResultsPoints.redPoints > todayResultsPoints.bluePoints ? blueTeamLabel : redTeamLabel;
                        return (
                          <button
                            type="button"
                            className="ai-suggest-btn"
                            onClick={() => {
                              setSelectedApp('ai-assistant');
                              setAiInput(`${leadingTeam} leads by ${diff} points with ${gamesLeft} games remaining today. Suggest realistic handicap adjustments or game format tweaks to balance the remaining games and keep it competitive for ${trailingTeam}.`);
                            }}
                            style={{ marginTop: '0.6rem', width: '100%', fontSize: '0.82rem' }}
                          >
                            ⚖️ AI: Suggest balance for remaining {gamesLeft} game{gamesLeft !== 1 ? 's' : ''}
                          </button>
                        );
                      })()}

                      <button
                        type="button"
                        className="ai-suggest-btn"
                        onClick={resetTodayResults}
                        style={{ marginTop: '0.5rem', width: '100%', fontSize: '0.8rem', opacity: 0.9 }}
                      >
                        Reset Today Points
                      </button>
                    </div>

                    <div className="overview-card overview-team-card">
                      <h3>Live Trend</h3>
                      <p className="overview-kicker">Score Spread (Red - Blue)</p>
                      <div className="trend-strip">
                        {scoreTrend.length === 0 ? <span className="muted">No score data yet.</span> : null}
                        {scoreTrend.map((point, index) => {
                          const height = Math.min(100, Math.max(15, 50 + point * 4));
                          const tone = point >= 0 ? 'var(--success-color)' : 'var(--danger-color)';
                          return (
                            <span
                              key={`score-${index}`}
                              className="trend-bar"
                              style={{ height: `${height}%`, backgroundColor: tone }}
                              title={`Spread ${point}`}
                            />
                          );
                        })}
                      </div>

                      <p className="overview-kicker" style={{ marginTop: '0.75rem' }}>Device Health (%)</p>
                      <div className="trend-strip">
                        {deviceHealthTrend.length === 0 ? <span className="muted">No device health data yet.</span> : null}
                        {deviceHealthTrend.map((point, index) => {
                          const height = Math.min(100, Math.max(12, point));
                          return (
                            <span
                              key={`device-${index}`}
                              className="trend-bar"
                              style={{ height: `${height}%`, backgroundColor: 'var(--accent-color)' }}
                              title={`Online ${point}%`}
                            />
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </section>
              ) : isMissionControl ? (
                <section className="mission-control">
                  <div className="mc-grid">
                    <div className="mc-card">
                      <h3>Today's Games</h3>
                      {todayScheduleItems.filter((i) => i.activity_type === 'Game').length === 0 ? (
                        <p className="muted">No games scheduled today. Add Game items in Schedule.</p>
                      ) : (
                        <div className="mc-game-list">
                          {todayScheduleItems.filter((i) => i.activity_type === 'Game').map((item) => (
                            <button
                              key={item.id}
                              type="button"
                              className={selectedScheduleGame && selectedScheduleGame.id === item.id ? 'mc-game-item mc-game-item-active' : 'mc-game-item'}
                              onClick={() => {
                                setSelectedScheduleGame(item);
                                const modeName = item.game_mode || missionForm.game_mode;
                                const selectedProps = (item.props_needed && item.props_needed.length > 0)
                                  ? item.props_needed
                                  : getDefaultPropsForGameMode(modeName);
                                const nextForm = {
                                  title: item.title,
                                  description: item.details || '',
                                  game_mode: modeName,
                                  main_timer_minutes: missionForm.main_timer_minutes,
                                  phase_timer_minutes: missionForm.phase_timer_minutes,
                                  objectivesText: missionForm.objectivesText,
                                  props_needed: selectedProps,
                                  prop_settings: buildDefaultPropSettings(
                                    selectedProps,
                                    missionForm.main_timer_minutes,
                                    missionForm.phase_timer_minutes
                                  ),
                                };
                                setMissionForm(nextForm);
                                // Auto-load the mission into Game Controls
                                const objectives = (nextForm.objectivesText || '')
                                  .split(',')
                                  .map((s) => s.trim())
                                  .filter(Boolean);
                                postMissionAction('/mission-control/mission', {
                                  title: nextForm.title,
                                  description: nextForm.description,
                                  game_mode: nextForm.game_mode,
                                  main_timer_seconds: Number(nextForm.main_timer_minutes) * 60,
                                  phase_timer_seconds: Number(nextForm.phase_timer_minutes) * 60,
                                  objectives,
                                  props_needed: nextForm.props_needed,
                                  prop_settings: nextForm.prop_settings,
                                });
                              }}
                            >
                              <strong>{item.title}</strong>
                              <span>{item.game_mode ? ` — ${item.game_mode}` : ''}</span>
                              <span className="schedule-meta">{item.start_time ? militaryTime(item.start_time) : 'TBD'}</span>
                            </button>
                          ))}
                        </div>
                      )}
                      <label style={{ marginTop: '0.75rem' }}>
                        Game Mode
                        <select
                          value={missionForm.game_mode}
                          onChange={(event) => {
                            const modeName = event.target.value;
                            const defaults = getDefaultPropsForGameMode(modeName);
                            setMissionForm((current) => ({
                              ...current,
                              game_mode: modeName,
                              props_needed: defaults,
                              prop_settings: buildDefaultPropSettings(
                                defaults,
                                current.main_timer_minutes,
                                current.phase_timer_minutes
                              ),
                            }));
                          }}
                        >
                          {gameModeOptions.map((mode) => (
                            <option key={mode} value={mode}>
                              {mode}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Main Timer (minutes)
                        <input
                          type="number"
                          min="1"
                          max="180"
                          value={missionForm.main_timer_minutes}
                          onChange={(event) =>
                            setMissionForm((current) => ({
                              ...current,
                              main_timer_minutes: event.target.value,
                            }))
                          }
                        />
                      </label>
                      <label>
                        Phase Timer (minutes)
                        <input
                          type="number"
                          min="1"
                          max="60"
                          value={missionForm.phase_timer_minutes}
                          onChange={(event) =>
                            setMissionForm((current) => ({
                              ...current,
                              phase_timer_minutes: event.target.value,
                            }))
                          }
                        />
                      </label>
                      <label>
                        Objectives (comma separated)
                        <textarea
                          value={missionForm.objectivesText}
                          onChange={(event) =>
                            setMissionForm((current) => ({
                              ...current,
                              objectivesText: event.target.value,
                            }))
                          }
                        />
                      </label>

                      <div style={{ marginTop: '0.6rem' }}>
                        <p className="schedule-meta" style={{ marginBottom: '0.35rem' }}>Mission Props</p>
                        {propNameOptions.length === 0 ? <p className="muted">No firmware props available.</p> : null}
                        <div style={{ display: 'grid', gap: '0.25rem', maxHeight: '10rem', overflowY: 'auto' }}>
                          {propNameOptions.map((propName) => {
                            const checked = (missionForm.props_needed || []).includes(propName);
                            return (
                              <label key={`mission-prop-${propName}`} style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={(event) => {
                                    setMissionForm((current) => {
                                      const existing = new Set(current.props_needed || []);
                                      if (event.target.checked) {
                                        existing.add(propName);
                                      } else {
                                        existing.delete(propName);
                                      }
                                      const nextProps = Array.from(existing);
                                      const nextSettings = { ...(current.prop_settings || {}) };
                                      if (event.target.checked) {
                                        nextSettings[propName] = nextSettings[propName] || {
                                          enabled: true,
                                          game_time_seconds: Math.max(0, Number(current.main_timer_minutes) || 0) * 60,
                                          phase_time_seconds: Math.max(0, Number(current.phase_timer_minutes) || 0) * 60,
                                          notes: '',
                                        };
                                      } else {
                                        delete nextSettings[propName];
                                      }
                                      return { ...current, props_needed: nextProps, prop_settings: nextSettings };
                                    });
                                  }}
                                />
                                <span>{propName}</span>
                              </label>
                            );
                          })}
                        </div>
                      </div>

                      {(missionForm.props_needed || []).length > 0 ? (
                        <div style={{ marginTop: '0.7rem' }}>
                          <p className="schedule-meta" style={{ marginBottom: '0.35rem' }}>Prop Settings</p>
                          {(missionForm.props_needed || []).map((propName) => {
                            const settings = missionForm.prop_settings?.[propName] || {};
                            return (
                              <div key={`mission-prop-settings-${propName}`} style={{ border: '1px solid var(--line)', borderRadius: '6px', padding: '0.45rem', marginBottom: '0.35rem' }}>
                                <strong>{propName}</strong>
                                <label style={{ marginTop: '0.2rem' }}>
                                  <input
                                    type="checkbox"
                                    checked={settings.enabled !== false}
                                    onChange={(event) => {
                                      setMissionForm((current) => ({
                                        ...current,
                                        prop_settings: {
                                          ...(current.prop_settings || {}),
                                          [propName]: {
                                            ...(current.prop_settings?.[propName] || {}),
                                            enabled: event.target.checked,
                                          },
                                        },
                                      }));
                                    }}
                                  />
                                  Enabled
                                </label>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem' }}>
                                  <label>
                                    Game Time (sec)
                                    <input
                                      type="number"
                                      min="0"
                                      value={settings.game_time_seconds ?? Number(missionForm.main_timer_minutes) * 60}
                                      onChange={(event) => {
                                        setMissionForm((current) => ({
                                          ...current,
                                          prop_settings: {
                                            ...(current.prop_settings || {}),
                                            [propName]: {
                                              ...(current.prop_settings?.[propName] || {}),
                                              game_time_seconds: Number(event.target.value) || 0,
                                            },
                                          },
                                        }));
                                      }}
                                    />
                                  </label>
                                  <label>
                                    Phase Time (sec)
                                    <input
                                      type="number"
                                      min="0"
                                      value={settings.phase_time_seconds ?? Number(missionForm.phase_timer_minutes) * 60}
                                      onChange={(event) => {
                                        setMissionForm((current) => ({
                                          ...current,
                                          prop_settings: {
                                            ...(current.prop_settings || {}),
                                            [propName]: {
                                              ...(current.prop_settings?.[propName] || {}),
                                              phase_time_seconds: Number(event.target.value) || 0,
                                            },
                                          },
                                        }));
                                      }}
                                    />
                                  </label>
                                </div>
                                <label>
                                  Notes
                                  <input
                                    value={settings.notes || ''}
                                    onChange={(event) => {
                                      setMissionForm((current) => ({
                                        ...current,
                                        prop_settings: {
                                          ...(current.prop_settings || {}),
                                          [propName]: {
                                            ...(current.prop_settings?.[propName] || {}),
                                            notes: event.target.value,
                                          },
                                        },
                                      }));
                                    }}
                                  />
                                </label>
                              </div>
                            );
                          })}
                        </div>
                      ) : null}

                      <button type="button" onClick={handleCreateMission}>Create Mission</button>
                      <button type="button" onClick={saveMissionAsPreset} style={{ marginLeft: '0.5rem' }}>
                        Save as Preset
                      </button>
                      {presetSaveStatus ? (
                        <p className="schedule-meta" style={{ marginTop: '0.3rem' }}>{presetSaveStatus}</p>
                      ) : null}
                    </div>

                    <div className="mc-card">
                      <h3>Game Controls</h3>
                      <p className="mc-heading">Mission: {missionState.mission_title}</p>
                      <p className="mc-heading">Mode: {missionState.game_mode}</p>
                      <p className="mc-heading">State: {missionState.state.toUpperCase()}</p>

                      {missionState.state === 'ready' && (
                        <div className="ready-row">
                          <button
                            type="button"
                            className={`ready-btn ready-red${teamReadyState.red ? ' ready-active' : ''}`}
                            onClick={() => markTeamReady('red')}
                            disabled={teamReadyState.red || countdown !== null}
                          >
                            {teamReadyState.red ? `${redTeamLabel} ✓` : `${redTeamLabel} Ready?`}
                          </button>
                          <button
                            type="button"
                            className={`ready-btn ready-blue${teamReadyState.blue ? ' ready-active' : ''}`}
                            onClick={() => markTeamReady('blue')}
                            disabled={teamReadyState.blue || countdown !== null}
                          >
                            {teamReadyState.blue ? `${blueTeamLabel} ✓` : `${blueTeamLabel} Ready?`}
                          </button>
                          <button
                            type="button"
                            className="ready-btn ready-reset"
                            onClick={resetReady}
                            disabled={countdown !== null}
                          >
                            Reset
                          </button>
                        </div>
                      )}

                      {countdown !== null && (
                        <div className="countdown-display">
                          {countdown === 0 ? 'GO!' : countdown}
                        </div>
                      )}

                      <div className="control-row">
                        <button
                          type="button"
                          onClick={() => postMissionAction('/mission-control/start')}
                          disabled={countdown !== null}
                        >
                          Resume Game
                        </button>
                        <button type="button" onClick={() => postMissionAction('/mission-control/end')}>
                          End Game
                        </button>
                      </div>

                      <div className="timers-row">
                        <div className="timer-box">
                          <p>Main Countdown</p>
                          <strong>{formatDuration(missionState.main_timer_seconds)}</strong>
                        </div>
                        <div className="timer-box">
                          <p>Phase Timer</p>
                          <strong>{formatDuration(missionState.phase_timer_seconds)}</strong>
                        </div>
                      </div>

                      <div className="score-row">
                        <div className="score-card score-red">
                          <p>{redTeamLabel}</p>
                          <strong>{missionState.red_team_score}</strong>
                          <div>
                            <input
                              type="number"
                              min="1"
                              step="1"
                              value={manualScoreDelta.red}
                              onChange={(event) =>
                                setManualScoreDelta((current) => ({
                                  ...current,
                                  red: event.target.value,
                                }))
                              }
                            />
                            <button
                              type="button"
                              onClick={() => applyManualScore('red', 1)}
                            >
                              + Add
                            </button>
                            <button
                              type="button"
                              onClick={() => applyManualScore('red', -1)}
                            >
                              - Deduct
                            </button>
                          </div>
                        </div>
                        <div className="score-card score-blue">
                          <p>{blueTeamLabel}</p>
                          <strong>{missionState.blue_team_score}</strong>
                          <div>
                            <input
                              type="number"
                              min="1"
                              step="1"
                              value={manualScoreDelta.blue}
                              onChange={(event) =>
                                setManualScoreDelta((current) => ({
                                  ...current,
                                  blue: event.target.value,
                                }))
                              }
                            />
                            <button
                              type="button"
                              onClick={() => applyManualScore('blue', 1)}
                            >
                              + Add
                            </button>
                            <button
                              type="button"
                              onClick={() => applyManualScore('blue', -1)}
                            >
                              - Deduct
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="mc-card objectives-card">
                      <h3>Objective Status</h3>
                      {missionState.objectives.length === 0 ? <p className="muted">No objectives loaded.</p> : null}
                      {missionState.objectives.map((objective) => (
                        <div className="objective-row" key={objective.id}>
                          <span>{objective.label}</span>
                          <select
                            value={objective.status}
                            onChange={(event) =>
                              postMissionAction(`/mission-control/objectives/${objective.id}`, {
                                status: event.target.value,
                              })
                            }
                          >
                            <option value="pending">Pending</option>
                            <option value="active">Active</option>
                            <option value="complete">Complete</option>
                            <option value="failed">Failed</option>
                          </select>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              ) : isSchedule ? (
                <section className="schedule-module">
                  <div className="schedule-grid">
                    <div className="schedule-card">
                      <h3>{editingScheduleId ? 'Edit Schedule Item' : 'Add Schedule Item'}</h3>
                      <label>
                        Title
                        <input
                          value={scheduleForm.title}
                          onChange={(event) =>
                            setScheduleForm((current) => ({ ...current, title: event.target.value }))
                          }
                        />
                      </label>
                      <label>
                        Activity Type
                        <select
                          value={scheduleForm.activity_type}
                          onChange={(event) =>
                            setScheduleForm((current) => ({
                              ...current,
                              activity_type: event.target.value,
                            }))
                          }
                        >
                          {ACTIVITY_TYPES.map((type) => (
                            <option value={type} key={type}>
                              {type}
                            </option>
                          ))}
                        </select>
                      </label>
                      {scheduleForm.activity_type === 'Game' ? (
                        <>
                          <label>
                            Game Mode
                            <select
                              value={scheduleForm.game_mode}
                              onChange={(event) => {
                                const modeName = event.target.value;
                                const defaults = getDefaultPropsForGameMode(modeName);
                                setScheduleForm((current) => ({
                                  ...current,
                                  game_mode: modeName,
                                  props_needed: defaults,
                                }));
                              }}
                            >
                              <option value="">— none —</option>
                              {gameModeOptions.map((mode) => (
                                <option key={mode} value={mode}>{mode}</option>
                              ))}
                            </select>
                          </label>
                          <div>
                            <p className="schedule-meta" style={{ marginBottom: '0.3rem' }}>Props Needed</p>
                            {propNameOptions.length === 0 ? <p className="muted">No firmware props available.</p> : null}
                            <div style={{ display: 'grid', gap: '0.22rem', maxHeight: '8.5rem', overflowY: 'auto' }}>
                              {propNameOptions.map((propName) => (
                                <label key={`schedule-prop-${propName}`} style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                                  <input
                                    type="checkbox"
                                    checked={(scheduleForm.props_needed || []).includes(propName)}
                                    onChange={(event) => {
                                      setScheduleForm((current) => {
                                        const next = new Set(current.props_needed || []);
                                        if (event.target.checked) {
                                          next.add(propName);
                                        } else {
                                          next.delete(propName);
                                        }
                                        return { ...current, props_needed: Array.from(next) };
                                      });
                                    }}
                                  />
                                  <span>{propName}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        </>
                      ) : null}
                      <label>
                        Start Time
                        <input
                          type="time"
                          value={scheduleForm.start_time}
                          onChange={(event) =>
                            setScheduleForm((current) => ({
                              ...current,
                              start_time: event.target.value,
                            }))
                          }
                        />
                      </label>
                      <label>
                        Details
                        <textarea
                          value={scheduleForm.details}
                          onChange={(event) =>
                            setScheduleForm((current) => ({
                              ...current,
                              details: event.target.value,
                            }))
                          }
                        />
                      </label>
                      <div className="schedule-actions">
                        <button type="button" onClick={saveScheduleItem}>Save Item</button>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingScheduleId(null);
                            setScheduleForm({
                              title: '',
                              details: '',
                              activity_type: 'Custom',
                              game_mode: '',
                              props_needed: [],
                              start_time: '',
                              is_complete: false,
                            });
                          }}
                        >
                          Reset
                        </button>
                      </div>
                      {scheduleSaveError ? (
                        <p className="schedule-warning" style={{ marginTop: '0.5rem' }}>{scheduleSaveError}</p>
                      ) : null}
                    </div>

                    <div className="schedule-card">
                      <h3>Activity Overview</h3>
                      <p className="schedule-meta">
                        Current:{' '}
                        {scheduleOverview.current_activity
                          ? `${scheduleOverview.current_activity.title} (${scheduleOverview.current_activity.activity_type})`
                          : 'No active activity'}
                      </p>
                      <p className="schedule-meta">
                        Next:{' '}
                        {scheduleOverview.next_activity
                          ? `${scheduleOverview.next_activity.title} (${scheduleOverview.next_activity.activity_type})`
                          : 'No upcoming activity'}
                      </p>
                      {scheduleOverview.delay_warning ? (
                        <p className="schedule-warning">Delay Warning: {scheduleOverview.delay_warning}</p>
                      ) : (
                        <p className="schedule-ok">No delay warning</p>
                      )}
                    </div>

                    <div className="schedule-card schedule-list-card">
                      <h3>Schedule Items</h3>
                      {scheduleItems.length === 0 ? <p className="muted">No schedule items yet.</p> : null}
                      {scheduleItems.map((item) => (
                        <div className="schedule-item" key={item.id}>
                          <div className="schedule-item-header">
                            <strong>{item.title}</strong>
                            <span>{item.activity_type}{item.game_mode ? ` — ${item.game_mode}` : ''}</span>
                          </div>
                          <p className="schedule-meta">
                            {militaryTime(item.start_time)}
                          </p>
                          <p className="schedule-meta">{item.details || 'No details'}</p>
                          {item.activity_type === 'Game' && Array.isArray(item.props_needed) && item.props_needed.length > 0 ? (
                            <p className="schedule-meta">Props: {item.props_needed.join(', ')}</p>
                          ) : null}
                          <p className="schedule-meta">Status: {item.is_complete ? 'Complete' : 'Pending'}</p>
                          <div className="schedule-item-actions">
                            <button type="button" onClick={() => editScheduleItem(item)}>Edit</button>
                            <button type="button" onClick={() => completeScheduleItem(item.id)}>
                              Mark Complete
                            </button>
                            {item.activity_type === 'Game' ? (
                              <button
                                type="button"
                                onClick={() => {
                                  setRecordingResultForItemId(recordingResultForItemId === item.id ? null : item.id);
                                  setQuickResultForm({ winner: 'Draw', red_points: 0, blue_points: 0, notes: '' });
                                }}
                              >
                                {recordingResultForItemId === item.id ? 'Cancel Result' : 'Record Result'}
                              </button>
                            ) : null}
                            <button type="button" onClick={() => deleteScheduleItem(item.id)}>Delete</button>
                          </div>
                          {recordingResultForItemId === item.id ? (
                            <div style={{ marginTop: '0.5rem', padding: '0.5rem', background: 'var(--card-bg, #1a1a1a)', borderRadius: '4px', border: '1px solid var(--border-color, #333)' }}>
                              <p style={{ margin: '0 0 0.4rem', fontWeight: 600, fontSize: '0.85rem' }}>Quick Result — {item.title}</p>
                              <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.3rem' }}>
                                Winner
                                <select
                                  value={quickResultForm.winner}
                                  onChange={(e) => setQuickResultForm((f) => ({ ...f, winner: e.target.value }))}
                                  style={{ flex: 1 }}
                                >
                                  <option>Red</option>
                                  <option>Blue</option>
                                  <option>Draw</option>
                                  <option>Cancelled</option>
                                </select>
                              </label>
                              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.3rem' }}>
                                <label style={{ flex: 1 }}>
                                  Red pts
                                  <input type="number" min="0" value={quickResultForm.red_points}
                                    onChange={(e) => setQuickResultForm((f) => ({ ...f, red_points: e.target.value }))} />
                                </label>
                                <label style={{ flex: 1 }}>
                                  Blue pts
                                  <input type="number" min="0" value={quickResultForm.blue_points}
                                    onChange={(e) => setQuickResultForm((f) => ({ ...f, blue_points: e.target.value }))} />
                                </label>
                              </div>
                              <label style={{ marginBottom: '0.3rem' }}>
                                Notes
                                <input value={quickResultForm.notes}
                                  onChange={(e) => setQuickResultForm((f) => ({ ...f, notes: e.target.value }))}
                                  placeholder="Optional notes" />
                              </label>
                              <button type="button" onClick={() => quickRecordResult(item)}>Save Result</button>
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>

                    <div className="schedule-card">
                      <h3>Announcement Rules</h3>
                      <p className="schedule-meta muted">Christy will announce automatically at set times before schedule activities. Toggle rules on/off or customise the message.</p>

                      {announcementRules.length === 0 ? (
                        <p className="muted">No announcement rules yet.</p>
                      ) : null}
                      {announcementRules.map((rule) => (
                        <div className="schedule-item" key={rule.id} style={{ opacity: rule.enabled ? 1 : 0.5 }}>
                          <div className="schedule-item-header">
                            <strong>{rule.name}</strong>
                            <span>{rule.enabled ? 'Enabled' : 'Disabled'}</span>
                          </div>
                          <p className="schedule-meta">
                            Triggers {rule.trigger_minutes_before} min before{' '}
                            {rule.trigger_activity_types ? `"${rule.trigger_activity_types}"` : 'any activity'}
                          </p>
                          <p className="schedule-meta" style={{ fontStyle: 'italic' }}>"{rule.message_template}"</p>
                          <div className="schedule-item-actions">
                            <button type="button" onClick={() => startEditRule(rule)}>Edit</button>
                            <button type="button" onClick={() => toggleAnnouncementRule(rule)}>
                              {rule.enabled ? 'Disable' : 'Enable'}
                            </button>
                            <button type="button" onClick={() => deleteAnnouncementRule(rule.id)}>Delete</button>
                          </div>
                        </div>
                      ))}

                      <div style={{ marginTop: '0.8rem', borderTop: '1px solid var(--border-color, #333)', paddingTop: '0.8rem' }}>
                        <h4 style={{ margin: '0 0 0.5rem' }}>{editingRuleId ? 'Edit Rule' : 'Add Rule'}</h4>
                        <label>
                          Rule Name
                          <input
                            value={ruleForm.name}
                            onChange={(e) => setRuleForm((f) => ({ ...f, name: e.target.value }))}
                            placeholder="e.g. Drop-off warning"
                          />
                        </label>
                        <label>
                          Activity Types (comma-separated, blank = all)
                          <input
                            value={ruleForm.trigger_activity_types}
                            onChange={(e) => setRuleForm((f) => ({ ...f, trigger_activity_types: e.target.value }))}
                            placeholder="e.g. Drop Off, Pickup, Game"
                          />
                        </label>
                        <label>
                          Minutes Before Start
                          <input
                            type="number"
                            min="1"
                            max="1440"
                            value={ruleForm.trigger_minutes_before}
                            onChange={(e) => setRuleForm((f) => ({ ...f, trigger_minutes_before: e.target.value }))}
                          />
                        </label>
                        <label>
                          Announcement Message
                          <textarea
                            rows={3}
                            value={ruleForm.message_template}
                            onChange={(e) => setRuleForm((f) => ({ ...f, message_template: e.target.value }))}
                            placeholder="e.g. All players for {title} at {start_time} — please proceed to the car park now."
                            style={{ resize: 'vertical' }}
                          />
                        </label>
                        <p className="schedule-meta muted">Placeholders: {'{title}'}, {'{activity_type}'}, {'{start_time}'}</p>
                        <label style={{ flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
                          <input
                            type="checkbox"
                            checked={ruleForm.enabled}
                            onChange={(e) => setRuleForm((f) => ({ ...f, enabled: e.target.checked }))}
                            style={{ width: 'auto' }}
                          />
                          Enabled
                        </label>
                        <div className="schedule-actions" style={{ marginTop: '0.5rem' }}>
                          <button type="button" onClick={saveAnnouncementRule}>
                            {editingRuleId ? 'Update Rule' : 'Add Rule'}
                          </button>
                          {editingRuleId ? (
                            <button
                              type="button"
                              onClick={() => {
                                setEditingRuleId(null);
                                setRuleForm({ name: '', enabled: true, trigger_activity_types: '', trigger_minutes_before: 15, message_template: '' });
                              }}
                            >
                              Cancel
                            </button>
                          ) : null}
                        </div>
                      </div>
                    </div>

                    <div className="mc-card">
                      <h3>Today&#39;s Game Results</h3>
                      <p className="mc-heading" style={{ marginBottom: '0.6rem' }}>
                        {redTeamLabel} wins: {resultsSummary.total_red_wins} &nbsp;|&nbsp;
                        {blueTeamLabel} wins: {resultsSummary.total_blue_wins} &nbsp;|&nbsp;
                        Draws: {resultsSummary.total_draws} &nbsp;|&nbsp;
                        Cancelled: {resultsSummary.total_cancelled}
                      </p>
                      <p className="mc-heading" style={{ marginBottom: '0.8rem' }}>
                        {redTeamLabel} total pts: {resultsSummary.total_red_points} &nbsp;|&nbsp;
                        {blueTeamLabel} total pts: {resultsSummary.total_blue_points}
                      </p>

                      {scheduleItems.filter((i) => i.activity_type === 'Game').length === 0 ? (
                        <p className="muted">No games scheduled today. Add Game items in the Schedule tab.</p>
                      ) : null}

                      {scheduleItems.filter((i) => i.activity_type === 'Game').map((item) => {
                        const linked = resultsHistory.find((r) => r.schedule_item_id === item.id);
                        return (
                          <div key={item.id} style={{ marginBottom: '1rem', padding: '0.6rem', background: 'var(--card-bg, #1a1a1a)', borderRadius: '6px', border: '1px solid var(--border-color, #333)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                              <strong>{item.title}</strong>
                              <span style={{ fontSize: '0.8rem', opacity: 0.7 }}>
                                {militaryTime(item.start_time)}
                                {item.game_mode ? ` — ${item.game_mode}` : ''}
                              </span>
                            </div>

                            {linked ? (
                              <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center', flexWrap: 'wrap' }}>
                                <span style={{ padding: '2px 8px', borderRadius: '4px', background: linked.winner === 'Red' ? 'var(--red-color, #c0392b)' : linked.winner === 'Blue' ? 'var(--blue-color, #2980b9)' : '#555', color: '#fff', fontSize: '0.8rem' }}>
                                  {linked.winner}
                                </span>
                                <span style={{ fontSize: '0.85rem' }}>{redTeamLabel} {linked.red_points} pts</span>
                                <span style={{ fontSize: '0.85rem' }}>{blueTeamLabel} {linked.blue_points} pts</span>
                                {linked.red_penalties > 0 || linked.blue_penalties > 0 ? (
                                  <span style={{ fontSize: '0.78rem', opacity: 0.65 }}>
                                    Penalties - {redTeamLabel}: {linked.red_penalties} | {blueTeamLabel}: {linked.blue_penalties}
                                  </span>
                                ) : null}
                                {linked.notes ? <span style={{ fontSize: '0.78rem', opacity: 0.65 }}>{linked.notes}</span> : null}
                                <button
                                  type="button"
                                  style={{ marginLeft: 'auto', fontSize: '0.78rem', padding: '2px 8px' }}
                                  onClick={() => {
                                    setRecordingResultForItemId(recordingResultForItemId === item.id ? null : item.id);
                                    setQuickResultForm({ winner: linked.winner, red_points: linked.red_points, blue_points: linked.blue_points, notes: linked.notes || '' });
                                  }}
                                >
                                  Edit Result
                                </button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                onClick={() => {
                                  setRecordingResultForItemId(recordingResultForItemId === item.id ? null : item.id);
                                  setQuickResultForm({ winner: 'Draw', red_points: 0, blue_points: 0, notes: '' });
                                }}
                              >
                                {recordingResultForItemId === item.id ? 'Cancel' : 'Record Result'}
                              </button>
                            )}

                            {recordingResultForItemId === item.id ? (
                              <div style={{ marginTop: '0.5rem', display: 'grid', gap: '0.4rem' }}>
                                <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                  Winner
                                  <select
                                    value={quickResultForm.winner}
                                    onChange={(e) => setQuickResultForm((f) => ({ ...f, winner: e.target.value }))}
                                    style={{ flex: 1 }}
                                  >
                                    <option>Red</option><option>Blue</option><option>Draw</option><option>Cancelled</option>
                                  </select>
                                </label>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                  <label style={{ flex: 1 }}>
                                    {redTeamLabel} points
                                    <input type="number" min="0" value={quickResultForm.red_points}
                                      onChange={(e) => setQuickResultForm((f) => ({ ...f, red_points: e.target.value }))} />
                                  </label>
                                  <label style={{ flex: 1 }}>
                                    {blueTeamLabel} points
                                    <input type="number" min="0" value={quickResultForm.blue_points}
                                      onChange={(e) => setQuickResultForm((f) => ({ ...f, blue_points: e.target.value }))} />
                                  </label>
                                </div>
                                <label>
                                  Notes (optional)
                                  <input value={quickResultForm.notes}
                                    onChange={(e) => setQuickResultForm((f) => ({ ...f, notes: e.target.value }))} />
                                </label>
                                <button type="button" onClick={() => quickRecordResult(item)}>Save Result</button>
                              </div>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>

                    <div className="mc-card">
                      <h3>Session History</h3>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.5rem' }}>
                        <button type="button" onClick={exportResultsCsv} style={{ fontSize: '0.8rem' }}>Export CSV</button>
                      </div>
                      {resultsHistory.length === 0 ? <p className="muted">No results recorded yet.</p> : null}
                      {resultsHistory.map((result) => (
                        <div key={result.id} style={{ marginBottom: '0.6rem', padding: '0.5rem', background: 'var(--card-bg, #1a1a1a)', borderRadius: '5px', border: '1px solid var(--border-color, #333)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <strong style={{ fontSize: '0.9rem' }}>{result.session_name}</strong>
                            <span style={{ padding: '1px 7px', borderRadius: '4px', background: result.winner === 'Red' ? 'var(--red-color, #c0392b)' : result.winner === 'Blue' ? 'var(--blue-color, #2980b9)' : '#555', color: '#fff', fontSize: '0.78rem' }}>
                              {result.winner}
                            </span>
                          </div>
                          <p style={{ margin: '0.2rem 0 0', fontSize: '0.82rem', opacity: 0.75 }}>
                            {redTeamLabel} {result.red_points} pts &nbsp;|&nbsp; {blueTeamLabel} {result.blue_points} pts
                          </p>
                          {result.notes ? <p style={{ margin: '0.1rem 0 0', fontSize: '0.78rem', opacity: 0.6 }}>{result.notes}</p> : null}
                          <p style={{ margin: '0.1rem 0 0', fontSize: '0.72rem', opacity: 0.45 }}>{new Date(result.created_at).toLocaleString()}</p>
                        </div>
                      ))}
                    </div>


                  </div>
                </section>
              ) : isPropNetwork ? (
                <section className="prop-module">
                  <div className="prop-grid">
                    <div className="prop-card">
                      <h3>{editingPropId ? 'Edit Prop' : 'Add Prop'}</h3>
                      <label>
                        Device ID
                        <input
                          value={propForm.device_id}
                          onChange={(event) =>
                            setPropForm((current) => ({ ...current, device_id: event.target.value }))
                          }
                        />
                      </label>
                      <label>
                        Name
                        <input
                          value={propForm.name}
                          onChange={(event) =>
                            setPropForm((current) => ({ ...current, name: event.target.value }))
                          }
                        />
                      </label>
                      <label>
                        Type
                        <select
                          value={propForm.prop_type}
                          onChange={(event) =>
                            setPropForm((current) => ({ ...current, prop_type: event.target.value }))
                          }
                        >
                          {PROP_TYPES.map((type) => (
                            <option key={type} value={type}>
                              {type}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Location
                        <input
                          value={propForm.location}
                          onChange={(event) =>
                            setPropForm((current) => ({ ...current, location: event.target.value }))
                          }
                        />
                      </label>
                      <label>
                        Firmware Version
                        <input
                          value={propForm.firmware_version}
                          onChange={(event) =>
                            setPropForm((current) => ({ ...current, firmware_version: event.target.value }))
                          }
                        />
                      </label>
                      <label>
                        Device Auth Token (optional, min 8 chars)
                        <input
                          value={propForm.auth_token}
                          onChange={(event) =>
                            setPropForm((current) => ({ ...current, auth_token: event.target.value }))
                          }
                          placeholder="Leave blank to keep existing token"
                        />
                      </label>
                      {propSaveError ? <p style={{ color: 'var(--danger-color, #e74c3c)', marginTop: '0.4rem' }}>{propSaveError}</p> : null}
                      <div className="prop-actions">
                        <button type="button" onClick={saveProp}>Save Prop</button>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingPropId(null);
                            setPropSaveError('');
                            setPropForm({
                              device_id: '',
                              name: '',
                              prop_type: 'Custom',
                              location: '',
                              firmware_version: '',
                            });
                          }}
                        >
                          Reset
                        </button>
                      </div>
                    </div>

                    <div className="prop-card prop-list-card">
                      <h3>Registered Props</h3>
                      {propsList.length === 0 ? <p className="muted">No props registered.</p> : null}
                      {propsList.map((item) => (
                        <div className="prop-item" key={item.id}>
                          <div className="prop-item-header">
                            <strong>{item.name}</strong>
                            <span>{item.prop_type}</span>
                          </div>
                          <p className="prop-meta">Device ID: {item.device_id}</p>
                          <p className="prop-meta">Location: {item.location || 'Unknown'}</p>
                          <p className="prop-meta">Status: {item.status}</p>
                          <p className="prop-meta">
                            Battery: {item.battery_level}% | Signal: {item.signal_strength}%
                          </p>
                          <p className="prop-meta">
                            Last Status Report:{' '}
                            {item.last_seen ? new Date(item.last_seen).toLocaleString() : 'Never'}
                          </p>
                          <p className="prop-meta">Firmware: {item.firmware_version || 'N/A'}</p>
                          <div className="prop-item-actions">
                            <button type="button" onClick={() => startEditProp(item)}>Edit</button>
                            <button type="button" onClick={() => rotatePropToken(item.id)}>Issue Token</button>
                            <button type="button" onClick={() => deleteProp(item.id)}>Delete</button>
                          </div>
                          {issuedPropTokens[item.id] ? (
                            <div className="prop-meta" style={{ marginTop: '0.45rem' }}>
                              <strong>Issued token:</strong> {issuedPropTokens[item.id]}
                              <button
                                type="button"
                                style={{ marginLeft: '0.45rem', width: 'auto' }}
                                onClick={() => copyToken(issuedPropTokens[item.id])}
                              >
                                Copy
                              </button>
                            </div>
                          ) : null}
                          <div className="prop-command-grid">
                            <button type="button" onClick={() => sendPropCommand(item.id, 'arm')}>Arm</button>
                            <button type="button" onClick={() => sendPropCommand(item.id, 'disarm')}>
                              Disarm
                            </button>
                            <button type="button" onClick={() => sendPropCommand(item.id, 'reset')}>Reset</button>
                            <button
                              type="button"
                              onClick={() => sendPropCommand(item.id, 'status_request')}
                            >
                              Status Request
                            </button>
                            <button
                              type="button"
                              onClick={() => sendPropCommand(item.id, 'trigger_alarm')}
                            >
                              Trigger Alarm
                            </button>
                            <button
                              type="button"
                              onClick={() => sendPropCommand(item.id, 'game_start')}
                            >
                              Game Start
                            </button>
                            <button
                              type="button"
                              onClick={() => sendPropCommand(item.id, 'game_end')}
                            >
                              Game End
                            </button>
                            <button
                              type="button"
                              onClick={() => sendPropCommand(item.id, 'ready')}
                            >
                              Ready
                            </button>
                            <button
                              type="button"
                              onClick={() => sendPropCommand(item.id, 'test_buzz')}
                            >
                              Test Buzzer
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              ) : isLogs ? (
                <section className="logs-module">
                  <div className="logs-grid">
                    <div className="logs-card">
                      <h3>System Log Filters</h3>
                      <div className="logs-filter-grid">
                        <label>
                          Level
                          <select
                            value={logFilters.level}
                            onChange={(event) =>
                              setLogFilters((current) => ({
                                ...current,
                                level: event.target.value,
                              }))
                            }
                          >
                            {LOG_LEVELS.map((level) => (
                              <option key={level} value={level}>
                                {level}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Category
                          <select
                            value={logFilters.category}
                            onChange={(event) =>
                              setLogFilters((current) => ({
                                ...current,
                                category: event.target.value,
                              }))
                            }
                          >
                            {LOG_CATEGORIES.map((category) => (
                              <option key={category} value={category}>
                                {category}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>

                      <div className="logs-actions">
                        <button type="button" onClick={() => fetchSystemLogs()}>
                          Refresh
                        </button>
                        <button type="button" onClick={exportSystemLogsCsv}>Export CSV</button>
                        <button type="button" onClick={clearSystemLogs}>Clear Logs</button>
                      </div>
                    </div>

                    <div className="logs-card logs-list-card">
                      <h3>System Logs</h3>
                      {systemLogs.length === 0 ? <p className="muted">No logs found for current filter.</p> : null}
                      {systemLogs.map((log) => (
                        <div className="log-item" key={log.id}>
                          <div className="log-item-header">
                            <strong>{log.level}</strong>
                            <span>{log.category}</span>
                          </div>
                          <p className="log-meta">Source: {log.source}</p>
                          <p className="log-message">{log.message}</p>
                          <p className="log-meta">{new Date(log.created_at).toLocaleString()}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              ) : isSystemMonitor ? (
                <section className="monitor-module">
                  <div className="monitor-grid">
                    <div className="monitor-card">
                      <h3>Runtime</h3>
                      <p className="monitor-meta">Backend Version: {systemStatus.backend_version}</p>
                      <p className="monitor-meta">Mode: {systemStatus.platform_mode}</p>
                      <p className="monitor-meta">Uptime: {formatUptime(systemStatus.uptime_seconds)}</p>
                      <p className="monitor-meta">WebSocket Clients: {systemStatus.connected_clients}</p>
                      <p className="monitor-meta">Active Sessions: {systemStatus.active_game_sessions}</p>
                    </div>

                    <div className="monitor-card">
                      <h3>Pi Telemetry</h3>
                      <p className="monitor-meta">CPU Temp: {systemStatus.cpu_temperature_c.toFixed(1)} C</p>
                      <p className="monitor-meta">CPU Usage: {systemStatus.cpu_usage_percent.toFixed(1)}%</p>
                      <p className="monitor-meta">RAM Usage: {systemStatus.ram_usage_percent.toFixed(1)}%</p>
                      <p className="monitor-meta">Disk Usage: {systemStatus.disk_usage_percent.toFixed(1)}%</p>
                    </div>

                    <div className="monitor-card">
                      <h3>Services</h3>
                      <p className="monitor-meta">Database: {systemStatus.database_status}</p>
                      <p className="monitor-meta">LoRa Service: {systemStatus.lora_service_status}</p>
                      <p className="monitor-meta">Backend Status: {systemStatus.status}</p>
                    </div>

                    <div className="monitor-card monitor-entities-card">
                      <h3>Entity Counters</h3>
                      {Object.entries(systemStatus.entity_counts).map(([name, value]) => (
                        <div className="monitor-entity-row" key={name}>
                          <span>{name}</span>
                          <strong>{value}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              ) : isUpdateCenter ? (
                <section className="update-module">
                  <div className="update-grid">
                    <div className="update-card">
                      <h3>Versions</h3>
                      <p className="update-meta">System Version: {updateCenterStatus.system_version}</p>
                      <p className="update-meta">Frontend Version: {updateCenterStatus.frontend_version}</p>
                      <p className="update-meta">Backend Version: {updateCenterStatus.backend_version}</p>
                      <p className="update-meta">Database Version: {updateCenterStatus.database_version}</p>
                      <p className="update-meta">Database Path: {updateCenterStatus.database_path}</p>
                      <p className="update-meta">Latest Backup: {updateCenterStatus.latest_backup || 'None'}</p>
                      <p className="update-meta">Firmware Packages: {updateCenterStatus.firmware_packages_count}</p>
                      <p className="update-meta">
                        Last Firmware Upload: {updateCenterStatus.last_firmware_rollout || 'None'}
                      </p>
                    </div>

                    <div className="update-card">
                      <h3>Firmware Rollout</h3>
                      <label>
                        Firmware Package File
                        <input
                          type="file"
                          onChange={(event) => setSelectedUpdatePackage(event.target.files?.[0] ?? null)}
                        />
                      </label>
                      <label>
                        Firmware Version
                        <input
                          value={firmwareVersion}
                          onChange={(event) => setFirmwareVersion(event.target.value)}
                          placeholder="e.g. 1.2.3"
                        />
                      </label>
                      <label>
                        Notes
                        <input
                          value={firmwareNotes}
                          onChange={(event) => setFirmwareNotes(event.target.value)}
                          placeholder="Optional rollout note"
                        />
                      </label>
                      <label>
                        Uploaded Packages
                        <select
                          value={selectedFirmwarePackageId}
                          onChange={(event) => setSelectedFirmwarePackageId(event.target.value)}
                        >
                          <option value="">Select package...</option>
                          {firmwarePackages.map((pkg) => (
                            <option key={pkg.id} value={pkg.id}>
                              {pkg.version} - {pkg.filename}
                            </option>
                          ))}
                        </select>
                      </label>
                      <p className="update-warning">
                        Select target props below. If none are selected, rollout applies to all registered props.
                      </p>
                      <div className="update-log-entry" style={{ maxHeight: '140px', overflowY: 'auto' }}>
                        {propsList.length === 0 ? (
                          <p className="muted">No props available.</p>
                        ) : (
                          propsList.map((item) => (
                            <label key={item.id} style={{ display: 'block', marginBottom: '0.25rem' }}>
                              <input
                                type="checkbox"
                                checked={selectedFirmwarePropIds.includes(item.id)}
                                onChange={() => toggleFirmwareTargetProp(item.id)}
                              />{' '}
                              {item.name} ({item.device_id})
                            </label>
                          ))
                        )}
                      </div>
                      <div className="update-actions">
                        <button
                          type="button"
                          onClick={uploadFirmwarePackage}
                        >
                          Upload Firmware
                        </button>
                        <button type="button" onClick={applyFirmwarePackage}>
                          Apply Firmware
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedFirmwarePropIds([]);
                          }}
                        >
                          Clear Targets
                        </button>
                        <button type="button" onClick={() => runUpdateCenterAction('/update-center/backup')}>
                          Backup Database
                        </button>
                        <button
                          type="button"
                          onClick={() => runUpdateCenterAction('/update-center/restore-placeholder')}
                        >
                          Restore Placeholder
                        </button>
                        <button
                          type="button"
                          onClick={() => runUpdateCenterAction('/update-center/rollback-placeholder')}
                        >
                          Rollback Placeholder
                        </button>
                      </div>
                      <p className="update-warning">
                        Firmware rollout is queued through LoRa commands. Core app restore and rollback remain safe placeholders.
                      </p>
                      {updateMessage ? <p className="update-status-message">{updateMessage}</p> : null}
                    </div>

                    <div className="update-card update-changelog-card">
                      <h3>Firmware Rollout History</h3>
                      {firmwareRollouts.length === 0 ? <p className="muted">No rollout jobs yet.</p> : null}
                      {firmwareRollouts.map((job) => (
                        <div className="update-log-entry" key={job.id}>
                          <strong>Job #{job.id}</strong> | {job.package_version} | {job.status}
                          <br />
                          Targets: {job.targeted_count} | Acked: {job.acknowledged_count} | Failed: {job.failed_count}
                          <br />
                          {new Date(job.created_at).toLocaleString()}
                        </div>
                      ))}
                    </div>

                    <div className="update-card update-changelog-card">
                      <h3>Changelog</h3>
                      {updateCenterStatus.changelog.length === 0 ? <p className="muted">No changelog entries.</p> : null}
                      {updateCenterStatus.changelog.map((item) => (
                        <div className="update-log-entry" key={item}>
                          {item}
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              ) : isAIAssistant ? (
                <section className="ai-module">
                  <div className="ai-grid">
                    <div className="ai-card">
                      <h3>Quick Prompts</h3>
                      <div className="ai-prompt-grid">
                        {AI_QUICK_PROMPTS.map((prompt) => (
                          <button
                            key={prompt}
                            type="button"
                            disabled={aiTyping}
                            onClick={() => askAI(prompt)}
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                      <p className="ai-safety-note" style={{ marginTop: '0.6rem' }}>
                        For operational actions, the AI will ask you to confirm before proceeding.
                      </p>
                      <div className="ai-card" style={{ marginTop: '0.6rem', padding: '0.55rem' }}>
                        <h3 style={{ marginBottom: '0.4rem' }}>Today Agenda</h3>
                        <p className="schedule-meta" style={{ margin: '0.2rem 0' }}>
                          Current: {scheduleOverview.current_activity ? scheduleOverview.current_activity.title : 'None'}
                        </p>
                        <p className="schedule-meta" style={{ margin: '0.2rem 0 0.5rem' }}>
                          Next: {scheduleOverview.next_activity
                            ? `${scheduleOverview.next_activity.title} @ ${militaryTime(scheduleOverview.next_activity.start_time)}`
                            : 'None'}
                        </p>
                        <div className="ai-prompt-grid">
                          <button type="button" onClick={announceNextAgendaNow} disabled={!scheduleOverview.next_activity}>
                            Announce Next Activity
                          </button>
                          <button type="button" onClick={askAiForNextAgendaBrief}>
                            Prepare Next Brief in Chat
                          </button>
                        </div>
                      </div>
                      <div className="ai-prompt-grid" style={{ marginTop: '0.6rem' }}>
                        <button
                          type="button"
                          onClick={isListening ? stopVoiceInput : startVoiceInput}
                          disabled={!speechInputSupported || aiTyping || !aiVoiceInputEnabled}
                        >
                          {isListening ? 'Stop Listening' : 'Voice Input'}
                        </button>
                        <button
                          type="button"
                          onClick={speakLatestAssistantMessage}
                          disabled={!speechOutputSupported || !aiVoiceOutputEnabled}
                        >
                          Speak Last Reply
                        </button>
                        <button
                          type="button"
                          onClick={stopSpeakingNow}
                          disabled={!isSpeaking}
                        >
                          Stop Speaking
                        </button>
                        <button type="button" onClick={clearAiConversation} title="Start a new conversation">
                          New Chat
                        </button>
                      </div>
                      <div style={{ marginTop: '0.75rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', opacity: 0.8 }}>
                          Typed Announcement (speak aloud)
                        </label>
                        <textarea
                          value={announcementText}
                          onChange={(event) => setAnnouncementText(event.target.value)}
                          placeholder="Type what Christy should announce aloud..."
                          style={{ width: '100%', minHeight: '68px', resize: 'vertical' }}
                        />
                        <div style={{ marginTop: '0.35rem' }}>
                          <button type="button" onClick={speakAnnouncementText} disabled={!aiVoiceOutputEnabled}>
                            Announce Aloud
                          </button>
                        </div>
                      </div>
                      {!aiVoiceInputEnabled ? <p className="ai-safety-note">Voice input is disabled in Admin AI Settings.</p> : null}
                      {!aiVoiceOutputEnabled ? <p className="ai-safety-note">Voice output is disabled in Admin AI Settings.</p> : null}
                      {!speechInputSupported ? <p className="ai-safety-note">Speech input unsupported in this browser.</p> : null}
                      {!speechOutputSupported ? <p className="ai-safety-note">Speech output unsupported in this browser.</p> : null}
                      {voiceNote ? <p className="ai-safety-note">{voiceNote}</p> : null}
                      {speechError ? <p className="ai-safety-note" style={{ color: 'var(--danger-color, #f55)' }}>{speechError}</p> : null}
                    </div>

                    <div className="ai-card ai-chat-card">
                      <h3>Christy — AOJ Field Advisor</h3>
                      <div className="ai-chat-log">
                        {aiMessages.map((item, index) => (
                          <div key={`${item.role}-${index}`} className={`ai-bubble ai-${item.role}`}>
                            {/* Render simple markdown: **bold**, numbered lists, bullet lines */}
                            <div style={{ whiteSpace: 'pre-wrap' }}>
                              {item.text.split('\n').map((line, li) => {
                                const parts = [];
                                let lastIndex = 0;
                                const regex = /\*\*(.+?)\*\*/g;
                                let match;
                                while ((match = regex.exec(line)) !== null) {
                                  if (match.index > lastIndex) {
                                    parts.push(line.substring(lastIndex, match.index));
                                  }
                                  parts.push(<strong key={`${li}-${match.index}`}>{match[1]}</strong>);
                                  lastIndex = match.index + match[0].length;
                                }
                                if (lastIndex < line.length) {
                                  parts.push(line.substring(lastIndex));
                                }
                                return (
                                  <p key={li} style={{ margin: '0.15rem 0' }}>
                                    {parts.length > 0 ? parts : line}
                                  </p>
                                );
                              })}
                            </div>
                            {item.awaiting_confirm ? (
                              <div style={{ marginTop: '0.4rem' }}>
                                <button
                                  type="button"
                                  style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem' }}
                                  onClick={() => { askAI('yes confirm'); }}
                                >
                                  ✓ Confirm
                                </button>
                              </div>
                            ) : null}
                            {item.meta ? <small>{item.meta}</small> : null}
                          </div>
                        ))}
                        {aiTyping ? (
                          <div className="ai-bubble ai-assistant">
                            <p style={{ opacity: 0.6 }}>Advisor is thinking...</p>
                          </div>
                        ) : null}
                        <div ref={aiChatEndRef} />
                      </div>

                      <div className="ai-chat-input-row">
                        <textarea
                          value={aiInput}
                          onChange={(event) => setAiInput(event.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                              e.preventDefault();
                              if (aiInput.trim()) { askAI(aiInput); setAiInput(''); }
                            }
                          }}
                          placeholder="Ask for operational advice, game suggestions, or briefing text... (Enter to send)"
                          disabled={aiTyping}
                        />
                        <button
                          type="button"
                          disabled={aiTyping || !aiInput.trim()}
                          onClick={() => { askAI(aiInput); setAiInput(''); }}
                        >
                          Send
                        </button>
                      </div>
                    </div>
                  </div>
                </section>
              ) : isSettings ? (
                <section className="settings-module">
                  <nav className="settings-tabs">
                    {[
                      { id: 'general', label: 'General' },
                      { id: 'teams', label: 'Teams' },
                      { id: 'game-modes', label: 'Game Modes' },
                      { id: 'knowledge', label: 'Knowledge Base' },
                      { id: 'theme', label: 'Theme' },
                      { id: 'ai', label: 'AI Settings' },
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        className={settingsTab === tab.id ? 'settings-tab active' : 'settings-tab'}
                        onClick={() => setSettingsTab(tab.id)}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </nav>
                  <div className="settings-panel">
                    {settingsTab === 'general' ? (
                      <div className="settings-general-grid">
                        <div className="settings-general-card">
                          <h3>Workspace Layout</h3>
                          <label className="settings-toggle-row">
                            <input
                              type="checkbox"
                              checked={showLiveFeed}
                              onChange={(event) =>
                                setUiPrefs((current) => ({
                                  ...current,
                                  showLiveFeed: event.target.checked,
                                }))
                              }
                            />
                            <span>Show Live Feed panel</span>
                          </label>
                          <p className="muted">When off, the workspace uses a cleaner single-panel layout.</p>
                        </div>

                        <div className="settings-general-card">
                          <h3>System Profile</h3>
                          <ul>
                            {WINDOW_CONTENT['settings'].map((item) => (
                              <li key={item}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ) : settingsTab === 'teams' ? (
                      <AdminCustomTeams apiBase={apiBase} />
                    ) : settingsTab === 'game-modes' ? (
                      <AdminGameModes apiBase={apiBase} />
                    ) : settingsTab === 'knowledge' ? (
                      <AdminKnowledgeBase apiBase={apiBase} />
                    ) : settingsTab === 'theme' ? (
                      <AdminThemeEditor apiBase={apiBase} />
                    ) : settingsTab === 'ai' ? (
                      <AdminAISettings apiBase={apiBase} />
                    ) : null}
                  </div>
                </section>
              ) : (
                <ul>
                  {WINDOW_CONTENT[activeApp.id].map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              )}
              </div>
            </article>
          ) : (
            <article className="window primary-window desktop-empty-window">
              <div className="window-titlebar">
                <span>Desktop Workspace</span>
                <small>Open a module icon to launch a window</small>
              </div>
              <div className="window-content">
                <p className="muted">No active window. Select any icon from Tactical Desktop.</p>
              </div>
            </article>
          )}

          {showLiveFeed ? (
            <article className="window aux-window">
              <div className="window-titlebar">
                <span>Live Feed</span>
                <small>WebSocket Stream</small>
              </div>
              <div className="window-content">
                {events.length === 0 ? <p className="muted">Awaiting field telemetry...</p> : null}
                <ul className="live-feed-list">
                  {events.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            </article>
          ) : null}
        </section>
      </main>

      <footer className="desktop-taskbar">
        <button
          type="button"
          className={`taskbar-window${windowOpen && !windowMinimized ? ' active' : ''}`}
          onClick={restoreDesktopWindow}
        >
          {activeApp.title}
        </button>
      </footer>
    </div>
  );
}

export default App;
