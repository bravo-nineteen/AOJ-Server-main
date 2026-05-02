import { useEffect, useState } from 'react';

export function AdminCustomTeams({ apiBase }) {
  const [teams, setTeams] = useState([]);
  const [form, setForm] = useState({ name: '', short_name: '', color: '#ffffff', icon: '', description: '', active: true });
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchTeams = async () => {
    try {
      setLoading(true);
      const resp = await fetch(`${apiBase}/custom/teams`);
      if (resp.ok) {
        setTeams(await resp.json());
      }
    } catch (err) {
      setError(`Fetch failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, [apiBase]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!form.name.trim()) {
      setError('Team name is required');
      return;
    }

    try {
      const method = editingId ? 'PUT' : 'POST';
      const url = editingId ? `${apiBase}/custom/teams/${editingId}` : `${apiBase}/custom/teams`;
      
      const resp = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (resp.ok) {
        setForm({ name: '', short_name: '', color: '#ffffff', icon: '', description: '', active: true });
        setEditingId(null);
        await fetchTeams();
      } else {
        setError(`Error: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Submit failed: ${err.message}`);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this team?')) return;
    try {
      const resp = await fetch(`${apiBase}/custom/teams/${id}`, { method: 'DELETE' });
      if (resp.ok) {
        await fetchTeams();
      } else {
        setError(`Delete failed: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Delete error: ${err.message}`);
    }
  };

  const handleEdit = (team) => {
    setEditingId(team.id);
    setForm({
      name: team.name,
      short_name: team.short_name,
      color: team.color,
      icon: team.icon,
      description: team.description,
      active: team.active,
    });
  };

  return (
    <div style={{ padding: '1rem' }}>
      <h2>Team Editor</h2>
      {error && <div style={{ color: 'var(--danger)', padding: '0.5rem' }}>{error}</div>}
      
      <form onSubmit={handleSubmit} style={{ marginBottom: '2rem', border: '1px solid var(--line)', padding: '1rem', borderRadius: '6px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label>Team Name *</label>
          <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={{ width: '100%', padding: '0.5rem' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Short Name</label>
          <input type="text" value={form.short_name} onChange={(e) => setForm({ ...form, short_name: e.target.value })} placeholder="e.g., RED" style={{ width: '100%', padding: '0.5rem' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Color</label>
          <input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} style={{ width: '60px', height: '40px' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Icon URL</label>
          <input type="text" value={form.icon} onChange={(e) => setForm({ ...form, icon: e.target.value })} style={{ width: '100%', padding: '0.5rem' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Description</label>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} style={{ width: '100%', padding: '0.5rem', minHeight: '80px' }} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            Active
          </label>
        </div>
        <button type="submit" style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--hud)', color: 'black', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          {editingId ? 'Update Team' : 'Add Team'}
        </button>
        {editingId && (
          <button type="button" onClick={() => { setEditingId(null); setForm({ name: '', short_name: '', color: '#ffffff', icon: '', description: '', active: true }); }} style={{ marginLeft: '0.5rem', padding: '0.5rem 1rem' }}>
            Cancel
          </button>
        )}
      </form>

      <div>
        <h3>Teams ({teams.length})</h3>
        {loading ? <p>Loading...</p> : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {teams.map((team) => (
              <div key={team.id} style={{ border: '1px solid var(--line)', padding: '1rem', borderRadius: '6px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <div style={{ color: team.color, fontSize: '1.1rem', fontWeight: 'bold' }}>{team.name}</div>
                    {team.short_name && <div style={{ color: 'var(--text-soft)', fontSize: '0.9rem' }}>{team.short_name}</div>}
                    {team.description && <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>{team.description}</div>}
                    <div style={{ marginTop: '0.5rem', color: 'var(--text-soft)', fontSize: '0.85rem' }}>Status: {team.active ? 'Active' : 'Inactive'}</div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button onClick={() => handleEdit(team)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem' }}>Edit</button>
                    <button onClick={() => handleDelete(team.id)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem', backgroundColor: 'var(--danger)', color: 'white' }}>Delete</button>
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
