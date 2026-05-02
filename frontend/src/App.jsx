import { useEffect, useMemo, useState } from 'react';
import { AdminCustomTeams } from './components/AdminCustomTeams';
import { AdminGameModes } from './components/AdminGameModes';
import { AdminKnowledgeBase } from './components/AdminKnowledgeBase';
import { AdminThemeEditor } from './components/AdminThemeEditor';
import { AdminAISettings } from './components/AdminAISettings';

const APPS = [
  { id: 'mission-control', title: 'Mission Control', subtitle: 'Live objectives and squad directives' },
  { id: 'prop-network', title: 'Prop Network', subtitle: 'Field devices, relays, and trigger nodes' },
  { id: 'schedule', title: 'Schedule', subtitle: 'Operations timeline and event sequencing' },
  { id: 'results-board', title: 'Results Board', subtitle: 'Session scoreflow and rank snapshots' },
  { id: 'system-monitor', title: 'System Monitor', subtitle: 'Runtime health and resource telemetry' },
  { id: 'ai-assistant', title: 'AI Assistant', subtitle: 'Command aide for planning and analysis' },
  { id: 'update-center', title: 'Update Center', subtitle: 'Node sync, package state, firmware rollout' },
  { id: 'logs', title: 'Logs', subtitle: 'Audit stream and anomaly events' },
  { id: 'settings', title: 'Settings', subtitle: 'Network, access, and interface controls' },
  { id: 'admin-teams', title: 'Admin: Teams', subtitle: 'Manage custom team configurations' },
  { id: 'admin-game-modes', title: 'Admin: Game Modes', subtitle: 'Manage custom game modes' },
  { id: 'admin-knowledge', title: 'Admin: Knowledge Base', subtitle: 'Manage custom knowledge entries' },
  { id: 'admin-theme', title: 'Admin: Theme', subtitle: 'Customize interface colors and appearance' },
  { id: 'admin-ai-settings', title: 'Admin: AI Settings', subtitle: 'Configure AI assistant behavior' },
];

const WINDOW_CONTENT = {
  'prop-network': ['12 props registered on subnet', '2 relays in maintenance state', 'Latency envelope: 18ms average'],
  schedule: ['14:00 Briefing', '14:20 Session Alpha launch', '15:10 Mission reset and scoreboard review'],
  'results-board': ['Blue Team: 1420', 'Red Team: 1310', 'Green Team: 890'],
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
  event_feed: [],
  updated_at: '',
};

const DEFAULT_GAME_MODES = ['Skirmish', 'Domination', 'Capture Point', 'Hostage Rescue'];
const ACTIVITY_TYPES = [
  'Safety Brief',
  'Game',
  'Break',
  'Lunch',
  'Setup',
  'Pack Down',
  'Custom',
];
const WINNER_OPTIONS = ['Red', 'Blue', 'Draw', 'Cancelled'];
const PROP_TYPES = [
  'Bomb',
  'Domination Point',
  'Respawn Station',
  'Alarm',
  'Sensor',
  'Custom',
];
const LOG_LEVELS = ['ALL', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
const LOG_CATEGORIES = ['ALL', 'SYSTEM', 'MISSION', 'PROP', 'LORA', 'WIFI', 'AI', 'UPDATE'];
const AI_QUICK_PROMPTS = [
  'Suggest next game',
  'Summarize results',
  'Create marshal briefing',
  'Explain prop issue',
  'Check schedule delay',
  'Generate team announcement',
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

function App() {
  const host = window.location.hostname || 'localhost';
  const apiBase = useMemo(() => `http://${host}:8000/api`, [host]);
  const wsUrl = useMemo(() => {
    return `ws://${host}:8000/ws/live`;
  }, [host]);

  const [networkStatus, setNetworkStatus] = useState('CONNECTING');
  const [events, setEvents] = useState([]);
  const [selectedApp, setSelectedApp] = useState(APPS[0].id);
  const [clock, setClock] = useState(new Date());
  const [deviceCount] = useState(8);
  const [alerts] = useState(2);
  const [currentTheme, setCurrentTheme] = useState(null);
  const [missionState, setMissionState] = useState(DEFAULT_MISSION_STATE);
  const [gameModeOptions, setGameModeOptions] = useState(DEFAULT_GAME_MODES);
  const [missionForm, setMissionForm] = useState({
    title: 'Operation Echo',
    description: 'Field objective sequence for Sector Echo.',
    game_mode: DEFAULT_GAME_MODES[0],
    main_timer_seconds: 1800,
    phase_timer_seconds: 300,
    objectivesText: 'Capture Relay,Hold HQ,Extract VIP',
  });
  const [scheduleItems, setScheduleItems] = useState([]);
  const [scheduleOverview, setScheduleOverview] = useState({
    current_activity: null,
    next_activity: null,
    delay_warning: null,
  });
  const [editingScheduleId, setEditingScheduleId] = useState(null);
  const [scheduleForm, setScheduleForm] = useState({
    title: 'Safety Briefing',
    details: 'Operator brief and radio checks.',
    activity_type: 'Safety Brief',
    start_time: '',
    end_time: '',
    is_complete: false,
  });
  const [resultsHistory, setResultsHistory] = useState([]);
  const [resultsSummary, setResultsSummary] = useState({
    total_red_wins: 0,
    total_blue_wins: 0,
    total_draws: 0,
    total_cancelled: 0,
    total_red_points: 0,
    total_blue_points: 0,
  });
  const [resultForm, setResultForm] = useState({
    session_name: 'Session Alpha',
    winner: 'Draw',
    red_points: 0,
    blue_points: 0,
    red_penalties: 0,
    blue_penalties: 0,
    notes: '',
  });
  const [propsList, setPropsList] = useState([]);
  const [editingPropId, setEditingPropId] = useState(null);
  const [propForm, setPropForm] = useState({
    device_id: '',
    name: '',
    prop_type: 'Custom',
    location: '',
    status: 'offline',
    battery_level: 100,
    signal_strength: 100,
    last_seen: '',
    firmware_version: '',
  });
  const [systemLogs, setSystemLogs] = useState([]);
  const [logFilters, setLogFilters] = useState({ level: 'ALL', category: 'ALL' });
  const [systemStatus, setSystemStatus] = useState(DEFAULT_SYSTEM_STATUS);
  const [aiInput, setAiInput] = useState('');
  const [aiMessages, setAiMessages] = useState([
    {
      role: 'assistant',
      text: 'Mock local advisor online. Advisory only mode is enforced.',
      meta: 'safety: admin confirmation required for operational commands',
    },
  ]);
  const [updateCenterStatus, setUpdateCenterStatus] = useState(DEFAULT_UPDATE_CENTER_STATUS);
  const [updateMessage, setUpdateMessage] = useState('');
  const [selectedUpdatePackage, setSelectedUpdatePackage] = useState(null);

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
        return;
      }

      const rows = await response.json();
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
    setPropsList(payload);
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

  async function askAI(prompt) {
    const cleanedPrompt = prompt.trim();
    if (!cleanedPrompt) {
      return;
    }

    setAiMessages((current) => [
      ...current,
      {
        role: 'user',
        text: cleanedPrompt,
      },
    ]);

    const response = await fetch(`${apiBase}/ai/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: cleanedPrompt }),
    });

    if (!response.ok) {
      setAiMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: 'AI route unavailable. Check backend connectivity.',
          meta: 'error',
        },
      ]);
      return;
    }

    const payload = await response.json();
    setAiMessages((current) => [
      ...current,
      {
        role: 'assistant',
        text: payload.answer,
        meta: `${payload.model} | ${payload.safety_notice}`,
      },
    ]);
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
    if (!propForm.device_id.trim() || !propForm.name.trim()) {
      return;
    }

    const body = {
      ...propForm,
      battery_level: Number(propForm.battery_level) || 0,
      signal_strength: Number(propForm.signal_strength) || 0,
      last_seen: propForm.last_seen ? new Date(propForm.last_seen).toISOString() : null,
    };

    const path = editingPropId ? `${apiBase}/props/${editingPropId}` : `${apiBase}/props`;
    const method = editingPropId ? 'PUT' : 'POST';
    const response = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      return;
    }

    setEditingPropId(null);
    setPropForm({
      device_id: '',
      name: '',
      prop_type: 'Custom',
      location: '',
      status: 'offline',
      battery_level: 100,
      signal_strength: 100,
      last_seen: '',
      firmware_version: '',
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
      status: item.status,
      battery_level: item.battery_level,
      signal_strength: item.signal_strength,
      last_seen: toDateTimeInputValue(item.last_seen),
      firmware_version: item.firmware_version,
    });
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

  async function saveResult() {
    if (!resultForm.session_name.trim()) {
      return;
    }

    const response = await fetch(`${apiBase}/results`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...resultForm,
        red_points: Number(resultForm.red_points) || 0,
        blue_points: Number(resultForm.blue_points) || 0,
        red_penalties: Number(resultForm.red_penalties) || 0,
        blue_penalties: Number(resultForm.blue_penalties) || 0,
      }),
    });

    if (!response.ok) {
      return;
    }

    setResultForm({
      session_name: '',
      winner: 'Draw',
      red_points: 0,
      blue_points: 0,
      red_penalties: 0,
      blue_penalties: 0,
      notes: '',
    });
    fetchResultsData();
  }

  function exportResultsCsv() {
    window.open(`${apiBase}/results/export/csv`, '_blank');
  }

  async function saveScheduleItem() {
    if (!scheduleForm.start_time || !scheduleForm.end_time || !scheduleForm.title.trim()) {
      return;
    }

    const body = {
      title: scheduleForm.title,
      details: scheduleForm.details,
      activity_type: scheduleForm.activity_type,
      start_time: new Date(scheduleForm.start_time).toISOString(),
      end_time: new Date(scheduleForm.end_time).toISOString(),
      is_complete: scheduleForm.is_complete,
    };

    const path = editingScheduleId
      ? `${apiBase}/schedule/items/${editingScheduleId}`
      : `${apiBase}/schedule/items`;
    const method = editingScheduleId ? 'PUT' : 'POST';

    const response = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return;
    }

    setEditingScheduleId(null);
    setScheduleForm({
      title: '',
      details: '',
      activity_type: 'Custom',
      start_time: '',
      end_time: '',
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
      start_time: toDateTimeInputValue(item.start_time),
      end_time: toDateTimeInputValue(item.end_time),
      is_complete: item.is_complete,
    });
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
    fetchMissionState();
    fetchGameModeOptions();
    fetchScheduleData();
    fetchResultsData();
    fetchPropsData();
    fetchSystemLogs();
    fetchSystemStatus();
    fetchUpdateCenterStatus();
  }, [apiBase]);

  useEffect(() => {
    if (selectedApp === 'mission-control') {
      fetchGameModeOptions();
    }
  }, [selectedApp, apiBase]);

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
        const line = `${new Date().toLocaleTimeString()} :: ${JSON.stringify(data)}`;
        setEvents((previous) => [line, ...previous].slice(0, 12));
      } catch {
        const line = `${new Date().toLocaleTimeString()} :: ${message.data}`;
        setEvents((previous) => [line, ...previous].slice(0, 12));
      }
    };

    return () => socket.close();
  }, [wsUrl]);

  const activeApp = APPS.find((app) => app.id === selectedApp) ?? APPS[0];

  const isMissionControl = activeApp.id === 'mission-control';
  const isSchedule = activeApp.id === 'schedule';
  const isResultsBoard = activeApp.id === 'results-board';
  const isPropNetwork = activeApp.id === 'prop-network';
  const isLogs = activeApp.id === 'logs';
  const isSystemMonitor = activeApp.id === 'system-monitor';
  const isAIAssistant = activeApp.id === 'ai-assistant';
  const isUpdateCenter = activeApp.id === 'update-center';
  const isAdminTeams = activeApp.id === 'admin-teams';
  const isAdminGameModes = activeApp.id === 'admin-game-modes';
  const isAdminKnowledge = activeApp.id === 'admin-knowledge';
  const isAdminTheme = activeApp.id === 'admin-theme';
  const isAdminAISettings = activeApp.id === 'admin-ai-settings';

  function handleCreateMission() {
    const objectives = missionForm.objectivesText
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    postMissionAction('/mission-control/mission', {
      title: missionForm.title,
      description: missionForm.description,
      game_mode: missionForm.game_mode,
      main_timer_seconds: Number(missionForm.main_timer_seconds),
      phase_timer_seconds: Number(missionForm.phase_timer_seconds),
      objectives,
    });
  }

  return (
    <div className="desktop-shell">
      <header className="top-bar">
        <div className="brand-block">
          <span className="brand-mark">AOJ</span>
          <div>
            <h1>Command OS</h1>
            <p>Raspberry Pi Tactical Field Console</p>
          </div>
        </div>

        <div className="status-cluster">
          <div className={`indicator net-${networkStatus.toLowerCase()}`}>
            Network {networkStatus}
          </div>
          <div className="indicator">Alerts {alerts}</div>
          <div className="indicator">Devices {deviceCount}</div>
          <div className="clock">{clock.toLocaleTimeString()}</div>
        </div>
      </header>

      <main className="desktop-grid">
        <aside className="launcher">
          <h2>Launcher</h2>
          <nav>
            {APPS.map((app) => (
              <button
                key={app.id}
                className={app.id === selectedApp ? 'launch-btn active' : 'launch-btn'}
                onClick={() => setSelectedApp(app.id)}
                type="button"
              >
                {app.title}
              </button>
            ))}
          </nav>
        </aside>

        <section className="window-stack">
          <article className="window primary-window">
            <div className="window-titlebar">
              <span>{activeApp.title}</span>
              <small>{activeApp.subtitle}</small>
            </div>
            <div className="window-content">
              {isMissionControl ? (
                <section className="mission-control">
                  <div className="mc-grid">
                    <div className="mc-card">
                      <h3>Create Mission</h3>
                      <label>
                        Mission Name
                        <input
                          value={missionForm.title}
                          onChange={(event) =>
                            setMissionForm((current) => ({ ...current, title: event.target.value }))
                          }
                        />
                      </label>
                      <label>
                        Game Mode
                        <select
                          value={missionForm.game_mode}
                          onChange={(event) =>
                            setMissionForm((current) => ({ ...current, game_mode: event.target.value }))
                          }
                        >
                          {gameModeOptions.map((mode) => (
                            <option key={mode} value={mode}>
                              {mode}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Main Timer (seconds)
                        <input
                          type="number"
                          value={missionForm.main_timer_seconds}
                          onChange={(event) =>
                            setMissionForm((current) => ({
                              ...current,
                              main_timer_seconds: event.target.value,
                            }))
                          }
                        />
                      </label>
                      <label>
                        Phase Timer (seconds)
                        <input
                          type="number"
                          value={missionForm.phase_timer_seconds}
                          onChange={(event) =>
                            setMissionForm((current) => ({
                              ...current,
                              phase_timer_seconds: event.target.value,
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
                      <button type="button" onClick={handleCreateMission}>Create Mission</button>
                    </div>

                    <div className="mc-card">
                      <h3>Game Controls</h3>
                      <p className="mc-heading">Mission: {missionState.mission_title}</p>
                      <p className="mc-heading">Mode: {missionState.game_mode}</p>
                      <p className="mc-heading">State: {missionState.state.toUpperCase()}</p>

                      <div className="control-row">
                        <button type="button" onClick={() => postMissionAction('/mission-control/start')}>
                          Start Game
                        </button>
                        <button type="button" onClick={() => postMissionAction('/mission-control/pause')}>
                          Pause Game
                        </button>
                        <button type="button" onClick={() => postMissionAction('/mission-control/resume')}>
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
                          <p>Red Team</p>
                          <strong>{missionState.red_team_score}</strong>
                          <div>
                            <button
                              type="button"
                              onClick={() =>
                                postMissionAction('/mission-control/score', {
                                  team: 'red',
                                  delta: 10,
                                  reason: 'objective',
                                })
                              }
                            >
                              +10
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                postMissionAction('/mission-control/score', {
                                  team: 'red',
                                  delta: -10,
                                  reason: 'penalty',
                                })
                              }
                            >
                              -10
                            </button>
                          </div>
                        </div>
                        <div className="score-card score-blue">
                          <p>Blue Team</p>
                          <strong>{missionState.blue_team_score}</strong>
                          <div>
                            <button
                              type="button"
                              onClick={() =>
                                postMissionAction('/mission-control/score', {
                                  team: 'blue',
                                  delta: 10,
                                  reason: 'objective',
                                })
                              }
                            >
                              +10
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                postMissionAction('/mission-control/score', {
                                  team: 'blue',
                                  delta: -10,
                                  reason: 'penalty',
                                })
                              }
                            >
                              -10
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
                      <label>
                        Start Time
                        <input
                          type="datetime-local"
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
                        End Time
                        <input
                          type="datetime-local"
                          value={scheduleForm.end_time}
                          onChange={(event) =>
                            setScheduleForm((current) => ({
                              ...current,
                              end_time: event.target.value,
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
                              start_time: '',
                              end_time: '',
                              is_complete: false,
                            });
                          }}
                        >
                          Reset
                        </button>
                      </div>
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
                            <span>{item.activity_type}</span>
                          </div>
                          <p className="schedule-meta">
                            {new Date(item.start_time).toLocaleString()} - {new Date(item.end_time).toLocaleString()}
                          </p>
                          <p className="schedule-meta">{item.details || 'No details'}</p>
                          <p className="schedule-meta">Status: {item.is_complete ? 'Complete' : 'Pending'}</p>
                          <div className="schedule-item-actions">
                            <button type="button" onClick={() => editScheduleItem(item)}>Edit</button>
                            <button type="button" onClick={() => completeScheduleItem(item.id)}>
                              Mark Complete
                            </button>
                            <button type="button" onClick={() => deleteScheduleItem(item.id)}>Delete</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              ) : isResultsBoard ? (
                <section className="results-module">
                  <div className="results-grid">
                    <div className="results-card">
                      <h3>Record Game Result</h3>
                      <label>
                        Session Name
                        <input
                          value={resultForm.session_name}
                          onChange={(event) =>
                            setResultForm((current) => ({ ...current, session_name: event.target.value }))
                          }
                        />
                      </label>
                      <label>
                        Winner
                        <select
                          value={resultForm.winner}
                          onChange={(event) =>
                            setResultForm((current) => ({ ...current, winner: event.target.value }))
                          }
                        >
                          {WINNER_OPTIONS.map((winner) => (
                            <option key={winner} value={winner}>
                              {winner}
                            </option>
                          ))}
                        </select>
                      </label>

                      <div className="results-points-grid">
                        <label>
                          Red Points
                          <input
                            type="number"
                            value={resultForm.red_points}
                            onChange={(event) =>
                              setResultForm((current) => ({
                                ...current,
                                red_points: event.target.value,
                              }))
                            }
                          />
                        </label>
                        <label>
                          Blue Points
                          <input
                            type="number"
                            value={resultForm.blue_points}
                            onChange={(event) =>
                              setResultForm((current) => ({
                                ...current,
                                blue_points: event.target.value,
                              }))
                            }
                          />
                        </label>
                        <label>
                          Red Penalties
                          <input
                            type="number"
                            value={resultForm.red_penalties}
                            onChange={(event) =>
                              setResultForm((current) => ({
                                ...current,
                                red_penalties: event.target.value,
                              }))
                            }
                          />
                        </label>
                        <label>
                          Blue Penalties
                          <input
                            type="number"
                            value={resultForm.blue_penalties}
                            onChange={(event) =>
                              setResultForm((current) => ({
                                ...current,
                                blue_penalties: event.target.value,
                              }))
                            }
                          />
                        </label>
                      </div>

                      <label>
                        Notes
                        <textarea
                          value={resultForm.notes}
                          onChange={(event) =>
                            setResultForm((current) => ({ ...current, notes: event.target.value }))
                          }
                        />
                      </label>

                      <div className="results-actions">
                        <button type="button" onClick={saveResult}>Record Result</button>
                        <button type="button" onClick={exportResultsCsv}>Export CSV</button>
                      </div>
                    </div>

                    <div className="results-card">
                      <h3>Totals</h3>
                      <div className="results-summary-grid">
                        <p>Total Red Wins: {resultsSummary.total_red_wins}</p>
                        <p>Total Blue Wins: {resultsSummary.total_blue_wins}</p>
                        <p>Total Draws: {resultsSummary.total_draws}</p>
                        <p>Total Cancelled: {resultsSummary.total_cancelled}</p>
                        <p>Total Red Points: {resultsSummary.total_red_points}</p>
                        <p>Total Blue Points: {resultsSummary.total_blue_points}</p>
                      </div>
                    </div>

                    <div className="results-card results-history-card">
                      <h3>Session History</h3>
                      {resultsHistory.length === 0 ? <p className="muted">No results recorded yet.</p> : null}
                      {resultsHistory.map((result) => (
                        <div className="results-item" key={result.id}>
                          <div className="results-item-header">
                            <strong>{result.session_name}</strong>
                            <span>{result.winner}</span>
                          </div>
                          <p className="results-meta">
                            Red {result.red_points} (penalties {result.red_penalties}) | Blue {result.blue_points} (penalties {result.blue_penalties})
                          </p>
                          <p className="results-meta">Notes: {result.notes || 'No notes'}</p>
                          <p className="results-meta">{new Date(result.created_at).toLocaleString()}</p>
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
                        Status
                        <input
                          value={propForm.status}
                          onChange={(event) =>
                            setPropForm((current) => ({ ...current, status: event.target.value }))
                          }
                        />
                      </label>
                      <div className="prop-input-grid">
                        <label>
                          Battery Level
                          <input
                            type="number"
                            value={propForm.battery_level}
                            onChange={(event) =>
                              setPropForm((current) => ({
                                ...current,
                                battery_level: event.target.value,
                              }))
                            }
                          />
                        </label>
                        <label>
                          Signal Strength
                          <input
                            type="number"
                            value={propForm.signal_strength}
                            onChange={(event) =>
                              setPropForm((current) => ({
                                ...current,
                                signal_strength: event.target.value,
                              }))
                            }
                          />
                        </label>
                      </div>
                      <label>
                        Last Seen
                        <input
                          type="datetime-local"
                          value={propForm.last_seen}
                          onChange={(event) =>
                            setPropForm((current) => ({ ...current, last_seen: event.target.value }))
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
                      <div className="prop-actions">
                        <button type="button" onClick={saveProp}>Save Prop</button>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingPropId(null);
                            setPropForm({
                              device_id: '',
                              name: '',
                              prop_type: 'Custom',
                              location: '',
                              status: 'offline',
                              battery_level: 100,
                              signal_strength: 100,
                              last_seen: '',
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
                            Last Seen:{' '}
                            {item.last_seen ? new Date(item.last_seen).toLocaleString() : 'Never'}
                          </p>
                          <p className="prop-meta">Firmware: {item.firmware_version || 'N/A'}</p>
                          <div className="prop-item-actions">
                            <button type="button" onClick={() => startEditProp(item)}>Edit</button>
                            <button type="button" onClick={() => deleteProp(item.id)}>Delete</button>
                          </div>
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
                    </div>

                    <div className="update-card">
                      <h3>Safe Actions</h3>
                      <label>
                        Offline Update Package Placeholder
                        <input
                          type="file"
                          onChange={(event) => setSelectedUpdatePackage(event.target.files?.[0] ?? null)}
                        />
                      </label>
                      <div className="update-actions">
                        <button
                          type="button"
                          onClick={() =>
                            runUpdateCenterAction('/update-center/upload-placeholder', {
                              filename: selectedUpdatePackage?.name || 'no-file-selected.pkg',
                              size_bytes: selectedUpdatePackage?.size || 0,
                            })
                          }
                        >
                          Upload Placeholder
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
                        Safe mode only. No file replacement or rollback is performed yet.
                      </p>
                      {updateMessage ? <p className="update-status-message">{updateMessage}</p> : null}
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
                            onClick={() => {
                              setAiInput(prompt);
                              askAI(prompt);
                            }}
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                      <p className="ai-safety-note">
                        Advisory-only mode is active. Hardware control requires admin confirmation.
                      </p>
                    </div>

                    <div className="ai-card ai-chat-card">
                      <h3>AI Assistant Chat</h3>
                      <div className="ai-chat-log">
                        {aiMessages.map((item, index) => (
                          <div key={`${item.role}-${index}`} className={`ai-bubble ai-${item.role}`}>
                            <p>{item.text}</p>
                            {item.meta ? <small>{item.meta}</small> : null}
                          </div>
                        ))}
                      </div>

                      <div className="ai-chat-input-row">
                        <textarea
                          value={aiInput}
                          onChange={(event) => setAiInput(event.target.value)}
                          placeholder="Ask for operational advice, summaries, or briefing text..."
                        />
                        <button
                          type="button"
                          onClick={() => {
                            askAI(aiInput);
                            setAiInput('');
                          }}
                        >
                          Send
                        </button>
                      </div>
                    </div>
                  </div>
                </section>
              ) : isAdminTeams ? (
                <AdminCustomTeams apiBase={apiBase} />
              ) : isAdminGameModes ? (
                <AdminGameModes apiBase={apiBase} />
              ) : isAdminKnowledge ? (
                <AdminKnowledgeBase apiBase={apiBase} />
              ) : isAdminTheme ? (
                <AdminThemeEditor apiBase={apiBase} />
              ) : isAdminAISettings ? (
                <AdminAISettings apiBase={apiBase} />
              ) : (
                <ul>
                  {WINDOW_CONTENT[activeApp.id].map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              )}
            </div>
          </article>

          <article className="window aux-window">
            <div className="window-titlebar">
              <span>Live Feed</span>
              <small>WebSocket Stream</small>
            </div>
            <div className="window-content">
              {events.length === 0 ? <p className="muted">Awaiting field telemetry...</p> : null}
              <ul>
                {events.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              <p className="endpoint">Endpoint: {wsUrl}</p>
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}

export default App;
