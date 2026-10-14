/* Final analytics polish: layout, comparison windows, labels and presentation fixes. */
(() => {
  const monthLabel = (key, includeYear = false) => {
    const [year, month] = String(key || '').split('-').map(Number);
    if (!year || !month) return key || '';
    return new Date(year, month - 1, 1, 12).toLocaleDateString(undefined,
      includeYear ? { month: 'short', year: '2-digit' } : { month: 'short' });
  };

  const ratioLabel = value => {
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    return n.toFixed(2).replace(/0+$/, '').replace(/\.$/, '') + '×';
  };

  const localIsoDate = date => date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0') + '-' + String(date.getDate()).padStart(2, '0');

  function normalizeE1rmData() {
    if (typeof data === 'undefined' || !data) return;
    for (const exercise of data.exercises || []) {
      exercise.e1rm = Math.max(Number(exercise.e1rm) || 0, Number(exercise.best_weight) || 0);
    }
    for (const record of data.records || []) {
      record.e1rm = Math.max(Number(record.e1rm) || 0, Number(record.best_weight) || 0);
    }
    if (Array.isArray(data.records)) data.records.sort((a, b) => Number(b.e1rm || 0) - Number(a.e1rm || 0));
  }

  function renderCorrectedRecords() {
    const box = document.getElementById('records');
    if (!box || typeof data === 'undefined' || !data) return;
    box.replaceChildren();
    const rows = data.records || [];
    if (!rows.length) {
      text(box, 'p', 'No weighted exercise records yet.');
      return;
    }
    rows.slice(0, 7).forEach((x, i) => {
      const row = text(box, 'div', '', 'session');
      const left = text(row, 'div', '');
      text(left, 'strong', (i + 1) + '. ' + x.name);
      text(left, 'p', 'Best ' + num(x.best_weight) + ' kg · ' + num(x.volume) + ' kg volume');
      text(row, 'span', 'e1RM ' + num(Math.max(Number(x.e1rm) || 0, Number(x.best_weight) || 0)) + ' kg');
    });
  }

  function tidyAnalyticsLayout() {
    const monthlyGrid = document.getElementById('monthly')?.closest('.grid');
    const exerciseGrid = document.getElementById('topExercises')?.closest('.grid');
    if (monthlyGrid) monthlyGrid.classList.add('analytics-paired-grid', 'analytics-month-row');
    if (exerciseGrid) exerciseGrid.classList.add('analytics-paired-grid', 'analytics-exercise-row');

    const recordsArticle = document.getElementById('records')?.closest('article');
    const patternsArticle = document.getElementById('patterns')?.closest('article');
    if (!recordsArticle || !patternsArticle || recordsArticle.parentElement !== patternsArticle.parentElement) return;
    const grid = recordsArticle.parentElement;
    grid.classList.add('analytics-final-grid');
    if (grid.firstElementChild !== patternsArticle) grid.insertBefore(patternsArticle, recordsArticle);
  }

  function effectiveTrainingBounds() {
    if (typeof data === 'undefined' || !data) return null;
    const endKey = data.date_range?.end;
    let startKey = data.date_range?.start;
    const firstRecorded = data.lifetime?.first_date;
    if (firstRecorded && (!startKey || firstRecorded > startKey)) startKey = firstRecorded;
    if (!startKey || !endKey) return null;
    const start = new Date(startKey + 'T12:00:00');
    const end = new Date(endKey + 'T12:00:00');
    return { start, end, startKey, endKey, days: Math.max(1, Math.round((end - start) / 86400000) + 1) };
  }

  function correctedChartRows() {
    const bounds = effectiveTrainingBounds();
    if (!bounds || typeof data === 'undefined' || !data) return [];
    if (bounds.days < 365) {
      const monday = new Date(bounds.start);
      monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
      const firstWeek = localIsoDate(monday);
      return (data.weekly || [])
        .filter(w => w.date >= firstWeek && w.date <= bounds.endKey)
        .map(w => ({ ...w, label: w.date.slice(5), title: 'Week of ' + w.date }));
    }
    const firstMonth = bounds.startKey.slice(0, 7);
    return (data.monthly || [])
      .filter(w => w.month >= firstMonth && w.month <= bounds.endKey.slice(0, 7))
      .map(w => ({ ...w, label: w.month.slice(5), title: 'Month ' + w.month }));
  }

  function installCorrectedChartRows() {
    if (typeof chartRows === 'function') chartRows = correctedChartRows;
  }

  function polishOverviewChartCadence() {
    const bounds = effectiveTrainingBounds();
    const monthly = Boolean(bounds && bounds.days >= 365);
    const cadence = monthly ? 'month' : 'week';
    const frequency = document.getElementById('frequency')?.closest('article');
    const volume = document.getElementById('volume')?.closest('article');
    const sets = document.getElementById('setsChart')?.closest('article');
    const time = document.getElementById('timeChart')?.closest('article');
    if (frequency) {
      const h = frequency.querySelector('h2'), p = frequency.querySelector('p');
      if (h) h.textContent = monthly ? '📅 Monthly consistency' : '📅 Weekly consistency';
      if (p) p.textContent = 'Workouts per ' + cadence;
    }
    if (volume) {
      const p = volume.querySelector('p');
      if (p) p.textContent = 'Weight × reps per ' + cadence;
    }
    if (sets) {
      const h = sets.querySelector('h2'), p = sets.querySelector('p');
      if (h) h.textContent = monthly ? '🔥 Sets per month' : '🔥 Sets per week';
      if (p) p.textContent = 'Working sets, excluding warm-ups';
    }
    if (time) {
      const p = time.querySelector('p');
      if (p) p.textContent = 'Minutes trained per ' + cadence;
    }
  }

  function rerenderOverviewCharts() {
    if (typeof bars !== 'function' || typeof data === 'undefined' || !data) return;
    bars('frequency', 'workouts');
    bars('volume', 'volume');
    bars('setsChart', 'sets');
    bars('timeChart', 'minutes');
    polishOverviewChartCadence();
  }

  function polishMonthlyLabels() {
    if (typeof data === 'undefined' || !data) return;
    const rows = data.monthly || [];
    const years = new Set(rows.map(x => String(x.month || '').slice(0, 4)));
    const includeYear = years.size > 1;
    const labels = document.querySelectorAll('#monthly .barcol small');
    labels.forEach((label, index) => {
      if (rows[index]) label.textContent = monthLabel(rows[index].month, includeYear);
    });
  }

  function polishLoadRatio() {
    if (typeof data === 'undefined' || !data?.load?.available) return;
    const cards = [...document.querySelectorAll('#load .mini')];
    const card = cards.find(x => x.querySelector('small')?.textContent?.toLowerCase().includes('7d vs 28d'));
    const strong = card?.querySelector('strong');
    if (strong) strong.textContent = ratioLabel(data.load.ratio);
  }

  function renderGroupedPrTimeline() {
    const box = document.getElementById('prTimeline');
    if (!box || typeof data === 'undefined' || !data) return;
    box.replaceChildren();
    const prs = data.prs || [];
    if (!prs.length) {
      text(box, 'p', 'PRs will appear after an exercise has enough history to beat a previous record.');
      return;
    }
    const grouped = new Map();
    for (const pr of prs) {
      const key = pr.date + '\u0000' + pr.exercise;
      if (!grouped.has(key)) grouped.set(key, { date: pr.date, exercise: pr.exercise, events: [] });
      grouped.get(key).events.push(pr);
    }
    [...grouped.values()].slice(0, 12).forEach(group => {
      const row = text(box, 'div', '', 'session pr-grouped');
      const left = text(row, 'div', '');
      text(left, 'strong', group.exercise);
      const details = group.events.map(pr => pr.kind + ': ' + num(pr.value) + ' ' + pr.unit).join(' · ');
      text(left, 'p', group.date + ' · ' + details);
      text(row, 'span', group.events.length === 1 ? 'PR' : group.events.length + ' PRs', 'pr-count');
    });
  }

  function renderCorrectedExerciseBreakdown() {
    const box = document.getElementById('table');
    if (!box || typeof data === 'undefined' || !data) return;
    box.replaceChildren();
    const sort = document.getElementById('exerciseSort')?.value || 'volume';
    const latest = e => (e.history || []).reduce((max, h) => h.date > max ? h.date : max, '');
    const rows = [...(data.exercises || [])].sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name);
      if (sort === 'recent') return latest(b).localeCompare(latest(a)) || a.name.localeCompare(b.name);
      const field = sort === 'sessions' ? 'sessions' : sort === 'sets' ? 'sets' : 'volume';
      return (Number(b[field]) || 0) - (Number(a[field]) || 0) || a.name.localeCompare(b.name);
    });
    for (const e of rows) {
      const tr = text(box, 'tr', '');
      const hasWeightedSets = Number(e.measurement_counts?.weighted || 0) > 0 || e.measurement_type === 'weighted';
      const values = [
        e.name,
        e.sessions,
        e.sets,
        num(e.reps),
        hasWeightedSets && Number(e.best_weight) > 0 ? num(e.best_weight) : '—',
        hasWeightedSets && Number(e.e1rm) > 0 ? num(e.e1rm) : '—',
        hasWeightedSets && Number(e.volume) > 0 ? num(e.volume) : '—'
      ];
      values.forEach(v => text(tr, 'td', v));
      tr.title = 'Last recorded: ' + (latest(e) || 'Unknown');
    }
  }

  function installExerciseBreakdownFix() {
    const select = document.getElementById('exerciseSort');
    if (select) select.onchange = renderCorrectedExerciseBreakdown;
    renderCorrectedExerciseBreakdown();
  }

  function enhanceMeasurementMetricOptions() {
    const select = document.getElementById('measureMetric');
    if (!select) return;
    const extra = [
      ['left_biceps', 'Left biceps (cm)'],
      ['right_biceps', 'Right biceps (cm)'],
      ['left_forearm', 'Left forearm (cm)'],
      ['right_forearm', 'Right forearm (cm)'],
      ['left_thigh', 'Left thigh (cm)'],
      ['right_thigh', 'Right thigh (cm)'],
      ['left_calf', 'Left calf (cm)'],
      ['right_calf', 'Right calf (cm)'],
      ['lean_mass', 'Lean mass (kg)'],
      ['body_fat', 'Body fat (%)'],
      ['abdomen', 'Abdomen (cm)']
    ];
    const existing = new Set([...select.options].map(option => option.value));
    for (const [value, label] of extra) {
      if (existing.has(value)) continue;
      const option = document.createElement('option');
      option.value = value;
      option.textContent = label;
      select.appendChild(option);
    }
  }

  function deltaText(current, previous) {
    const p = Number(previous || 0);
    if (!p) return 'No comparable prior data';
    const d = (Number(current || 0) - p) / p * 100;
    return (d >= 0 ? '+' : '') + num(d) + '%';
  }

  async function fetchReportStats(key) {
    const [year, month] = String(key || '').split('-').map(Number);
    if (!year || !month) return null;
    const last = new Date(year, month, 0).getDate();
    const start = key + '-01';
    const end = key + '-' + String(last).padStart(2, '0');
    const response = await fetch('/api/stats?days=90&start=' + start + '&end=' + end);
    if (!response.ok) return null;
    return response.json();
  }

  async function polishExactPrCount() {
    const key = document.getElementById('reportMonth')?.value;
    if (!key) return;
    try {
      const monthData = await fetchReportStats(key);
      if (!monthData) return;
      const card = [...document.querySelectorAll('#monthlyReport .reporthighlights .mini')]
        .find(x => x.querySelector('small')?.textContent === 'PR events');
      const strong = card?.querySelector('strong');
      if (!strong) return;
      if (Number.isFinite(Number(monthData.pr_count))) strong.textContent = num(monthData.pr_count);
      else {
        const visible = (monthData.prs || []).length;
        strong.textContent = visible >= 30 ? visible + '+' : num(visible);
      }
    } catch (_) {
      // Leave the already rendered value in place if the exact-count request fails.
    }
  }

  async function polishCurrentMonthReport() {
    const key = document.getElementById('reportMonth')?.value;
    if (!key || typeof reportArchive === 'undefined' || !reportArchive) return;
    const now = new Date();
    const currentKey = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
    if (key !== currentKey) return;

    const [year, month] = key.split('-').map(Number);
    const previousMonth = new Date(year, month - 2, 1, 12);
    const previousKey = previousMonth.getFullYear() + '-' + String(previousMonth.getMonth() + 1).padStart(2, '0');
    const previousLastDay = new Date(previousMonth.getFullYear(), previousMonth.getMonth() + 1, 0).getDate();
    const comparableDay = Math.min(now.getDate(), previousLastDay);
    const prevStart = previousKey + '-01';
    const prevEnd = previousKey + '-' + String(comparableDay).padStart(2, '0');

    try {
      const response = await fetch('/api/stats?days=90&start=' + prevStart + '&end=' + prevEnd);
      if (!response.ok) return;
      const previousData = await response.json();
      const previous = (previousData.monthly || []).find(x => x.month === previousKey) || { workouts: 0, sets: 0, volume: 0, minutes: 0 };
      const current = (reportArchive.monthly || []).find(x => x.month === key) || { workouts: 0, sets: 0, volume: 0, minutes: 0 };
      const previousName = previousMonth.toLocaleDateString(undefined, { month: 'short' });
      const intro = document.querySelector('#monthlyReport .reportintro');
      if (intro) intro.textContent = 'Compared with ' + previousName + ' 1–' + comparableDay + ' · matching elapsed days';

      const values = {
        'Workouts': [current.workouts, previous.workouts],
        'Working sets': [current.sets, previous.sets],
        'Volume': [current.volume, previous.volume],
        'Training time': [current.minutes, previous.minutes]
      };
      document.querySelectorAll('#monthlyReport .reportmetric').forEach(card => {
        const label = card.querySelector('small')?.textContent;
        const delta = card.querySelector('.reportdelta');
        if (!delta || !values[label]) return;
        delta.textContent = 'vs ' + previousName + ' 1–' + comparableDay + ' · ' + deltaText(values[label][0], values[label][1]);
      });
    } catch (_) {
      // Keep the already rendered full-month comparison if the extra comparison request fails.
    }
  }

  function applyPolish() {
    normalizeE1rmData();
    tidyAnalyticsLayout();
    enhanceMeasurementMetricOptions();
    installCorrectedChartRows();
    rerenderOverviewCharts();
    polishMonthlyLabels();
    polishLoadRatio();
    renderGroupedPrTimeline();
    renderCorrectedRecords();
    if (typeof renderRecordExplorer === 'function') renderRecordExplorer();
    installExerciseBreakdownFix();
    if (typeof progress === 'function' && document.getElementById('exercise')?.value) progress();
  }

  installCorrectedChartRows();
  enhanceMeasurementMetricOptions();

  const existingRenderMonthlyReport = typeof renderMonthlyReport === 'function' ? renderMonthlyReport : null;
  if (existingRenderMonthlyReport) {
    renderMonthlyReport = async function (...args) {
      const result = await existingRenderMonthlyReport.apply(this, args);
      await polishExactPrCount();
      await polishCurrentMonthReport();
      return result;
    };
  }

  const existingLoad = typeof load === 'function' ? load : null;
  if (existingLoad) {
    load = async function (...args) {
      const result = await existingLoad.apply(this, args);
      applyPolish();
      await polishExactPrCount();
      await polishCurrentMonthReport();
      return result;
    };
  }

  // Covers the initial async load that may already be in flight when this overlay is evaluated.
  let attempts = 0;
  const initial = setInterval(async () => {
    attempts += 1;
    if (typeof data !== 'undefined' && data) {
      clearInterval(initial);
      applyPolish();
      await polishExactPrCount();
      await polishCurrentMonthReport();
    } else if (attempts > 30) clearInterval(initial);
  }, 200);
})();
