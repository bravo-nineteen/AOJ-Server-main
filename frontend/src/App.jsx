import { useEffect, useMemo, useState } from 'react';

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

const GAME_MODES = ['Skirmish', 'Domination', 'Capture Point', 'Hostage Rescue'];
const ACTIVITY_TYPES = [
  'Safety Brief',
  'Game',
  'Break',
  'Lunch',
  'Setup',
  'Pack Down',
  'Custom',
];

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
  const [missionState, setMissionState] = useState(DEFAULT_MISSION_STATE);
  const [missionForm, setMissionForm] = useState({
    title: 'Operation Echo',
    description: 'Field objective sequence for Sector Echo.',
    game_mode: GAME_MODES[0],
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

  async function fetchMissionState() {
    const response = await fetch(`${apiBase}/mission-control/state`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setMissionState(payload);
    setEvents(payload.event_feed ?? []);
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
    fetchMissionState();
    fetchScheduleData();
  }, [apiBase]);

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
                          {GAME_MODES.map((mode) => (
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
