chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'analyzeResults') {
    const payload = message.payload || {};
    (async () => {
      try {
        const res = await fetch('http://127.0.0.1:5002/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          sendResponse({ ok: false, error: `HTTP ${res.status}` });
          return;
        }
        const data = await res.json();
        sendResponse({ ok: true, data });
      } catch (e) {
        sendResponse({ ok: false, error: e?.message || String(e) });
      }
    })();
    return true; // keep port open for async response
  }
});
