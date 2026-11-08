"""
Digital Microscope — Professional Web Interface
"""

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import tempfile

from microscope.core import DigitalMicroscope

app = FastAPI(title="Микроскоп цифрового пространства", version="2.0")

HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Микроскоп цифрового пространства</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  body { font-family: system-ui, -apple-system, sans-serif; }
  .tree-node { margin-left: 1rem; border-left: 1px solid #e2e8f0; padding-left: 0.5rem; }
  .mol { padding: 3px 8px; border-radius: 6px; margin: 2px 0; cursor: pointer; }
  .mol:hover { background: #f1f5f9; }
  .badge { font-size: 0.65rem; font-weight: 600; padding: 1px 7px; border-radius: 999px; background: #e2e8f0; color: #334155; }
  .tab { padding: 6px 14px; border-radius: 8px; cursor: pointer; }
  .tab.active { background: #0f172a; color: white; }
</style>
</head>
<body class="bg-slate-100 text-slate-800">
<div class="max-w-7xl mx-auto p-4 md:p-6">
  <header class="mb-6 flex items-center justify-between">
    <div>
      <h1 class="text-2xl md:text-3xl font-bold tracking-tight">Микроскоп цифрового пространства</h1>
      <p class="text-slate-500 text-sm">Изучение цифровой ткани на молекулярном уровне · v2.0</p>
    </div>
    <div class="text-xs text-slate-400">универсальный инструмент</div>
  </header>

  <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
    <!-- Input -->
    <div class="lg:col-span-4 space-y-4">
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <h2 class="font-semibold mb-3">Образец</h2>
        <form id="form" class="space-y-3">
          <textarea id="content" rows="12" class="w-full border border-slate-200 rounded-xl p-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-slate-300" placeholder="Вставьте JSON, Python, CSV, HTML, Markdown, текст, YAML..."></textarea>
          <input type="file" id="file" class="text-sm w-full">
          <div class="flex gap-2">
            <button type="submit" class="flex-1 bg-slate-900 text-white py-2.5 rounded-xl hover:bg-slate-800 transition">Изучить</button>
            <button type="button" id="example" class="px-4 py-2.5 border rounded-xl text-sm hover:bg-slate-50">Пример</button>
          </div>
        </form>
      </div>
      <div id="stats" class="bg-white rounded-2xl shadow-sm p-5 hidden">
        <h2 class="font-semibold mb-2">Статистика</h2>
        <div id="stats-content" class="text-sm space-y-1.5"></div>
      </div>
    </div>

    <!-- Results -->
    <div class="lg:col-span-8">
      <div class="bg-white rounded-2xl shadow-sm p-5 min-h-[560px]">
        <div class="flex gap-2 mb-4">
          <div class="tab active" data-tab="tree">Дерево</div>
          <div class="tab" data-tab="graph">Граф</div>
          <div class="tab" data-tab="json">JSON</div>
        </div>
        <div id="view-tree" class="overflow-auto max-h-[65vh] text-sm"></div>
        <div id="view-graph" class="hidden overflow-auto max-h-[65vh]"><div class="mermaid" id="mermaid-box"></div></div>
        <div id="view-json" class="hidden overflow-auto max-h-[65vh]"><pre id="json-box" class="text-xs bg-slate-50 p-3 rounded-lg"></pre></div>
      </div>
    </div>
  </div>
</div>

<script>
mermaid.initialize({ startOnLoad: false, theme: 'neutral' });

const form = document.getElementById('form');
const views = { tree: document.getElementById('view-tree'), graph: document.getElementById('view-graph'), json: document.getElementById('view-json') };
document.querySelectorAll('.tab').forEach(t => {
  t.onclick = () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    Object.values(views).forEach(v => v.classList.add('hidden'));
    views[t.dataset.tab].classList.remove('hidden');
  };
});

function renderTree(node) {
  const div = document.createElement('div');
  div.className = 'tree-node';
  const row = document.createElement('div');
  row.className = 'mol flex items-center gap-2';
  const badge = document.createElement('span');
  badge.className = 'badge';
  badge.textContent = node.type;
  const name = document.createElement('span');
  name.className = 'font-medium';
  name.textContent = node.name;
  row.append(badge, name);
  if (node.value) {
    const v = document.createElement('span');
    v.className = 'text-slate-500 text-xs truncate max-w-xs';
    v.textContent = '= ' + String(node.value).slice(0, 120);
    row.append(v);
  }
  div.append(row);
  if (node.children?.length) {
    node.children.slice(0, 50).forEach(c => div.append(renderTree(c)));
    if (node.children.length > 50) {
      const more = document.createElement('div');
      more.className = 'text-xs text-slate-400 ml-4';
      more.textContent = `… ещё ${node.children.length - 50}`;
      div.append(more);
    }
  }
  return div;
}

document.getElementById('example').onclick = () => {
  document.getElementById('content').value = JSON.stringify({
    project: "Digital Microscope",
    version: "2.0",
    features: ["tree", "graph", "stats", "cli", "web"],
    molecules: 128,
    active: true
  }, null, 2);
};

form.onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData();
  const file = document.getElementById('file').files[0];
  const text = document.getElementById('content').value;
  if (file) fd.append('file', file);
  else if (text.trim()) fd.append('text', text);
  else return alert('Введите данные или загрузите файл');

  views.tree.innerHTML = '<p class="text-slate-400">Анализирую ткань…</p>';
  try {
    const res = await fetch('/api/analyze', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    views.tree.innerHTML = '';
    views.tree.append(renderTree(data.tree));

    document.getElementById('json-box').textContent = JSON.stringify(data, null, 2);
    document.getElementById('mermaid-box').textContent = data.mermaid || 'graph TD\n  A[нет данных]';
    mermaid.run({ nodes: [document.getElementById('mermaid-box')] });

    document.getElementById('stats').classList.remove('hidden');
    document.getElementById('stats-content').innerHTML = `
      <div>Тип: <b>${data.detected}</b></div>
      <div>Молекул: <b>${data.stats.total_molecules}</b></div>
      <div>Глубина: <b>${data.stats.depth}</b></div>
      <div class="text-xs text-slate-500 mt-2">${Object.entries(data.stats.types).slice(0,10).map(([k,v])=>`${k}: ${v}`).join(' · ')}</div>
    `;
  } catch (err) {
    views.tree.innerHTML = `<p class="text-red-500">${err.message}</p>`;
  }
};
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.post("/api/analyze")
async def analyze(text: str = Form(None), file: UploadFile = File(None)):
    scope = DigitalMicroscope()
    try:
        if file:
            content = await file.read()
            name = file.filename
        elif text:
            content = text
            name = "pasted.txt"
        else:
            return JSONResponse({"error": "Нет данных"}, status_code=400)

        root = scope.analyze(content, filename=name)
        stats = scope.get_stats(root)
        mermaid = scope.to_mermaid(root)
        return {
            "detected": root.metadata.get("detected_type"),
            "stats": stats,
            "tree": root.to_dict(),
            "mermaid": mermaid,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0"}
