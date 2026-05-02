import { useEffect, useState } from 'react';

export function AdminAISettings({ apiBase }) {
  const [settings, setSettings] = useState({
    enabled: true,
    provider: 'mock',
    model: 'mock-local',
    voice_enabled: false,
    speech_to_text_enabled: false,
    text_to_speech_enabled: false,
    system_personality: 'professional',
    response_style: 'concise',
    max_context_entries: 50,
    safety_mode: 'enforce',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const resp = await fetch(`${apiBase}/ai/settings`);
      if (resp.ok) {
        const data = await resp.json();
        setSettings(data);
      }
    } catch (err) {
      setError(`Fetch failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, [apiBase]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const resp = await fetch(`${apiBase}/ai/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });

      if (resp.ok) {
        setSuccess('Settings saved successfully');
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(`Error: ${resp.statusText}`);
      }
    } catch (err) {
      setError(`Submit failed: ${err.message}`);
    }
  };

  return (
    <div style={{ padding: '1rem' }}>
      <h2>AI Assistant Settings</h2>
      {error && <div style={{ color: 'var(--danger)', padding: '0.5rem', marginBottom: '1rem' }}>{error}</div>}
      {success && <div style={{ color: 'var(--hud)', padding: '0.5rem', marginBottom: '1rem' }}>{success}</div>}

      <form onSubmit={handleSubmit} style={{ border: '1px solid var(--line)', padding: '1.5rem', borderRadius: '6px' }}>
        <div style={{ marginBottom: '2rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--line)' }}>
          <h3>Enable/Disable</h3>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={settings.enabled}
                onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
                style={{ width: '20px', height: '20px' }}
              />
              <span>Enable AI Assistant</span>
            </label>
            <p style={{ marginTop: '0.5rem', color: 'var(--text-soft)', fontSize: '0.9rem' }}>When disabled, all AI features are unavailable.</p>
          </div>
        </div>

        <div style={{ marginBottom: '2rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--line)' }}>
          <h3>Voice Input/Output</h3>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={settings.voice_enabled}
                onChange={(e) => setSettings({ ...settings, voice_enabled: e.target.checked })}
                style={{ width: '20px', height: '20px' }}
              />
              <span>Enable Voice Features</span>
            </label>
            <p style={{ marginTop: '0.5rem', color: 'var(--text-soft)', fontSize: '0.9rem' }}>Enable all voice-related capabilities.</p>
          </div>

          <div style={{ marginBottom: '1rem', paddingLeft: '1.5rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={settings.speech_to_text_enabled}
                onChange={(e) => setSettings({ ...settings, speech_to_text_enabled: e.target.checked })}
                disabled={!settings.voice_enabled}
                style={{ width: '20px', height: '20px' }}
              />
              <span>Enable Voice Input (Speech-to-Text)</span>
            </label>
            <p style={{ marginTop: '0.3rem', color: 'var(--text-soft)', fontSize: '0.85rem', paddingLeft: '1.5rem' }}>Users can speak commands and questions to the AI.</p>
          </div>

          <div style={{ marginBottom: '1rem', paddingLeft: '1.5rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={settings.text_to_speech_enabled}
                onChange={(e) => setSettings({ ...settings, text_to_speech_enabled: e.target.checked })}
                disabled={!settings.voice_enabled}
                style={{ width: '20px', height: '20px' }}
              />
              <span>Enable Voice Output (Text-to-Speech)</span>
            </label>
            <p style={{ marginTop: '0.3rem', color: 'var(--text-soft)', fontSize: '0.85rem', paddingLeft: '1.5rem' }}>AI responses are read aloud to the user.</p>
          </div>
        </div>

        <div style={{ marginBottom: '2rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--line)' }}>
          <h3>Behavior Settings</h3>
          <div style={{ marginBottom: '1rem' }}>
            <label>System Personality</label>
            <select
              value={settings.system_personality}
              onChange={(e) => setSettings({ ...settings, system_personality: e.target.value })}
              style={{ width: '100%', padding: '0.5rem' }}
            >
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="technical">Technical</option>
              <option value="friendly">Friendly</option>
            </select>
            <p style={{ marginTop: '0.3rem', color: 'var(--text-soft)', fontSize: '0.85rem' }}>How the AI presents itself to users.</p>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label>Response Style</label>
            <select
              value={settings.response_style}
              onChange={(e) => setSettings({ ...settings, response_style: e.target.value })}
              style={{ width: '100%', padding: '0.5rem' }}
            >
              <option value="concise">Concise</option>
              <option value="detailed">Detailed</option>
              <option value="balanced">Balanced</option>
            </select>
            <p style={{ marginTop: '0.3rem', color: 'var(--text-soft)', fontSize: '0.85rem' }}>How verbose AI responses should be.</p>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label>Safety Mode</label>
            <select
              value={settings.safety_mode}
              onChange={(e) => setSettings({ ...settings, safety_mode: e.target.value })}
              style={{ width: '100%', padding: '0.5rem' }}
            >
              <option value="strict">Strict</option>
              <option value="enforce">Enforce (default)</option>
              <option value="advisory">Advisory Only</option>
            </select>
            <p style={{ marginTop: '0.3rem', color: 'var(--text-soft)', fontSize: '0.85rem' }}>How strictly the AI enforces safety policies.</p>
          </div>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label>Max Context Entries</label>
          <input
            type="number"
            value={settings.max_context_entries}
            onChange={(e) => setSettings({ ...settings, max_context_entries: parseInt(e.target.value) || 50 })}
            min="1"
            max="500"
            style={{ width: '100%', padding: '0.5rem' }}
          />
          <p style={{ marginTop: '0.3rem', color: 'var(--text-soft)', fontSize: '0.85rem' }}>Maximum number of knowledge base entries to include in AI context (1-500).</p>
        </div>

        <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
          <button
            type="submit"
            style={{
              padding: '0.7rem 1.5rem',
              backgroundColor: 'var(--hud)',
              color: 'black',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            Save Settings
          </button>
          <button
            type="button"
            onClick={fetchSettings}
            style={{
              padding: '0.7rem 1.5rem',
              backgroundColor: 'transparent',
              color: 'var(--text-main)',
              border: '1px solid var(--line)',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Reload
          </button>
        </div>
      </form>

      <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: 'var(--ink-1)', borderRadius: '6px', border: '1px solid var(--line)' }}>
        <h3>Settings Info</h3>
        <div style={{ fontSize: '0.9rem', color: 'var(--text-soft)', lineHeight: '1.6' }}>
          <div>
            <strong>Provider:</strong> {settings.provider}
          </div>
          <div>
            <strong>Model:</strong> {settings.model}
          </div>
          <div>
            <strong>Current Status:</strong> {settings.enabled ? 'Enabled' : 'Disabled'}
          </div>
          {settings.voice_enabled && (
            <>
              <div>
                <strong>Voice Input:</strong> {settings.speech_to_text_enabled ? 'Enabled' : 'Disabled'}
              </div>
              <div>
                <strong>Voice Output:</strong> {settings.text_to_speech_enabled ? 'Enabled' : 'Disabled'}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
