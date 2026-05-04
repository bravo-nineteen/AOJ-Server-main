import { useEffect, useState } from 'react';

export function AdminCustomTeams({ apiBase }) {
  const [teams, setTeams] = useState([]);
  const [form, setForm] = useState({ name: '', short_name: '', color: '#ffffff', icon: '', description: '', active: true });
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState('');

  const resolveLogoUrl = (icon) => {
    if (!icon) {
      return '';
    }
    if (icon.startsWith('http://') || icon.startsWith('https://') || icon.startsWith('data:')) {
      return icon;
    }
    const origin = apiBase.endsWith('/api') ? apiBase.slice(0, -4) : apiBase;
    if (icon.startsWith('/')) {
      return `${origin}${icon}`;
    }
    return `${origin}/${icon}`;
  };

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
        window.dispatchEvent(new CustomEvent('custom-data-changed', { detail: { type: 'teams' } }));
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
        window.dispatchEvent(new CustomEvent('custom-data-changed', { detail: { type: 'teams' } }));
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

  const toSquareBlob = (file) => new Promise((resolve, reject) => {
    const img = new Image();
    const reader = new FileReader();

    reader.onload = () => {
      img.src = reader.result;
    };
    reader.onerror = () => reject(new Error('Image read failed'));
    reader.readAsDataURL(file);

    img.onload = () => {
      const side = Math.min(img.width, img.height);
      const sx = Math.floor((img.width - side) / 2);
      const sy = Math.floor((img.height - side) / 2);

      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 256;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Canvas unsupported'));
        return;
      }
      ctx.drawImage(img, sx, sy, side, side, 0, 0, 256, 256);
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error('Image crop failed'));
          return;
        }
        resolve(blob);
      }, 'image/png', 0.95);
    };

    img.onerror = () => reject(new Error('Invalid image file'));
  });

  const uploadLogoFile = async (selectedFile) => {
    if (!selectedFile) {
      return;
    }

    setError('');
    setUploadingLogo(true);
    try {
      const croppedBlob = await toSquareBlob(selectedFile);
      const formData = new FormData();
      formData.append('file', croppedBlob, 'team_logo.png');
      const resp = await fetch(`${apiBase}/custom/teams/logo-upload`, {
        method: 'POST',
        body: formData,
      });

      if (!resp.ok) {
        throw new Error(`Upload failed (${resp.status})`);
      }

      const payload = await resp.json();
      setForm((current) => ({ ...current, icon: payload.url || '' }));
    } catch (err) {
      setError(`Logo upload failed: ${err.message}`);
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleLogoUpload = async (event) => {
    const selectedFile = event.target.files?.[0];
    await uploadLogoFile(selectedFile);
    event.target.value = '';
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
          <label>Team Logo</label>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={async (e) => {
              e.preventDefault();
              setDragOver(false);
              const dropped = e.dataTransfer?.files?.[0];
              await uploadLogoFile(dropped);
            }}
            style={{
              border: dragOver ? '1px solid var(--line-bright)' : '1px dashed var(--line)',
              borderRadius: '6px',
              padding: '0.7rem',
              marginBottom: '0.4rem',
              background: dragOver ? 'rgba(182,247,132,0.08)' : 'rgba(255,255,255,0.02)',
              fontSize: '0.82rem',
            }}
          >
            Drag and drop a logo image here (auto center-cropped to square), or use file picker below.
          </div>
          <input type="file" accept="image/*" onChange={handleLogoUpload} style={{ width: '100%', padding: '0.5rem' }} />
          <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {form.icon ? (
              <img
                src={resolveLogoUrl(form.icon)}
                alt="Team logo preview"
                style={{ width: '42px', height: '42px', borderRadius: '8px', objectFit: 'cover', border: '1px solid var(--line)' }}
              />
            ) : (
              <span
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '999px',
                  backgroundColor: form.color,
                  border: '1px solid var(--line)',
                  display: 'inline-block',
                }}
              />
            )}
            <input
              type="text"
              value={form.icon}
              placeholder="Logo URL (optional)"
              onChange={(e) => setForm({ ...form, icon: e.target.value })}
              style={{ width: '100%', padding: '0.5rem' }}
            />
          </div>
          <div style={{ marginTop: '0.3rem', fontSize: '0.8rem', color: 'var(--text-soft)' }}>
            {uploadingLogo ? 'Uploading logo...' : 'If no logo is set, team color will be used.'}
          </div>
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
                    <div style={{ marginTop: '0.35rem' }}>
                      {team.icon ? (
                        <img
                          src={resolveLogoUrl(team.icon)}
                          alt={`${team.name} logo`}
                          style={{ width: '36px', height: '36px', borderRadius: '8px', objectFit: 'cover', border: '1px solid var(--line)' }}
                        />
                      ) : (
                        <span
                          style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '999px',
                            backgroundColor: team.color,
                            border: '1px solid var(--line)',
                            display: 'inline-block',
                          }}
                          title={`${team.name} color token`}
                        />
                      )}
                    </div>
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
