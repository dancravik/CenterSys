// Обёртка над fetch: возвращает JSON или null при ошибке.
async function fetchJSON(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

const NO_DATA = '<div class="no-data">Нет информации</div>';
