import { useEffect, useState } from 'react';

export function AdminThemeEditor({ apiBase }) {
  const [themes, setThemes] = useState([]);
  const [form, setForm] = useState({
    name: '',
    primary_color: '#000000',
    secondary_color: '#ffffff',
    accent_color: '#ff0000',
    background_color: '#1a1a1a',
    panel_color: '#2a2a2a',
    text_color: '#ffffff',
    warning_color: '#ffaa00',
    danger_color: '#ff3333',
    success_color: '#00ff00',
    font_family: 'Arial, sans-serif',
    border_radius: '4px',
    density: 'normal',
    background_style: 'solid',
    logo_url: '',
  });
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchThemes = async () => {
    try {
      setLoading(true);
      const resp = await fetch(`${apiBase}/custom/themes`);
      if (resp.ok) {
        setThemes(await resp.json());
      }
    } catch (err) {
      setError(`Fetch failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchThemes();
  }, [apiBase]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.name.trim()) {
      setError('Theme name is required');
      return;
    }

    try {
      const method = editingId ? 'PUT' : 'POST';
      const url = editingId ? `${apiBase}/custom/themes/${editingId}` : `${apiBase}/custom/themes`;

      const resp = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (resp.ok) {
        resetForm();
        setEditingId(null);
        await fetchThemes();
        window.dispatchEvent(new CustomEvent('custom-data-changed', { detail: { type: 'theme' } }));
      } else {
        setError(`Error: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Submit failed: ${err.message}`);
    }
  };

  const handleSetActive = async (id) => {
    try {
      const resp = await fetch(`${apiBase}/custom/themes/active`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme_id: id }),
      });

      if (resp.ok) {
        await fetchThemes();
        window.dispatchEvent(new CustomEvent('custom-data-changed', { detail: { type: 'theme' } }));
      } else {
        setError(`Failed to set active theme: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this theme?')) return;
    try {
      const resp = await fetch(`${apiBase}/custom/themes/${id}`, { method: 'DELETE' });
      if (resp.ok) {
        await fetchThemes();
        window.dispatchEvent(new CustomEvent('custom-data-changed', { detail: { type: 'theme' } }));
      } else {
        setError(`Delete failed: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Delete error: ${err.message}`);
    }
  };

  const handleEdit = (theme) => {
    setEditingId(theme.id);
    setForm({
      name: theme.name,
      primary_color: theme.primary_color,
      secondary_color: theme.secondary_color,
      accent_color: theme.accent_color,
      background_color: theme.background_color,
      panel_color: theme.panel_color,
      text_color: theme.text_color,
      warning_color: theme.warning_color,
      danger_color: theme.danger_color,
      success_color: theme.success_color,
      font_family: theme.font_family,
      border_radius: theme.border_radius,
      density: theme.density,
      background_style: theme.background_style,
      logo_url: theme.logo_url,
    });
  };

  const resetForm = () => {
    setForm({
      name: '',
      primary_color: '#000000',
      secondary_color: '#ffffff',
      accent_color: '#ff0000',
      background_color: '#1a1a1a',
      panel_color: '#2a2a2a',
      text_color: '#ffffff',
      warning_color: '#ffaa00',
      danger_color: '#ff3333',
      success_color: '#00ff00',
      font_family: 'Arial, sans-serif',
      border_radius: '4px',
      density: 'normal',
      background_style: 'solid',
      logo_url: '',
    });
  };

  return (
    <div style={{ padding: '1rem' }}>
      <h2>Theme Editor</h2>
      {error && <div style={{ color: 'var(--danger)', padding: '0.5rem' }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ marginBottom: '2rem', border: '1px solid var(--line)', padding: '1rem', borderRadius: '6px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label>Theme Name *</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g., Dark Mode, Light Mode"
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>

        <div style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: 'var(--ink-1)', borderRadius: '4px' }}>
          <h4>Colors</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
            {['primary_color', 'secondary_color', 'accent_color', 'background_color', 'panel_color', 'text_color', 'warning_color', 'danger_color', 'success_color'].map((key) => (
              <div key={key}>
                <label style={{ display: 'block', marginBottom: '0.3rem', fontSize: '0.9rem' }}>
                  {key.replace(/_color$/, '').replace(/_/g, ' ')}
                </label>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <input
                    type="color"
                    value={form[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    style={{ width: '50px', height: '40px', cursor: 'pointer' }}
                  />
                  <input
                    type="text"
                    value={form[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    style={{ flex: 1, padding: '0.3rem', fontSize: '0.85rem' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: 'var(--ink-1)', borderRadius: '4px' }}>
          <h4>Typography & Layout</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div>
              <label>Font Family</label>
              <input
                type="text"
                value={form.font_family}
                onChange={(e) => setForm({ ...form, font_family: e.target.value })}
                placeholder="e.g., Arial, sans-serif"
                style={{ width: '100%', padding: '0.5rem' }}
              />
            </div>
            <div>
              <label>Border Radius</label>
              <input
                type="text"
                value={form.border_radius}
                onChange={(e) => setForm({ ...form, border_radius: e.target.value })}
                placeholder="e.g., 4px, 8px"
                style={{ width: '100%', padding: '0.5rem' }}
              />
            </div>
            <div>
              <label>Density</label>
              <select
                value={form.density}
                onChange={(e) => setForm({ ...form, density: e.target.value })}
                style={{ width: '100%', padding: '0.5rem' }}
              >
                <option value="compact">Compact</option>
                <option value="normal">Normal</option>
                <option value="spacious">Spacious</option>
              </select>
            </div>
            <div>
              <label>Background Style</label>
              <select
                value={form.background_style}
                onChange={(e) => setForm({ ...form, background_style: e.target.value })}
                style={{ width: '100%', padding: '0.5rem' }}
              >
                <option value="solid">Solid</option>
                <option value="gradient">Gradient</option>
                <option value="pattern">Pattern</option>
              </select>
            </div>
          </div>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label>Logo URL</label>
          <input
            type="text"
            value={form.logo_url}
            onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
            placeholder="e.g., /logo.png"
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>

        <button
          type="submit"
          style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--hud)', color: 'black', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {editingId ? 'Update Theme' : 'Add Theme'}
        </button>
        {editingId && (
          <button
            type="button"
            onClick={() => {
              setEditingId(null);
              resetForm();
            }}
            style={{ marginLeft: '0.5rem', padding: '0.5rem 1rem' }}
          >
            Cancel
          </button>
        )}
      </form>

      <div>
        <h3>Themes ({themes.length})</h3>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {themes.map((theme) => (
              <div
                key={theme.id}
                style={{
                  border: theme.is_active ? '2px solid var(--hud)' : '1px solid var(--line)',
                  padding: '1rem',
                  borderRadius: '6px',
                  backgroundColor: theme.is_active ? 'rgba(182, 247, 132, 0.05)' : 'transparent',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
                      {theme.name}
                      {theme.is_active && <span style={{ marginLeft: '0.5rem', color: 'var(--hud)', fontSize: '0.9rem' }}>[ACTIVE]</span>}
                    </div>
                    <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <div
                        style={{
                          width: '24px',
                          height: '24px',
                          backgroundColor: theme.primary_color,
                          border: '1px solid var(--line)',
                          borderRadius: '4px',
                          title: 'Primary',
                        }}
                      />
                      <div style={{ width: '24px', height: '24px', backgroundColor: theme.secondary_color, border: '1px solid var(--line)', borderRadius: '4px' }} />
                      <div style={{ width: '24px', height: '24px', backgroundColor: theme.accent_color, border: '1px solid var(--line)', borderRadius: '4px' }} />
                      <div style={{ width: '24px', height: '24px', backgroundColor: theme.background_color, border: '1px solid var(--line)', borderRadius: '4px' }} />
                      <div style={{ width: '24px', height: '24px', backgroundColor: theme.panel_color, border: '1px solid var(--line)', borderRadius: '4px' }} />
                      <div style={{ width: '24px', height: '24px', backgroundColor: theme.warning_color, border: '1px solid var(--line)', borderRadius: '4px' }} />
                      <div style={{ width: '24px', height: '24px', backgroundColor: theme.danger_color, border: '1px solid var(--line)', borderRadius: '4px' }} />
                      <div style={{ width: '24px', height: '24px', backgroundColor: theme.success_color, border: '1px solid var(--line)', borderRadius: '4px' }} />
                    </div>
                    <div style={{ marginTop: '0.5rem', color: 'var(--text-soft)', fontSize: '0.85rem' }}>
                      {theme.font_family} • {theme.density} • {theme.background_style}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '1rem' }}>
                    {!theme.is_active && (
                      <button
                        onClick={() => handleSetActive(theme.id)}
                        style={{
                          padding: '0.4rem 0.8rem',
                          fontSize: '0.9rem',
                          backgroundColor: 'var(--line-bright)',
                          color: 'black',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                        }}
                      >
                        Set Active
                      </button>
                    )}
                    <button onClick={() => handleEdit(theme)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem' }}>
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(theme.id)}
                      style={{
                        padding: '0.4rem 0.8rem',
                        fontSize: '0.9rem',
                        backgroundColor: 'var(--danger)',
                        color: 'white',
                      }}
                    >
                      Delete
                    </button>
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
