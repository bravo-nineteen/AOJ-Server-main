import { useEffect, useState } from 'react';

const KNOWLEDGE_CATEGORIES = [
  'Field Rules',
  'AOJ Rules',
  'Safety Procedures',
  'Game Explanations',
  'Team Descriptions',
  'Prop Troubleshooting Notes',
  'Marshal Procedures',
  'Emergency Procedures',
];

export function AdminKnowledgeBase({ apiBase }) {
  const [entries, setEntries] = useState([]);
  const [form, setForm] = useState({
    title: '',
    category: '',
    content: '',
    tags: '',
    active: true,
  });
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchEntries = async () => {
    try {
      setLoading(true);
      const resp = await fetch(`${apiBase}/custom/knowledge`);
      if (resp.ok) {
        setEntries(await resp.json());
      }
    } catch (err) {
      setError(`Fetch failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, [apiBase]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.title.trim()) {
      setError('Title is required');
      return;
    }

    if (!form.content.trim()) {
      setError('Content is required');
      return;
    }

    const tags = form.tags
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t);

    const payload = {
      title: form.title,
      category: form.category,
      content: form.content,
      tags,
      active: form.active,
    };

    try {
      const method = editingId ? 'PUT' : 'POST';
      const url = editingId ? `${apiBase}/custom/knowledge/${editingId}` : `${apiBase}/custom/knowledge`;

      const resp = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        setForm({ title: '', category: '', content: '', tags: '', active: true });
        setEditingId(null);
        await fetchEntries();
      } else {
        setError(`Error: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Submit failed: ${err.message}`);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this knowledge entry?')) return;
    try {
      const resp = await fetch(`${apiBase}/custom/knowledge/${id}`, { method: 'DELETE' });
      if (resp.ok) {
        await fetchEntries();
      } else {
        setError(`Delete failed: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Delete error: ${err.message}`);
    }
  };

  const handleEdit = (entry) => {
    setEditingId(entry.id);
    setForm({
      title: entry.title,
      category: entry.category,
      content: entry.content,
      tags: entry.tags.join(', '),
      active: entry.active,
    });
  };

  return (
    <div style={{ padding: '1rem' }}>
      <h2>Knowledge Base Editor</h2>
      {error && <div style={{ color: 'var(--danger)', padding: '0.5rem' }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ marginBottom: '2rem', border: '1px solid var(--line)', padding: '1rem', borderRadius: '6px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label>Title *</label>
          <input
            type="text"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="e.g., How to reset props"
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Category</label>
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            style={{ width: '100%', padding: '0.5rem' }}
          >
            <option value="">Select a category</option>
            {KNOWLEDGE_CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Content *</label>
          <textarea
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            placeholder="Enter detailed information..."
            style={{ width: '100%', padding: '0.5rem', minHeight: '150px' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Tags (comma-separated)</label>
          <input
            type="text"
            value={form.tags}
            onChange={(e) => setForm({ ...form, tags: e.target.value })}
            placeholder="e.g., safety, marshal, prop, troubleshooting"
            style={{ width: '100%', padding: '0.5rem' }}
          />
          <div style={{ marginTop: '0.35rem', fontSize: '0.82rem', color: 'var(--text-soft)' }}>
            Suggested tags: field-rules, aoj-rules, safety, game-mode, teams, props, marshal, emergency
          </div>
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            Active
          </label>
        </div>
        <button
          type="submit"
          style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--hud)', color: 'black', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {editingId ? 'Update Entry' : 'Add Entry'}
        </button>
        {editingId && (
          <button
            type="button"
            onClick={() => {
              setEditingId(null);
              setForm({ title: '', category: '', content: '', tags: '', active: true });
            }}
            style={{ marginLeft: '0.5rem', padding: '0.5rem 1rem' }}
          >
            Cancel
          </button>
        )}
      </form>

      <div>
        <h3>Knowledge Entries ({entries.length})</h3>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {entries.map((entry) => (
              <div key={entry.id} style={{ border: '1px solid var(--line)', padding: '1rem', borderRadius: '6px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{entry.title}</div>
                    {entry.category && <div style={{ color: 'var(--text-soft)', fontSize: '0.9rem' }}>{entry.category}</div>}
                    <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', lineHeight: '1.4', maxHeight: '60px', overflow: 'hidden' }}>{entry.content}</div>
                    {entry.tags && entry.tags.length > 0 && (
                      <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                        {entry.tags.map((tag) => (
                          <span
                            key={tag}
                            style={{
                              padding: '0.2rem 0.5rem',
                              backgroundColor: 'var(--line)',
                              borderRadius: '3px',
                              fontSize: '0.8rem',
                              color: 'var(--text-soft)',
                            }}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    <div style={{ marginTop: '0.5rem', color: 'var(--text-soft)', fontSize: '0.85rem' }}>Status: {entry.active ? 'Active' : 'Inactive'}</div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '1rem' }}>
                    <button onClick={() => handleEdit(entry)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem' }}>
                      Edit
                    </button>
                    <button onClick={() => handleDelete(entry.id)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem', backgroundColor: 'var(--danger)', color: 'white' }}>
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
