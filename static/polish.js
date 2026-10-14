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

  function deltaText(current, previous) {
    const p = Number(previous || 0);
    if (!p) return 'No comparable prior data';
    const d = (Number(current || 0) - p) / p * 100;
    return (d >= 0 ? '+' : '') + num(d) + '%';
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
    polishMonthlyLabels();
    polishLoadRatio();
    renderGroupedPrTimeline();
    renderCorrectedRecords();
    if (typeof renderRecordExplorer === 'function') renderRecordExplorer();
    if (typeof renderExerciseBreakdown === 'function') renderExerciseBreakdown();
    if (typeof progress === 'function' && document.getElementById('exercise')?.value) progress();
  }

  const existingRenderMonthlyReport = typeof renderMonthlyReport === 'function' ? renderMonthlyReport : null;
  if (existingRenderMonthlyReport) {
    renderMonthlyReport = async function (...args) {
      const result = await existingRenderMonthlyReport.apply(this, args);
      await polishCurrentMonthReport();
      return result;
    };
  }

  const existingLoad = typeof load === 'function' ? load : null;
  if (existingLoad) {
    load = async function (...args) {
      const result = await existingLoad.apply(this, args);
      applyPolish();
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
      await polishCurrentMonthReport();
    } else if (attempts > 30) clearInterval(initial);
  }, 200);
})();
