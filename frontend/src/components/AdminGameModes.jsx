import { useEffect, useState } from 'react';

export function AdminGameModes({ apiBase }) {
  const [modes, setModes] = useState([]);
  const [form, setForm] = useState({
    name: '',
    category: '',
    description: '',
    default_duration_minutes: 20,
    team_setup_team_count: 2,
    team_setup_team_names: 'Red Team, Blue Team',
    objectives_text: '',
    scoring_rules_text: '',
    win_conditions_text: '',
    required_props_text: '',
    scoring_rules_json: {},
    objective_rules_json: {},
    respawn_rules_text: '',
    briefing_text: '',
    marshal_notes: '',
    active: true,
  });
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchModes = async () => {
    try {
      setLoading(true);
      const resp = await fetch(`${apiBase}/custom/game-modes`);
      if (resp.ok) {
        setModes(await resp.json());
      }
    } catch (err) {
      setError(`Fetch failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModes();
  }, [apiBase]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.name.trim()) {
      setError('Game mode name is required');
      return;
    }

    const normalizeLineList = (raw) =>
      raw
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);

    const objectives = normalizeLineList(form.objectives_text);
    const winConditions = normalizeLineList(form.win_conditions_text);
    const requiredProps = normalizeLineList(form.required_props_text);

    const scoringRules = {};
    for (const line of normalizeLineList(form.scoring_rules_text)) {
      const [left, ...rest] = line.split('=');
      const eventName = (left || '').trim();
      const pointsRaw = rest.join('=').trim();
      if (!eventName || !pointsRaw) {
        continue;
      }
      const points = Number(pointsRaw);
      if (!Number.isFinite(points)) {
        setError(`Invalid scoring rule: "${line}". Use format Event = Points`);
        return;
      }
      scoringRules[eventName] = points;
    }

    const teamNames = form.team_setup_team_names
      .split(',')
      .map((name) => name.trim())
      .filter(Boolean);

    const teamSetup = {
      team_count: Number(form.team_setup_team_count) || 2,
      team_names: teamNames,
    };

    const payload = {
      name: form.name,
      category: form.category,
      description: form.description,
      rules_text: form.description,
      default_duration_minutes: Number(form.default_duration_minutes) || 20,
      team_setup_json: teamSetup,
      objectives_json: objectives,
      scoring_rules_json: scoringRules,
      objective_rules_json: {},
      respawn_rules_text: form.respawn_rules_text,
      win_conditions_json: winConditions,
      required_props_json: requiredProps,
      briefing_text: form.briefing_text,
      marshal_notes: form.marshal_notes,
      active: form.active,
    };

    try {
      const method = editingId ? 'PUT' : 'POST';
      const url = editingId ? `${apiBase}/custom/game-modes/${editingId}` : `${apiBase}/custom/game-modes`;

      const resp = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        setForm({
          name: '',
          category: '',
          description: '',
          default_duration_minutes: 20,
          team_setup_team_count: 2,
          team_setup_team_names: 'Red Team, Blue Team',
          objectives_text: '',
          scoring_rules_text: '',
          win_conditions_text: '',
          required_props_text: '',
          scoring_rules_json: {},
          objective_rules_json: {},
          respawn_rules_text: '',
          briefing_text: '',
          marshal_notes: '',
          active: true,
        });
        setEditingId(null);
        await fetchModes();
        window.dispatchEvent(new CustomEvent('custom-data-changed', { detail: { type: 'game-modes' } }));
      } else {
        setError(`Error: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Submit failed: ${err.message}`);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this game mode?')) return;
    try {
      const resp = await fetch(`${apiBase}/custom/game-modes/${id}`, { method: 'DELETE' });
      if (resp.ok) {
        await fetchModes();
        window.dispatchEvent(new CustomEvent('custom-data-changed', { detail: { type: 'game-modes' } }));
      } else {
        setError(`Delete failed: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Delete error: ${err.message}`);
    }
  };

  const handleEdit = (mode) => {
    const teamSetup = mode.team_setup_json || {};
    const teamNames = Array.isArray(teamSetup.team_names) ? teamSetup.team_names.join(', ') : '';
    const objectives = Array.isArray(mode.objectives_json) ? mode.objectives_json.join('\n') : '';
    const winConditions = Array.isArray(mode.win_conditions_json)
      ? mode.win_conditions_json.join('\n')
      : '';
    const requiredProps = Array.isArray(mode.required_props_json)
      ? mode.required_props_json.join('\n')
      : '';
    const scoringLines = Object.entries(mode.scoring_rules_json || {})
      .map(([eventName, points]) => `${eventName} = ${points}`)
      .join('\n');

    setEditingId(mode.id);
    setForm({
      name: mode.name,
      category: mode.category,
      description: mode.description,
      default_duration_minutes: mode.default_duration_minutes,
      team_setup_team_count: Number(teamSetup.team_count) || 2,
      team_setup_team_names: teamNames,
      objectives_text: objectives,
      scoring_rules_text: scoringLines,
      win_conditions_text: winConditions,
      required_props_text: requiredProps,
      scoring_rules_json: mode.scoring_rules_json,
      objective_rules_json: mode.objective_rules_json,
      respawn_rules_text: mode.respawn_rules_text,
      briefing_text: mode.briefing_text || '',
      marshal_notes: mode.marshal_notes || '',
      active: mode.active,
    });
  };

  return (
    <div style={{ padding: '1rem' }}>
      <h2>Game Mode Editor</h2>
      {error && <div style={{ color: 'var(--danger)', padding: '0.5rem' }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ marginBottom: '2rem', border: '1px solid var(--line)', padding: '1rem', borderRadius: '6px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label>Game Mode Name *</label>
          <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={{ width: '100%', padding: '0.5rem' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Category</label>
          <input type="text" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="e.g., Competitive, Training" style={{ width: '100%', padding: '0.5rem' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Description</label>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} style={{ width: '100%', padding: '0.5rem', minHeight: '70px' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Default Duration (minutes)</label>
          <input type="number" value={form.default_duration_minutes} onChange={(e) => setForm({ ...form, default_duration_minutes: parseInt(e.target.value) || 20 })} min="1" style={{ width: '100%', padding: '0.5rem' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Team Setup: Team Count</label>
          <input
            type="number"
            value={form.team_setup_team_count}
            onChange={(e) => setForm({ ...form, team_setup_team_count: parseInt(e.target.value) || 2 })}
            min="1"
            max="16"
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Team Setup: Team Names (comma separated)</label>
          <input
            type="text"
            value={form.team_setup_team_names}
            onChange={(e) => setForm({ ...form, team_setup_team_names: e.target.value })}
            placeholder="Red Team, Blue Team"
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Objectives (one per line)</label>
          <textarea
            value={form.objectives_text}
            onChange={(e) => setForm({ ...form, objectives_text: e.target.value })}
            placeholder={"Capture relay\nHold command post\nExtract VIP"}
            style={{ width: '100%', padding: '0.5rem', minHeight: '90px' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Scoring Rules (one per line: Event = Points)</label>
          <textarea
            value={form.scoring_rules_text}
            onChange={(e) => setForm({ ...form, scoring_rules_text: e.target.value })}
            placeholder={"Objective captured = 100\nElimination = 10\nPenalty = -25"}
            style={{ width: '100%', padding: '0.5rem', minHeight: '90px' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Respawn Rules</label>
          <textarea value={form.respawn_rules_text} onChange={(e) => setForm({ ...form, respawn_rules_text: e.target.value })} style={{ width: '100%', padding: '0.5rem', minHeight: '60px' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Win Conditions (one per line)</label>
          <textarea
            value={form.win_conditions_text}
            onChange={(e) => setForm({ ...form, win_conditions_text: e.target.value })}
            placeholder={"First to 500 points\nMost objectives completed by timeout"}
            style={{ width: '100%', padding: '0.5rem', minHeight: '80px' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Required Props (one per line)</label>
          <textarea
            value={form.required_props_text}
            onChange={(e) => setForm({ ...form, required_props_text: e.target.value })}
            placeholder={"Bomb prop\nCapture point beacon\nRespawn station"}
            style={{ width: '100%', padding: '0.5rem', minHeight: '80px' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Briefing Text</label>
          <textarea
            value={form.briefing_text}
            onChange={(e) => setForm({ ...form, briefing_text: e.target.value })}
            style={{ width: '100%', padding: '0.5rem', minHeight: '120px' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Marshal Notes</label>
          <textarea
            value={form.marshal_notes}
            onChange={(e) => setForm({ ...form, marshal_notes: e.target.value })}
            style={{ width: '100%', padding: '0.5rem', minHeight: '120px' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            Active
          </label>
        </div>
        <button type="submit" style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--hud)', color: 'black', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          {editingId ? 'Update Mode' : 'Add Mode'}
        </button>
        {editingId && (
          <button type="button" onClick={() => { setEditingId(null); setForm({ name: '', category: '', description: '', default_duration_minutes: 20, team_setup_team_count: 2, team_setup_team_names: 'Red Team, Blue Team', objectives_text: '', scoring_rules_text: '', win_conditions_text: '', required_props_text: '', scoring_rules_json: {}, objective_rules_json: {}, respawn_rules_text: '', briefing_text: '', marshal_notes: '', active: true }); }} style={{ marginLeft: '0.5rem', padding: '0.5rem 1rem' }}>
            Cancel
          </button>
        )}
      </form>

      <div>
        <h3>Game Modes ({modes.length})</h3>
        {loading ? <p>Loading...</p> : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {modes.map((mode) => (
              <div key={mode.id} style={{ border: '1px solid var(--line)', padding: '1rem', borderRadius: '6px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>{mode.name}</div>
                    {mode.category && <div style={{ color: 'var(--text-soft)', fontSize: '0.9rem' }}>Category: {mode.category}</div>}
                    {mode.description && <div style={{ marginTop: '0.3rem', fontSize: '0.9rem' }}>{mode.description}</div>}
                    {Array.isArray(mode.objectives_json) && mode.objectives_json.length > 0 ? (
                      <div style={{ marginTop: '0.4rem', fontSize: '0.85rem', color: 'var(--text-soft)' }}>
                        Objectives: {mode.objectives_json.length}
                      </div>
                    ) : null}
                    {Array.isArray(mode.win_conditions_json) && mode.win_conditions_json.length > 0 ? (
                      <div style={{ marginTop: '0.1rem', fontSize: '0.85rem', color: 'var(--text-soft)' }}>
                        Win Conditions: {mode.win_conditions_json.length}
                      </div>
                    ) : null}
                    <div style={{ marginTop: '0.5rem', color: 'var(--text-soft)', fontSize: '0.85rem' }}>Duration: {mode.default_duration_minutes} min • Status: {mode.active ? 'Active' : 'Inactive'}</div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button onClick={() => handleEdit(mode)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem' }}>Edit</button>
                    <button onClick={() => handleDelete(mode.id)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem', backgroundColor: 'var(--danger)', color: 'white' }}>Delete</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
