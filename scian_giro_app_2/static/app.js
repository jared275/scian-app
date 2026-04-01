const queryInput = document.getElementById('query-input');
const clearButton = document.getElementById('clear-button');
const resultsRoot = document.getElementById('results-root');
const emptyState = document.getElementById('empty-state');
const helper = document.getElementById('query-helper');
const metaCards = document.getElementById('meta-cards');

const LEVEL_FLOW = [
  { key: 'sector', label: 'Sector' },
  { key: 'subsector', label: 'Subsector' },
  { key: 'rama', label: 'Rama' },
  { key: 'subrama', label: 'Subrama' },
];

let debounceTimer = null;
let appState = {
  data: null,
  selectedIds: Object.fromEntries(LEVEL_FLOW.map((level) => [level.key, null])),
  focusLevel: 'sector',
};

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderScoreBar(scorePct) {
  return `
    <div class="score-bar">
      <span style="width:${Math.max(0, Math.min(scorePct, 100))}%"></span>
    </div>
  `;
}

function breadcrumbText(breadcrumb) {
  return (breadcrumb || [])
    .map((item) => `${item.level_label} ${item.code} - ${item.title}`)
    .join(' > ');
}

function getNode(nodeId) {
  return appState.data?.guide?.nodes?.[nodeId] || null;
}

function getPath(pathId) {
  return (appState.data?.top_paths || []).find((path) => path.id === pathId) || null;
}

function getLevelIndex(levelKey) {
  return LEVEL_FLOW.findIndex((level) => level.key === levelKey);
}

function getSelectedNodes() {
  return LEVEL_FLOW.map((level) => getNode(appState.selectedIds[level.key])).filter(Boolean);
}

function getDeepestSelectedNode() {
  const nodes = getSelectedNodes();
  return nodes.length ? nodes[nodes.length - 1] : null;
}

function resetSelectionState() {
  appState.selectedIds = Object.fromEntries(LEVEL_FLOW.map((level) => [level.key, null]));
  appState.focusLevel = 'sector';
}

function cascadeSelectionFrom(levelKey) {
  const startIndex = getLevelIndex(levelKey);
  for (let idx = startIndex + 1; idx < LEVEL_FLOW.length; idx += 1) {
    const parentLevel = LEVEL_FLOW[idx - 1].key;
    const currentLevel = LEVEL_FLOW[idx].key;
    const parentNode = getNode(appState.selectedIds[parentLevel]);
    const bestChildId = parentNode?.child_ids?.[0] || null;
    appState.selectedIds[currentLevel] = bestChildId;
  }
}

function applySelection(levelKey, nodeId) {
  appState.selectedIds[levelKey] = nodeId;
  appState.focusLevel = levelKey;
  cascadeSelectionFrom(levelKey);
  renderResults();
}

function applyPath(path) {
  if (!path) {
    return;
  }

  resetSelectionState();
  LEVEL_FLOW.forEach((level) => {
    appState.selectedIds[level.key] = path.levels?.[level.key]?.id || null;
  });
  appState.focusLevel = 'subrama';
  renderResults();
}

function syncSelectionFromDefault(data) {
  resetSelectionState();
  appState.focusLevel = 'sector';
  const defaults = data?.guide?.default_selection || {};

  LEVEL_FLOW.forEach((level) => {
    appState.selectedIds[level.key] = defaults[`${level.key}_id`] || null;
  });

  const lastDefinedIndex = LEVEL_FLOW.map((level, idx) => (appState.selectedIds[level.key] ? idx : -1)).reduce(
    (maxValue, currentValue) => Math.max(maxValue, currentValue),
    -1,
  );

  if (lastDefinedIndex >= 0) {
    cascadeSelectionFrom(LEVEL_FLOW[lastDefinedIndex].key);
  }
}

function currentSelectionCopyText() {
  const selectedNodes = getSelectedNodes();
  if (!selectedNodes.length) {
    return '';
  }
  return selectedNodes.map((node) => `${node.level_label} ${node.code} - ${node.title}`).join(' > ');
}

function copyText(text, button) {
  navigator.clipboard.writeText(text).then(() => {
    const original = button.textContent;
    button.textContent = 'Copiado';
    setTimeout(() => {
      button.textContent = original;
    }, 1400);
  });
}

function optionMeta(node, levelKey) {
  const bits = [];
  if (levelKey !== 'subrama') {
    bits.push(`Nivel ${node.score_pct}%`);
  }
  if (levelKey === 'subrama') {
    bits.push('Último nivel');
  } else if (node.children_count === 1) {
    bits.push('1 opción debajo');
  } else if (node.children_count > 1) {
    bits.push(`${node.children_count} opciones debajo`);
  }
  return bits.join(' · ');
}

function optionPrimaryScore(node, levelKey) {
  return levelKey === 'subrama' ? node.score_pct : node.guide_score_pct;
}

function optionPrimaryLabel(levelKey) {
  return levelKey === 'subrama' ? 'Coincidencia' : 'Camino';
}

function renderGuideOption(node, levelKey) {
  const isSelected = appState.selectedIds[levelKey] === node.id;
  return `
    <button
      type="button"
      class="guide-option ${isSelected ? 'selected' : ''}"
      data-level="${escapeHtml(levelKey)}"
      data-node-id="${escapeHtml(node.id)}"
    >
      <div class="guide-option-top">
        <span class="code-badge">${escapeHtml(node.code)}</span>
        <span class="score-badge">${escapeHtml(optionPrimaryLabel(levelKey))} ${escapeHtml(optionPrimaryScore(node, levelKey))}%</span>
      </div>
      <strong>${escapeHtml(node.title)}</strong>
      <p class="option-meta">${escapeHtml(optionMeta(node, levelKey))}</p>
      ${renderScoreBar(optionPrimaryScore(node, levelKey))}
    </button>
  `;
}

function getOptionsForLevel(levelKey) {
  if (!appState.data?.guide) {
    return [];
  }

  if (levelKey === 'sector') {
    return (appState.data.guide.root_sector_ids || []).map(getNode).filter(Boolean);
  }

  const levelIndex = getLevelIndex(levelKey);
  const parentLevelKey = LEVEL_FLOW[levelIndex - 1]?.key;
  const parentNode = getNode(appState.selectedIds[parentLevelKey]);
  if (!parentNode) {
    return [];
  }

  return (parentNode.child_ids || []).map(getNode).filter(Boolean);
}

function renderGuideStep(levelKey, index) {
  const options = getOptionsForLevel(levelKey);
  const selectedNode = getNode(appState.selectedIds[levelKey]);
  const levelLabel = LEVEL_FLOW[index].label;

  let subtitle = 'Haz click para elegir.';
  if (index === 0) {
    subtitle = 'Empieza por los sectores mejor posicionados.';
  } else {
    const parentNode = getNode(appState.selectedIds[LEVEL_FLOW[index - 1].key]);
    subtitle = parentNode
      ? `Dentro de: ${parentNode.title}`
      : `Selecciona un ${LEVEL_FLOW[index - 1].label.toLowerCase()} para continuar.`;
  }

  return `
    <section class="guide-step">
      <div class="guide-step-header">
        <div>
          <p class="step-eyebrow">Paso ${index + 1}</p>
          <h3>${escapeHtml(levelLabel)}</h3>
          <p class="step-subtitle">${escapeHtml(subtitle)}</p>
        </div>
        ${selectedNode ? `<span class="pill">${escapeHtml(selectedNode.code)}</span>` : ''}
      </div>
      <div class="guide-option-list">
        ${
          options.length
            ? options.map((node) => renderGuideOption(node, levelKey)).join('')
            : '<div class="guide-placeholder">Todavía no hay opciones para este paso.</div>'
        }
      </div>
    </section>
  `;
}

function pathMatchesCurrentSelection(path) {
  const focusIndex = Math.max(0, getLevelIndex(appState.focusLevel));
  for (let idx = 0; idx <= focusIndex; idx += 1) {
    const level = LEVEL_FLOW[idx];
    const selectedId = appState.selectedIds[level.key];
    if (!selectedId) {
      break;
    }
    if (path.levels?.[level.key]?.id !== selectedId) {
      return false;
    }
  }
  return true;
}

function renderPathPreview(path) {
  return `
    <article class="mini-path">
      <div class="mini-path-head">
        <span class="score-badge">Ruta ${escapeHtml(path.score_pct)}%</span>
        <span class="level-badge">Mejor nivel: ${escapeHtml(path.best_level_label)}</span>
      </div>
      <p class="mini-path-text">${escapeHtml(breadcrumbText(path.breadcrumb))}</p>
      <div class="mini-path-actions">
        <button type="button" class="text-button" data-apply-path="${escapeHtml(path.id)}">Usar este camino</button>
      </div>
    </article>
  `;
}

function renderFocusCard() {
  const selectedNodes = getSelectedNodes();
  const deepestNode = getDeepestSelectedNode();
  const bestPath = appState.data?.guide?.best_path || null;
  const activePathText = selectedNodes.length
    ? selectedNodes.map((node) => `${node.level_label} ${node.code} - ${node.title}`).join(' > ')
    : bestPath
      ? breadcrumbText(bestPath.breadcrumb)
      : 'Todavía no hay una ruta seleccionada.';

  const relatedPaths = (appState.data?.top_paths || []).filter(pathMatchesCurrentSelection);
  const previewPaths = (relatedPaths.length ? relatedPaths : appState.data?.top_paths || []).slice(0, 3);
  const hasFinalSelection = Boolean(appState.selectedIds.subrama && deepestNode?.level === 'subrama');

  return `
    <section class="card route-focus">
      <div class="section-title-row route-focus-head">
        <div>
          <h2>Ruta sugerida actual</h2>
          <p class="section-subtitle">
            La app sigue automáticamente el mejor camino dentro de la opción que elijas. Puedes cambiar cualquier paso con un click.
          </p>
        </div>
        ${bestPath ? '<span class="pill">Mejor ruta global disponible</span>' : ''}
      </div>

      <div class="route-crumbs">${escapeHtml(activePathText)}</div>

      <div class="route-actions">
        ${
          hasFinalSelection
            ? `<button type="button" class="copy-button" data-copy="${escapeHtml(currentSelectionCopyText())}">Copiar recorrido</button>`
            : '<span class="muted">Completa hasta Subrama para copiar el recorrido final.</span>'
        }
        ${bestPath ? `<button type="button" class="secondary-button inline-button" data-apply-path="${escapeHtml(bestPath.id)}">Volver a la mejor ruta</button>` : ''}
      </div>

      <div class="selection-status-grid">
        ${LEVEL_FLOW.map((level) => {
          const node = getNode(appState.selectedIds[level.key]);
          return `
            <div class="selection-status-card ${node ? 'filled' : ''}">
              <span>${escapeHtml(level.label)}</span>
              <strong>${escapeHtml(node ? `${node.code} - ${node.title}` : 'Sin elegir')}</strong>
            </div>
          `;
        }).join('')}
      </div>

      <details class="related-paths" ${previewPaths.length ? 'open' : ''}>
        <summary>Ver rutas fuertes compatibles con la selección actual</summary>
        <div class="mini-path-list">
          ${
            previewPaths.length
              ? previewPaths.map(renderPathPreview).join('')
              : '<p class="muted">No se encontraron rutas adicionales para la selección actual.</p>'
          }
        </div>
      </details>
    </section>
  `;
}

function bindDynamicEvents() {
  resultsRoot.querySelectorAll('[data-level][data-node-id]').forEach((button) => {
    button.addEventListener('click', () => {
      applySelection(button.dataset.level, button.dataset.nodeId);
    });
  });

  resultsRoot.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', () => copyText(button.dataset.copy, button));
  });

  resultsRoot.querySelectorAll('[data-apply-path]').forEach((button) => {
    button.addEventListener('click', () => {
      const path = getPath(button.dataset.applyPath);
      applyPath(path);
    });
  });
}

function renderResults() {
  if (!appState.data?.query) {
    resultsRoot.innerHTML = '';
    resultsRoot.appendChild(emptyState);
    emptyState.classList.remove('hidden');
    helper.textContent = 'La búsqueda abre el camino más probable y puedes ajustar cualquier nivel con un click.';
    return;
  }

  emptyState.classList.add('hidden');

  resultsRoot.innerHTML = `
    ${renderFocusCard()}
    <section class="card">
      <div class="section-title-row">
        <div>
          <h2>Explorador guiado por niveles</h2>
          <p class="section-subtitle">Avanza de Sector a Subrama sin perder de vista qué caminos tienen mejor similitud.</p>
        </div>
      </div>
      <div class="guide-grid">
        ${LEVEL_FLOW.map((level, index) => renderGuideStep(level.key, index)).join('')}
      </div>
    </section>
  `;

  helper.textContent = `Consulta expandida: ${appState.data.expanded_query}`;
  bindDynamicEvents();
}

async function loadMeta() {
  const response = await fetch('/api/meta');
  const meta = await response.json();
  metaCards.innerHTML = `
    <div class="mini-stat"><span>Subramas</span><strong>${meta.rows}</strong></div>
    <div class="mini-stat"><span>Sectores</span><strong>${meta.levels.sector}</strong></div>
    <div class="mini-stat"><span>Ramas</span><strong>${meta.levels.rama}</strong></div>
  `;
}

async function searchNow() {
  const value = queryInput.value.trim();
  if (!value) {
    appState.data = null;
    resetSelectionState();
    renderResults();
    return;
  }

  resultsRoot.innerHTML = '<section class="card"><p class="muted">Buscando coincidencias y armando el árbol sugerido…</p></section>';
  const response = await fetch(`/api/search?q=${encodeURIComponent(value)}`);
  const data = await response.json();
  appState.data = data;
  syncSelectionFromDefault(data);
  renderResults();
}

function scheduleSearch() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(searchNow, 220);
}

queryInput.addEventListener('input', scheduleSearch);
queryInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    clearTimeout(debounceTimer);
    searchNow();
  }
});

clearButton.addEventListener('click', () => {
  queryInput.value = '';
  appState.data = null;
  resetSelectionState();
  renderResults();
  queryInput.focus();
});

document.querySelectorAll('.example-chip').forEach((button) => {
  button.addEventListener('click', () => {
    queryInput.value = button.dataset.example || '';
    searchNow();
  });
});

loadMeta();
const initialQuery = new URLSearchParams(window.location.search).get('q');
if (initialQuery) {
  queryInput.value = initialQuery;
  searchNow();
} else {
  renderResults();
}
