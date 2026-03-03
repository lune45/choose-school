const ROUTES = {
  LANDING: "/",
  LOGIN: "/login",
  APP_HOME: "/app",
  STEP1: "/app/new",
  STEP2: "/app/concerns",
  STEP3: "/app/schools",
  STEP4: "/app/confirm"
};

const RANKING_DIMENSION_CONFIG = [
  { id: "employment", label: "就业薪资", weightKeys: ["就业薪资"], scoreKeys: ["就业薪资"] },
  { id: "rank", label: "学校排名", weightKeys: ["学校排名"], scoreKeys: ["学校排名"] },
  { id: "region", label: "区域", weightKeys: ["区域", "区域优势"], scoreKeys: ["区域", "区域优势"] },
  { id: "curriculum", label: "课程", weightKeys: ["课程", "课程适配"], scoreKeys: ["课程", "课程适配"] },
  { id: "cost", label: "成本", weightKeys: ["成本", "成本控制"], scoreKeys: ["成本", "成本控制"] },
  { id: "visa", label: "工签", weightKeys: ["工签", "工签支持"], scoreKeys: ["工签", "工签支持"] },
  { id: "alumni", label: "校友", weightKeys: ["校友", "校友网络"], scoreKeys: ["校友", "校友网络"] },
  { id: "h1b", label: "H1B", weightKeys: ["H1B", "H1B绿卡"], scoreKeys: ["H1B", "H1B绿卡"] },
];

const WIZARD_KEY = "wizardDraft";
const HISTORY_KEY = "analysisHistory";

function loadWizardDraft() {
  try {
    const raw = localStorage.getItem(WIZARD_KEY);
    if (!raw) {
      return {
        country: "",
        major: "CS",
        budget_max: 70000,
        concerns: ["学历提升", "学费压力", "学校排名"],
        school_ids: []
      };
    }
    const parsed = JSON.parse(raw);
    return {
      country: parsed.country || "",
      major: parsed.major || "CS",
      budget_max: Number(parsed.budget_max || 70000),
      concerns: Array.isArray(parsed.concerns) ? parsed.concerns : ["学历提升", "学费压力", "学校排名"],
      school_ids: Array.isArray(parsed.school_ids) ? parsed.school_ids : []
    };
  } catch {
    return {
      country: "",
      major: "CS",
      budget_max: 70000,
      concerns: ["学历提升", "学费压力", "学校排名"],
      school_ids: []
    };
  }
}

function loadReportHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

const state = {
  token: localStorage.getItem("token") || "",
  currentUser: null,
  countries: [],
  schools: [],
  schoolsCountry: "",
  selectedSchoolIds: new Set(),
  reportPollTimer: null,
  currentReportId: null,
  lastAnalysisPayload: null,
  wizard: loadWizardDraft(),
  reportHistory: loadReportHistory(),
  dimensions: [
    "学历提升", "学费压力", "学校排名", "当地就业", "就业去向", "移民",
    "薪资", "回国认可度", "读书压力", "课程难度", "安全度", "生活开销"
  ]
};

state.selectedSchoolIds = new Set(state.wizard.school_ids || []);

const els = {
  landingPage: document.getElementById("landingPage"),
  appHero: document.getElementById("appHero"),
  authCard: document.getElementById("authCard"),
  appHomePage: document.getElementById("appHomePage"),
  stepNewPage: document.getElementById("stepNewPage"),
  stepConcernsPage: document.getElementById("stepConcernsPage"),
  stepSchoolsPage: document.getElementById("stepSchoolsPage"),
  stepConfirmPage: document.getElementById("stepConfirmPage"),
  resultCard: document.getElementById("resultCard"),

  authTip: document.getElementById("authTip"),
  excelTip: document.getElementById("excelTip"),
  historyList: document.getElementById("historyList"),

  countrySelect: document.getElementById("countrySelect"),
  majorInput: document.getElementById("majorInput"),
  budgetInput: document.getElementById("budgetInput"),

  schoolList: document.getElementById("schoolList"),
  selectedSummary: document.getElementById("selectedSummary"),
  confirmSelectedList: document.getElementById("confirmSelectedList"),
  dimensionBox: document.getElementById("dimensionBox"),
  schoolSearch: document.getElementById("schoolSearch"),

  modelTag: document.getElementById("modelTag"),
  reportError: document.getElementById("reportError"),
  executiveSummaryCard: document.getElementById("executiveSummaryCard"),
  schoolsCards: document.getElementById("schoolsCards"),
  finalRecommendationCard: document.getElementById("finalRecommendationCard"),
  reportDisclaimer: document.getElementById("reportDisclaimer"),
  pdfLink: document.getElementById("pdfLink")
};

function saveWizardDraft() {
  state.wizard.school_ids = [...state.selectedSchoolIds];
  localStorage.setItem(WIZARD_KEY, JSON.stringify(state.wizard));
}

function saveReportHistory() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(state.reportHistory));
}

function tip(el, msg, isError = false) {
  el.textContent = msg || "";
  el.style.color = isError ? "#b4303f" : "#4f5d75";
}

function fmtTime(input) {
  if (!input) return "-";
  const d = new Date(input);
  if (Number.isNaN(d.getTime())) return String(input);
  return d.toLocaleString();
}

function getStatusLabel(status) {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  return "生成中";
}

function getStatusClass(status) {
  if (status === "completed") return "status-completed";
  if (status === "failed") return "status-failed";
  return "status-pending";
}

function upsertHistory(item) {
  const idx = state.reportHistory.findIndex((x) => String(x.id) === String(item.id));
  if (idx >= 0) state.reportHistory[idx] = { ...state.reportHistory[idx], ...item };
  else state.reportHistory.unshift(item);
  saveReportHistory();
}

function replaceHistoryId(tempId, item) {
  const idx = state.reportHistory.findIndex((x) => String(x.id) === String(tempId));
  if (idx >= 0) state.reportHistory[idx] = item;
  else state.reportHistory.unshift(item);
  saveReportHistory();
}

function renderHistoryList() {
  els.historyList.innerHTML = "";
  if (!state.reportHistory.length) {
    els.historyList.innerHTML = '<div class="history-empty">暂无历史报告</div>';
    return;
  }

  state.reportHistory
    .slice()
    .sort((a, b) => new Date(b.created_at || b.createdAt || 0) - new Date(a.created_at || a.createdAt || 0))
    .forEach((item) => {
      const row = document.createElement("div");
      row.className = "history-row";
      row.innerHTML = `
        <div>
          <div class="history-time">${fmtTime(item.created_at || item.createdAt)}</div>
          <div class="history-status ${getStatusClass(item.status)}">${getStatusLabel(item.status)}</div>
        </div>
        <button class="mini" ${item.id && !String(item.id).startsWith("tmp-") ? "" : "disabled"}>进入报告</button>
      `;
      const btn = row.querySelector("button");
      btn.addEventListener("click", () => {
        if (!item.id || String(item.id).startsWith("tmp-")) return;
        navigate(`/app/report/${item.id}`);
      });
      els.historyList.appendChild(row);
    });
}

async function api(path, options = {}, auth = false) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (auth && state.token) headers.Authorization = `Bearer ${state.token}`;

  const response = await fetch(path, { ...options, headers });
  const isJson = (response.headers.get("content-type") || "").includes("application/json");
  const data = isJson ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = (data && data.detail) || JSON.stringify(data);
    throw new Error(detail || "请求失败");
  }
  return data;
}

function switchAuthTab(tab) {
  const registerPanel = document.getElementById("registerPanel");
  const loginPanel = document.getElementById("loginPanel");
  document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
  document.querySelector(`[data-tab='${tab}']`).classList.add("active");
  registerPanel.classList.toggle("hidden", tab !== "register");
  loginPanel.classList.toggle("hidden", tab !== "login");
}

function switchLoginMode(mode) {
  const pwdBox = document.getElementById("pwdLoginBox");
  const codeBox = document.getElementById("codeLoginBox");
  const pwdBtn = document.getElementById("pwdModeBtn");
  const codeBtn = document.getElementById("codeModeBtn");
  const isPwd = mode === "pwd";
  pwdBox.classList.toggle("hidden", !isPwd);
  codeBox.classList.toggle("hidden", isPwd);
  pwdBtn.classList.toggle("active", isPwd);
  codeBtn.classList.toggle("active", !isPwd);
}

function selectedDimensions() {
  return [...document.querySelectorAll("input[name='dimension']:checked")].map((i) => i.value);
}

function renderDimensions() {
  const selected = new Set(state.wizard.concerns || []);
  els.dimensionBox.innerHTML = "";
  state.dimensions.forEach((d) => {
    const label = document.createElement("label");
    label.className = "chip";
    label.innerHTML = `<input type="checkbox" name="dimension" value="${d}" ${selected.has(d) ? "checked" : ""}/> ${d}`;
    els.dimensionBox.appendChild(label);
  });
}

function syncWizardConcernsFromUI() {
  state.wizard.concerns = selectedDimensions();
  saveWizardDraft();
}

function renderSchools(list) {
  els.schoolList.innerHTML = "";
  list.forEach((s) => {
    const row = document.createElement("label");
    row.className = "school-item";
    const checked = state.selectedSchoolIds.has(s.id) ? "checked" : "";
    row.innerHTML = `
      <input type="checkbox" data-id="${s.id}" ${checked} />
      <div>
        <div class="school-title">${s.school_name} · ${s.program_name}</div>
        <div class="school-meta">学费 $${s.tuition_usd} | 生活费 $${s.living_cost_usd} | 薪资中位数 $${s.median_salary_usd}</div>
      </div>
    `;
    row.querySelector("input").addEventListener("change", (e) => {
      const id = Number(e.target.dataset.id);
      if (e.target.checked) state.selectedSchoolIds.add(id);
      else state.selectedSchoolIds.delete(id);
      saveWizardDraft();
      renderSelectedSummary();
      renderConfirmList();
    });
    els.schoolList.appendChild(row);
  });
}

function renderSelectedSummary() {
  const selected = state.schools.filter((s) => state.selectedSchoolIds.has(s.id));
  els.selectedSummary.innerHTML = "";
  if (selected.length === 0) {
    els.selectedSummary.innerHTML = '<span class="chip">尚未选择学校</span>';
    return;
  }

  selected.forEach((s) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = `${s.school_name} · ${s.program_name}`;
    els.selectedSummary.appendChild(chip);
  });
}

function renderConfirmList() {
  const selected = state.schools.filter((s) => state.selectedSchoolIds.has(s.id));
  els.confirmSelectedList.innerHTML = "";
  if (selected.length === 0) {
    els.confirmSelectedList.innerHTML = '<div class="history-empty">尚未选择学校</div>';
    return;
  }

  selected.forEach((s) => {
    const row = document.createElement("div");
    row.className = "confirm-row";
    row.innerHTML = `
      <div>
        <strong>${s.school_name}</strong>
        <div class="school-meta">${s.program_name}</div>
      </div>
      <button class="mini danger" type="button">移除</button>
    `;
    row.querySelector("button").addEventListener("click", () => {
      state.selectedSchoolIds.delete(s.id);
      saveWizardDraft();
      renderSelectedSummary();
      renderSchools(state.schools);
      renderConfirmList();
    });
    els.confirmSelectedList.appendChild(row);
  });
}

async function sendCode(phone, purpose, tipEl) {
  const data = await api("/api/auth/send-code", {
    method: "POST",
    body: JSON.stringify({ phone, purpose })
  });
  let msg = `验证码已发送，有效期 ${data.expires_minutes} 分钟。`;
  if (data.debug_code) msg += `（开发调试码：${data.debug_code}）`;
  tip(tipEl, msg);
}

function setToken(token) {
  state.token = token;
  localStorage.setItem("token", token);
}

function clearToken() {
  state.token = "";
  state.currentUser = null;
  state.lastAnalysisPayload = null;
  localStorage.removeItem("token");
}

async function fetchMe() {
  if (!state.token) return null;
  const me = await api("/api/auth/me", {}, true);
  state.currentUser = me;
  return me;
}

async function loadCountries() {
  if (state.countries.length) return;
  const data = await api("/api/countries");
  state.countries = data.countries || [];
}

function hydrateStep1() {
  els.countrySelect.innerHTML = "";
  state.countries.forEach((c) => {
    const op = document.createElement("option");
    op.value = c;
    op.textContent = c;
    els.countrySelect.appendChild(op);
  });

  if (!state.wizard.country && state.countries.length) {
    state.wizard.country = state.countries[0];
  }

  if (state.wizard.country) {
    els.countrySelect.value = state.wizard.country;
  }
  els.majorInput.value = state.wizard.major || "CS";
  els.budgetInput.value = Number(state.wizard.budget_max || 70000);
}

function renderSchoolsBySearch() {
  const keyword = els.schoolSearch.value.trim().toLowerCase();
  if (!keyword) {
    renderSchools(state.schools);
    return;
  }
  const filtered = state.schools.filter((s) => {
    const text = `${s.school_name} ${s.program_name}`.toLowerCase();
    return text.includes(keyword);
  });
  renderSchools(filtered);
}

async function loadSchools(force = false) {
  const country = state.wizard.country;
  if (!country || !state.token) return;
  if (!force && state.schoolsCountry === country && state.schools.length) {
    renderSchoolsBySearch();
    renderSelectedSummary();
    renderConfirmList();
    return;
  }

  const data = await api(`/api/schools?country=${encodeURIComponent(country)}`, {}, true);
  state.schools = Array.isArray(data) ? data : [];
  state.schoolsCountry = country;
  renderSchoolsBySearch();
  renderSelectedSummary();
  renderConfirmList();
}

function parseJsonLoose(raw) {
  if (!raw) return null;
  if (typeof raw === "object") return raw;
  if (typeof raw !== "string") return null;

  const cleaned = raw
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/\s*```$/i, "")
    .trim();

  try {
    return JSON.parse(cleaned);
  } catch {
    // continue
  }

  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start >= 0 && end > start) {
    const maybe = cleaned.slice(start, end + 1);
    try {
      return JSON.parse(maybe);
    } catch {
      return null;
    }
  }
  return null;
}

function toStringSafe(value) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function toArraySafe(value) {
  if (Array.isArray(value)) return value.map((x) => toStringSafe(x)).filter(Boolean);
  if (typeof value === "string") {
    return value
      .split(/\n|；|;|。/)
      .map((x) => x.trim())
      .filter(Boolean);
  }
  return [];
}

function normalizeConcernAnalysis(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) {
    return raw
      .map((item) => {
        if (typeof item === "string") return { key: "关注分析", value: item };
        if (!item || typeof item !== "object") return null;
        const key = toStringSafe(item.concern || item.key || item.title || item.name);
        const value = toStringSafe(item.analysis || item.value || item.content || item.detail);
        if (!key || !value) return null;
        return { key, value };
      })
      .filter(Boolean);
  }
  if (typeof raw === "object") {
    return Object.entries(raw)
      .map(([k, v]) => ({ key: toStringSafe(k), value: toStringSafe(v) }))
      .filter((x) => x.key && x.value);
  }
  if (typeof raw === "string") return [{ key: "关注分析", value: raw }];
  return [];
}

function formatPlaceholder(value, fallback = "-") {
  const text = toStringSafe(value);
  return text || fallback;
}

function parseNumberOrNull(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") {
    const cleaned = value.trim().replace(/[%％]/g, "");
    if (!cleaned) return null;
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : null;
  }
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatNumeric(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" && value.trim() === "") return "";
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  if (Math.abs(n - Math.round(n)) < 0.0001) return String(Math.round(n));
  return String(Math.round(n * 100) / 100);
}

function displayMetric(value) {
  const numeric = formatNumeric(value);
  return numeric || formatPlaceholder(value);
}

function splitSentenceLines(value) {
  if (Array.isArray(value)) {
    const rawItems = value.map((x) => toStringSafe(x)).filter(Boolean);
    const hasNumberedPattern = rawItems.some((x) => /^\d+[.)、]\s*/.test(x));
    if (!hasNumberedPattern) return rawItems;

    const mergedItems = [];
    let current = "";
    rawItems.forEach((line) => {
      const normalized = line.trim();
      if (!normalized) return;
      if (/^\d+[.)、]\s*/.test(normalized)) {
        if (current) mergedItems.push(current.trim());
        current = normalized;
        return;
      }
      current = current ? `${current} ${normalized}` : normalized;
    });
    if (current) mergedItems.push(current.trim());
    return mergedItems.length ? mergedItems : rawItems;
  }

  const text = toStringSafe(value);
  if (!text) return ["-"];

  const linesByNewline = text
    .split(/\n+/)
    .map((x) => x.trim())
    .filter(Boolean);
  if (linesByNewline.length > 1) return linesByNewline;

  const hasNumberedPattern = /\d+[.)、]\s*/.test(text);
  if (hasNumberedPattern) {
    const parts = text
      .split(/\s*(?=\d+[.)、]\s*)/)
      .map((x) => x.trim())
      .filter(Boolean);
    if (parts.length > 1) return parts;
  }

  const bySemicolon = text
    .split(/；|;/)
    .map((x) => x.trim())
    .filter(Boolean);
  if (bySemicolon.length > 1) return bySemicolon;

  return [text];
}

function cleanListItemText(value) {
  return toStringSafe(value).replace(/^\d+[.)、]\s*/, "").trim();
}

function readScoreBreakdown(item) {
  const scoreBreakdown = item && typeof item.score_breakdown === "object" ? item.score_breakdown : {};
  return {
    employment: displayMetric(scoreBreakdown["就业薪资"] ?? item?.就业薪资 ?? item?.employment_salary),
    rank: displayMetric(scoreBreakdown["学校排名"] ?? item?.学校排名 ?? item?.排名分 ?? item?.rank_score),
    region: displayMetric(scoreBreakdown["区域"] ?? scoreBreakdown["区域优势"] ?? item?.区域 ?? item?.region),
    curriculum: displayMetric(scoreBreakdown["课程"] ?? scoreBreakdown["课程适配"] ?? item?.课程 ?? item?.curriculum),
    cost: displayMetric(scoreBreakdown["成本"] ?? scoreBreakdown["成本控制"] ?? item?.成本 ?? item?.cost),
    visa: displayMetric(scoreBreakdown["工签"] ?? scoreBreakdown["工签支持"] ?? item?.工签 ?? item?.visa),
    alumni: displayMetric(scoreBreakdown["校友"] ?? scoreBreakdown["校友网络"] ?? item?.校友 ?? item?.alumni),
    h1b: displayMetric(scoreBreakdown["H1B"] ?? scoreBreakdown["H1B绿卡"] ?? item?.H1B ?? item?.h1b),
  };
}

function readOutlookText(item) {
  const direct = toStringSafe(item?.就业前景 ?? item?.outlook);
  if (direct) return direct;

  const concernRows = normalizeConcernAnalysis(
    item?.concern_analysis ?? item?.concerns ?? item?.concernAnalysis
  );
  if (!concernRows.length) return "";

  const priorityHit = concernRows.find((row) => /就业|薪资|工签|h1b|移民/i.test(toStringSafe(row.key)));
  if (priorityHit?.value) return toStringSafe(priorityHit.value);
  return toStringSafe(concernRows[0].value);
}

function toObjectSafe(value) {
  if (!value) return null;
  if (typeof value === "string") {
    const parsed = parseJsonLoose(value);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
    return null;
  }
  if (typeof value === "object" && !Array.isArray(value)) return value;
  return null;
}

function pickWeightByKeys(source, keys) {
  if (!source || typeof source !== "object") return null;
  for (const key of keys) {
    const n = parseNumberOrNull(source[key]);
    if (n !== null) return n;
  }
  return null;
}

function inferDimensionIdsFromRanking(rankingRowsRaw, schoolsRaw) {
  const firstRankingRow = rankingRowsRaw.find((x) => x && typeof x === "object") || null;
  const scoreBreakdown = firstRankingRow ? toObjectSafe(firstRankingRow.score_breakdown) : null;
  const present = new Set();

  RANKING_DIMENSION_CONFIG.forEach((dim) => {
    const hasFromBreakdown = scoreBreakdown
      ? dim.scoreKeys.some((k) => Object.prototype.hasOwnProperty.call(scoreBreakdown, k))
      : false;
    const hasFromRow = firstRankingRow
      ? dim.scoreKeys.some((k) => Object.prototype.hasOwnProperty.call(firstRankingRow, k))
      : false;
    if (hasFromBreakdown || hasFromRow) present.add(dim.id);
  });

  if (!present.size) {
    const firstSchool = schoolsRaw.find((x) => x && typeof x === "object") || null;
    if (firstSchool) {
      RANKING_DIMENSION_CONFIG.forEach((dim) => {
        const hasDim = dim.scoreKeys.some((k) => Object.prototype.hasOwnProperty.call(firstSchool, k));
        if (hasDim) present.add(dim.id);
      });
    }
  }

  if (!present.size) {
    RANKING_DIMENSION_CONFIG.forEach((dim) => present.add(dim.id));
  }
  return [...present];
}

function buildDimensionWeights(data, parsed, rankingRowsRaw, schoolsRaw) {
  const sources = [];
  const candidates = [
    data?.weights,
    data?.weights_json,
    data?.concerns_json,
    data?.concerns,
    parsed?.weights,
    parsed?.weights_json,
    parsed?.concerns_json,
    parsed?.concerns,
  ];

  candidates.forEach((value) => {
    const obj = toObjectSafe(value);
    if (!obj) return;
    sources.push(obj);
    const nestedWeights = toObjectSafe(obj.weights);
    if (nestedWeights) sources.push(nestedWeights);
    const nestedWeightMap = toObjectSafe(obj.weight_map);
    if (nestedWeightMap) sources.push(nestedWeightMap);
    const nestedWeightsJson = toObjectSafe(obj.weights_json);
    if (nestedWeightsJson) sources.push(nestedWeightsJson);
  });

  const dimensionWeights = {};
  RANKING_DIMENSION_CONFIG.forEach((dim) => {
    let weight = null;
    for (const source of sources) {
      weight = pickWeightByKeys(source, dim.weightKeys);
      if (weight !== null) break;
    }
    dimensionWeights[dim.id] = weight;
  });

  const allMissing = Object.values(dimensionWeights).every((v) => v === null);
  if (allMissing) {
    const inferredIds = inferDimensionIdsFromRanking(rankingRowsRaw, schoolsRaw);
    const share = inferredIds.length ? Math.round((100 / inferredIds.length) * 10) / 10 : null;
    inferredIds.forEach((id) => {
      dimensionWeights[id] = share;
    });
  } else {
    const missingIds = Object.keys(dimensionWeights).filter((id) => dimensionWeights[id] === null);
    if (missingIds.length) {
      const inferredIds = new Set(inferDimensionIdsFromRanking(rankingRowsRaw, schoolsRaw));
      const fillTargets = missingIds.filter((id) => inferredIds.has(id));
      if (fillTargets.length) {
        const existingTotal = Object.values(dimensionWeights)
          .filter((v) => v !== null)
          .reduce((sum, v) => sum + Number(v), 0);
        const remaining = Math.max(0, 100 - existingTotal);
        const share = Math.round((remaining / fillTargets.length) * 10) / 10;
        fillTargets.forEach((id) => {
          dimensionWeights[id] = share;
        });
      }
    }
  }

  return dimensionWeights;
}

function normalizeResultJson(data) {
  const parsed = parseJsonLoose(data.result_json) || parseJsonLoose(data.summary_markdown) || null;

  if (!parsed || typeof parsed !== "object") {
    return { ok: false, reason: "报告结构化解析失败，请稍后重试。", value: null };
  }

  const rankingRowsRaw = Array.isArray(parsed.comprehensive_ranking) ? parsed.comprehensive_ranking : [];
  const assessmentsRaw = Array.isArray(parsed.school_assessments) ? parsed.school_assessments : [];
  const schoolsRaw = Array.isArray(parsed.schools) ? parsed.schools : [];
  const rankingFallbackRaw = Array.isArray(data.ranking) ? data.ranking : [];
  const dimensionWeights = buildDimensionWeights(data, parsed, rankingRowsRaw, schoolsRaw);

  const rankingRowsFromFallback = rankingFallbackRaw.map((item, idx) => {
    const metrics = (item && typeof item.metrics === "object" && item.metrics) || {};
    const totalNumber = parseNumberOrNull(item?.total_score);
    return {
      rank: parseNumberOrNull(item?.rank) ?? idx + 1,
      school: formatPlaceholder(item?.school),
      program: formatPlaceholder(item?.program),
      totalNumber,
      totalText: totalNumber === null ? "-" : formatNumeric(totalNumber),
      dimensions: {
        employment: displayMetric(metrics["就业薪资"]),
        rank: displayMetric(metrics["学校排名"]),
        region: displayMetric(metrics["区域"] ?? metrics["区域优势"]),
        curriculum: displayMetric(metrics["课程"] ?? metrics["课程适配"]),
        cost: displayMetric(metrics["成本"] ?? metrics["成本控制"]),
        visa: displayMetric(metrics["工签"] ?? metrics["工签支持"]),
        alumni: displayMetric(metrics["校友"] ?? metrics["校友网络"]),
        h1b: displayMetric(metrics["H1B"] ?? metrics["H1B绿卡"]),
      },
    };
  }).sort((a, b) => Number(a.rank || 0) - Number(b.rank || 0));

  const rankingFallbackMap = new Map(
    rankingRowsFromFallback.map((x) => [`${x.school}::${x.program}`, x])
  );

  const rankingRows = rankingRowsRaw.length
    ? rankingRowsRaw.map((item, idx) => {
        const rankCandidate = parseNumberOrNull(item?.排名 ?? item?.rank ?? item?.名次 ?? item?.序号);
        const totalNumber = parseNumberOrNull(item?.总分 ?? item?.fit_score ?? item?.total_score ?? item?.score);
        const normalizedRank =
          rankCandidate !== null && rankCandidate >= 1 && rankCandidate <= rankingRowsRaw.length
            ? rankCandidate
            : idx + 1;

        const school = formatPlaceholder(item?.院校 ?? item?.学校 ?? item?.school ?? item?.school_name);
        const program = formatPlaceholder(item?.项目 ?? item?.program ?? item?.program_name);
        const fallback = rankingFallbackMap.get(`${school}::${program}`);
        const dimensions = readScoreBreakdown(item);

        return {
          rank: normalizedRank,
          school,
          program,
          totalNumber,
          totalText: totalNumber === null ? "-" : formatNumeric(totalNumber),
          dimensions: {
            employment: dimensions.employment === "-" ? fallback?.dimensions?.employment || "-" : dimensions.employment,
            rank: dimensions.rank === "-" ? fallback?.dimensions?.rank || "-" : dimensions.rank,
            region: dimensions.region === "-" ? fallback?.dimensions?.region || "-" : dimensions.region,
            curriculum: dimensions.curriculum === "-" ? fallback?.dimensions?.curriculum || "-" : dimensions.curriculum,
            cost: dimensions.cost === "-" ? fallback?.dimensions?.cost || "-" : dimensions.cost,
            visa: dimensions.visa === "-" ? fallback?.dimensions?.visa || "-" : dimensions.visa,
            alumni: dimensions.alumni === "-" ? fallback?.dimensions?.alumni || "-" : dimensions.alumni,
            h1b: dimensions.h1b === "-" ? fallback?.dimensions?.h1b || "-" : dimensions.h1b,
          },
        };
      })
    : rankingRowsFromFallback.length
      ? rankingRowsFromFallback
    : schoolsRaw.map((item, idx) => {
        const totalNumber = parseNumberOrNull(item?.fit_score ?? item?.fitScore ?? item?.score ?? item?.total_score);
        return {
          rank: idx + 1,
          school: formatPlaceholder(item?.school_name ?? item?.school ?? item?.学校 ?? item?.院校),
          program: formatPlaceholder(item?.program_name ?? item?.program ?? item?.项目),
          totalNumber,
          totalText: totalNumber === null ? "-" : formatNumeric(totalNumber),
          dimensions: readScoreBreakdown(item),
        };
      });

  const schoolAssessments = assessmentsRaw.length
    ? assessmentsRaw.map((item) => ({
        school: formatPlaceholder(item?.学校 ?? item?.院校 ?? item?.school ?? item?.school_name),
        program: formatPlaceholder(item?.项目 ?? item?.program ?? item?.program_name),
        totalCost: formatPlaceholder(item?.总成本 ?? item?.total_cost ?? item?.cost),
        pros: splitSentenceLines(item?.亮点 ?? item?.pros ?? item?.highlights),
        cons: splitSentenceLines(item?.短板 ?? item?.cons ?? item?.risks),
        outlook: formatPlaceholder(readOutlookText(item)),
        experience: formatPlaceholder(item?.experience ?? item?.就读体验),
        concernAnalysis: normalizeConcernAnalysis(item?.concern_analysis ?? item?.concerns),
        recommendedActions: splitSentenceLines(
          item?.recommended_actions ??
            item?.actions ??
            item?.行动建议
        ),
      }))
    : schoolsRaw.map((item) => ({
        school: formatPlaceholder(item?.school_name ?? item?.school ?? item?.学校 ?? item?.院校),
        program: formatPlaceholder(item?.program_name ?? item?.program ?? item?.项目),
        totalCost: formatPlaceholder(item?.总成本 ?? item?.total_cost ?? item?.cost),
        pros: splitSentenceLines(item?.亮点 ?? item?.pros ?? item?.highlights),
        cons: splitSentenceLines(item?.短板 ?? item?.cons ?? item?.risks),
        outlook: formatPlaceholder(
          readOutlookText(item) ||
            item?.就业前景 ||
            item?.outlook ||
            (Array.isArray(item?.recommended_actions) ? item.recommended_actions.join("；") : item?.recommended_actions)
        ),
        experience: formatPlaceholder(item?.experience ?? item?.就读体验),
        concernAnalysis: normalizeConcernAnalysis(item?.concern_analysis ?? item?.concerns),
        recommendedActions: splitSentenceLines(
          item?.recommended_actions ??
            item?.actions ??
            item?.行动建议
        ),
      }));

  return {
    ok: true,
    value: {
      rankingRows,
      dimensionWeights,
      schoolAssessments,
      finalRecommendation: formatPlaceholder(
        parsed.final_recommendation || parsed.finalRecommendation || parsed.recommendation || parsed.conclusion
      ),
      disclaimer: toStringSafe(parsed.disclaimer) || toStringSafe(data.disclaimer) || "本报告仅供参考。"
    }
  };
}

function normalizeReportStatus(status) {
  const s = toStringSafe(status).toLowerCase();
  if (["queued", "running", "pending", "generating"].includes(s)) return "loading";
  if (s === "failed") return "failed";
  if (["succeeded", "completed", "success"].includes(s)) return "success";
  return "loading";
}

function stopReportPolling() {
  if (state.reportPollTimer) {
    window.clearTimeout(state.reportPollTimer);
    state.reportPollTimer = null;
  }
}

function concernMatch(selectedSet, key) {
  if (!selectedSet || selectedSet.size === 0) return true;
  const k = toStringSafe(key);
  for (const s of selectedSet) {
    if (k.includes(s) || s.includes(k)) return true;
  }
  return false;
}

function resetReportArea() {
  stopReportPolling();
  els.reportError.classList.remove("report-loading-box");
  els.reportError.classList.add("hidden");
  els.executiveSummaryCard.classList.add("hidden");
  els.schoolsCards.classList.add("hidden");
  els.finalRecommendationCard.classList.add("hidden");
  els.reportDisclaimer.classList.add("hidden");

  els.reportError.innerHTML = "";
  els.executiveSummaryCard.innerHTML = "";
  els.schoolsCards.innerHTML = "";
  els.finalRecommendationCard.innerHTML = "";
  els.reportDisclaimer.textContent = "";
}

function setPdfVisible(visible, analysisId = "") {
  if (visible && analysisId) {
    els.pdfLink.dataset.analysisId = String(analysisId);
    els.pdfLink.classList.remove("hidden");
    return;
  }
  els.pdfLink.dataset.analysisId = "";
  els.pdfLink.classList.add("hidden");
}

function renderLoadingReport() {
  resetReportArea();
  setPdfVisible(false);
  els.reportError.classList.add("report-loading-box");
  els.reportError.innerHTML = `
    <div class="report-loading">
      <span class="report-spinner" aria-hidden="true"></span>
      <div>
        <strong>AI正在分析中，通常需要30-60秒...</strong>
      </div>
    </div>
  `;
  els.reportError.classList.remove("hidden");
}

async function retryReport(analysisId) {
  if (analysisId) {
    try {
      const retryData = await api(`/api/report/${analysisId}/retry`, { method: "POST" }, true);
      const nextId = retryData.analysis_id || retryData.id || analysisId;
      navigate(`/app/report/${nextId}`);
      renderResult({ ...retryData, analysis_id: nextId });
      return;
    } catch {
      // fallback to local resubmit
    }
  }

  if (state.lastAnalysisPayload) {
    await triggerAnalysis(state.lastAnalysisPayload, true);
    return;
  }
  alert("无法重新生成，请返回修改后再试");
}

function renderFailedReport(errorMessage, analysisId = "") {
  resetReportArea();
  setPdfVisible(false);
  els.reportError.innerHTML = `
    <p>分析生成失败</p>
    <p>${toStringSafe(errorMessage) || "报告结构化解析失败，请点击重新生成。"}</p>
    <div class="report-error-actions">
      <button id="retryAnalysisBtn" class="outline-btn" type="button">重新生成</button>
      <button id="backToSchoolsBtn" class="mini" type="button">返回修改</button>
    </div>
  `;
  els.reportError.classList.remove("hidden");

  const retryBtn = document.getElementById("retryAnalysisBtn");
  if (retryBtn) {
    retryBtn.addEventListener("click", async () => {
      await retryReport(analysisId || state.currentReportId);
    });
  }

  const backToSchoolsBtn = document.getElementById("backToSchoolsBtn");
  if (backToSchoolsBtn) {
    backToSchoolsBtn.addEventListener("click", () => navigate(ROUTES.STEP3));
  }
}

function renderStructuredReport(report) {
  resetReportArea();

  const totalNumbers = report.rankingRows.map((x) => x.totalNumber).filter((x) => Number.isFinite(x));
  const maxTotal = totalNumbers.length ? Math.max(...totalNumbers) : null;
  const dimensionWeights = report.dimensionWeights || {};

  function renderWeightText(dimId) {
    const weight = parseNumberOrNull(dimensionWeights[dimId]);
    return weight === null ? "-" : `${formatNumeric(weight)}%`;
  }

  function renderWeightedCell(rawValue, weightValue) {
    const raw = parseNumberOrNull(rawValue);
    const weight = parseNumberOrNull(weightValue);
    const weighted = raw !== null && weight !== null ? Math.round((raw * weight) / 10) / 10 : null;
    const weightedText = weighted === null ? "-" : formatNumeric(weighted);
    const rawText = raw === null ? "-" : formatNumeric(raw);
    return `
      <td class="metric-cell">
        <div class="metric-main">${weightedText}</div>
        <div class="metric-sub">原分:${rawText}</div>
      </td>
    `;
  }

  const rankingRowsHtml = report.rankingRows.length
    ? report.rankingRows
        .map((row) => {
          const isTop = maxTotal !== null && row.totalNumber === maxTotal;
          return `
            <tr class="${isTop ? "rank-top-row" : ""}">
              <td>${formatPlaceholder(row.rank)}</td>
              <td>${formatPlaceholder(row.school)}</td>
              <td>${formatPlaceholder(row.program)}</td>
              <td class="total-score">${formatPlaceholder(row.totalText)}</td>
              ${renderWeightedCell(row.dimensions.employment, dimensionWeights.employment)}
              ${renderWeightedCell(row.dimensions.rank, dimensionWeights.rank)}
              ${renderWeightedCell(row.dimensions.region, dimensionWeights.region)}
              ${renderWeightedCell(row.dimensions.curriculum, dimensionWeights.curriculum)}
              ${renderWeightedCell(row.dimensions.cost, dimensionWeights.cost)}
              ${renderWeightedCell(row.dimensions.visa, dimensionWeights.visa)}
              ${renderWeightedCell(row.dimensions.alumni, dimensionWeights.alumni)}
              ${renderWeightedCell(row.dimensions.h1b, dimensionWeights.h1b)}
            </tr>
          `;
        })
        .join("")
    : `
      <tr>
        <td colspan="12" class="ranking-empty">-</td>
      </tr>
    `;

  els.executiveSummaryCard.innerHTML = `
    <h3>综合排名</h3>
    <div class="table-wrap">
      <table class="ranking-table">
        <thead>
          <tr>
            <th>排名</th>
            <th>院校</th>
            <th>项目</th>
            <th>总分</th>
            <th><span class="th-main">就业薪资</span><span class="th-weight">(${renderWeightText("employment")})</span></th>
            <th><span class="th-main">学校排名</span><span class="th-weight">(${renderWeightText("rank")})</span></th>
            <th><span class="th-main">区域</span><span class="th-weight">(${renderWeightText("region")})</span></th>
            <th><span class="th-main">课程</span><span class="th-weight">(${renderWeightText("curriculum")})</span></th>
            <th><span class="th-main">成本</span><span class="th-weight">(${renderWeightText("cost")})</span></th>
            <th><span class="th-main">工签</span><span class="th-weight">(${renderWeightText("visa")})</span></th>
            <th><span class="th-main">校友</span><span class="th-weight">(${renderWeightText("alumni")})</span></th>
            <th><span class="th-main">H1B</span><span class="th-weight">(${renderWeightText("h1b")})</span></th>
          </tr>
        </thead>
        <tbody>${rankingRowsHtml}</tbody>
      </table>
    </div>
  `;
  els.executiveSummaryCard.classList.remove("hidden");

  els.schoolsCards.innerHTML = "";
  const assessmentsToRender = report.schoolAssessments.length
    ? report.schoolAssessments
    : [
        {
          school: "-",
          program: "-",
          totalCost: "-",
          pros: ["-"],
          cons: ["-"],
          outlook: "-",
          experience: "-",
          concernAnalysis: [],
          recommendedActions: ["-"],
        }
      ];

  assessmentsToRender.forEach((s) => {
    const card = document.createElement("article");
    card.className = "assessment-card";

    const prosHtml = s.pros
      .map((line) => `<li>${formatPlaceholder(cleanListItemText(line))}</li>`)
      .join("");
    const consHtml = s.cons
      .map((line) => `<li>${formatPlaceholder(cleanListItemText(line))}</li>`)
      .join("");
    const concernRows = Array.isArray(s.concernAnalysis) ? s.concernAnalysis.filter((x) => x?.key && x?.value) : [];
    const concernHtml = concernRows
      .map(
        (row) => `
          <div class="concern-item">
            <h5>${formatPlaceholder(row.key)}</h5>
            <p>${formatPlaceholder(row.value)}</p>
          </div>
        `
      )
      .join("");
    const actionsSource = Array.isArray(s.recommendedActions) ? s.recommendedActions : [];
    const actionsClean = actionsSource.map((x) => cleanListItemText(x)).filter(Boolean);
    const actionsHtml = (actionsClean.length ? actionsClean : ["-"])
      .map((line) => `<li>${formatPlaceholder(line)}</li>`)
      .join("");

    card.innerHTML = `
      <div class="assessment-head">
        <div class="assessment-head-left">
          <h3>${formatPlaceholder(s.school)}</h3>
          <p>${formatPlaceholder(s.program)}</p>
        </div>
        <div class="assessment-cost">${formatPlaceholder(s.totalCost)}</div>
      </div>

      <section class="assessment-outlook">
        <span>就业前景：</span>${formatPlaceholder(s.outlook)}
      </section>

      <div class="assessment-grid">
        <div class="assessment-col-left">
          <section class="assessment-section">
            <h4>亮点</h4>
            <ul class="pros-list">${prosHtml}</ul>
          </section>

          <section class="assessment-section">
            <h4>短板</h4>
            <ul class="cons-list">${consHtml}</ul>
          </section>

          <section class="assessment-section assessment-experience">
            <h4>就读体验</h4>
            <p>${formatPlaceholder(s.experience)}</p>
          </section>
        </div>

        <div class="assessment-col-right">
          ${concernRows.length ? `
            <section class="assessment-section concern-analysis">
              <h4>关注点深度分析</h4>
              ${concernHtml}
            </section>
          ` : ""}

          <section class="assessment-section assessment-actions">
            <h4>行动建议</h4>
            <ol class="actions-list">${actionsHtml}</ol>
          </section>
        </div>
      </div>
    `;
    els.schoolsCards.appendChild(card);
  });
  els.schoolsCards.classList.remove("hidden");

  els.finalRecommendationCard.innerHTML = `
    <h3>最终建议</h3>
    <p>${formatPlaceholder(report.finalRecommendation)}</p>
  `;
  els.finalRecommendationCard.classList.remove("hidden");

  els.reportDisclaimer.textContent = formatPlaceholder(report.disclaimer);
  els.reportDisclaimer.classList.remove("hidden");
}

async function pollReport(analysisId) {
  if (!analysisId) return;
  if (window.location.pathname !== `/app/report/${analysisId}`) {
    stopReportPolling();
    return;
  }

  try {
    const data = await api(`/api/report/${analysisId}`, {}, true);
    const merged = { ...data, analysis_id: data.id };
    renderResult(merged);
    if (normalizeReportStatus(merged.status) === "loading") {
      state.reportPollTimer = window.setTimeout(() => pollReport(analysisId), 1500);
    }
  } catch (e) {
    renderFailedReport(e.message || "报告加载失败", analysisId);
  }
}

function renderResult(data) {
  els.modelTag.textContent = `模型: ${data.model_used}`;
  state.currentReportId = String(data.analysis_id || data.id || "");

  const statusType = normalizeReportStatus(data.status);
  if (statusType === "loading") {
    renderLoadingReport();
    stopReportPolling();
    if (state.currentReportId) {
      state.reportPollTimer = window.setTimeout(() => pollReport(state.currentReportId), 1500);
    }
    return;
  }

  if (statusType === "failed") {
    renderFailedReport(data.error_message || "分析服务调用失败", state.currentReportId);
    return;
  }

  const parsed = normalizeResultJson(data);
  if (!parsed.ok) {
    renderFailedReport(parsed.reason || "报告结构化解析失败，请点击重新生成。", state.currentReportId);
    return;
  }

  setPdfVisible(true, state.currentReportId);
  renderStructuredReport(parsed.value);
}

function toRunPayload() {
  return {
    country: state.wizard.country,
    major: state.wizard.major || "CS",
    budget_max: Number(state.wizard.budget_max || 0),
    selected_dimensions: state.wizard.concerns || [],
    school_ids: [...state.selectedSchoolIds]
  };
}

async function triggerAnalysis(payload, keepCurrentRoute = false) {
  const tempId = `tmp-${Date.now()}`;
  upsertHistory({
    id: tempId,
    status: "generating",
    error_message: "",
    model_used: "deepseek-chat",
    createdAt: new Date().toISOString(),
    payload
  });

  state.lastAnalysisPayload = payload;
  if (!keepCurrentRoute) navigate(ROUTES.APP_HOME);
  renderHistoryList();

  try {
    const data = await api(
      "/api/analysis/run",
      {
        method: "POST",
        body: JSON.stringify(payload)
      },
      true
    );

    const item = {
      id: data.analysis_id,
      status: data.status,
      error_message: data.error_message || "",
      model_used: data.model_used,
      createdAt: new Date().toISOString(),
      payload
    };
    replaceHistoryId(tempId, item);

    navigate(`/app/report/${data.analysis_id}`);
    renderResult(data);
  } catch (e) {
    replaceHistoryId(tempId, {
      id: tempId,
      status: "failed",
      error_message: e.message || "分析失败",
      model_used: "deepseek-chat",
      createdAt: new Date().toISOString(),
      payload
    });

    navigate(`/app/report/${tempId}`);
    renderFailedReport(e.message || "分析生成失败");
  }
}

function hideAllPages() {
  [
    els.landingPage,
    els.appHero,
    els.authCard,
    els.appHomePage,
    els.stepNewPage,
    els.stepConcernsPage,
    els.stepSchoolsPage,
    els.stepConfirmPage,
    els.resultCard
  ].forEach((el) => el && el.classList.add("hidden"));
}

function isReportPath(path) {
  return /^\/app\/report\/.+/.test(path);
}

function getReportId(path) {
  const m = path.match(/^\/app\/report\/(.+)$/);
  return m ? m[1] : "";
}

function navigate(path, replace = false) {
  if (window.location.pathname === path) {
    renderRoute();
    return;
  }
  if (replace) window.history.replaceState({}, "", path);
  else window.history.pushState({}, "", path);
  renderRoute();
}

async function loadReportById(id) {
  stopReportPolling();
  const local = state.reportHistory.find((x) => String(x.id) === String(id));
  if (local && local.payload) state.lastAnalysisPayload = local.payload;

  if (!id || String(id).startsWith("tmp-")) {
    state.currentReportId = String(id || "");
    renderFailedReport(local?.error_message || "报告不存在或尚未生成", state.currentReportId);
    return;
  }

  try {
    const data = await api(`/api/report/${id}`, {}, true);
    const merged = { ...data, analysis_id: data.id };
    renderResult(merged);
    upsertHistory({
      id: data.id,
      status: data.status,
      error_message: data.error_message || "",
      model_used: data.model_used,
      createdAt: data.created_at,
      payload: local?.payload || state.lastAnalysisPayload || null
    });
  } catch (e) {
    renderFailedReport(e.message || "报告加载失败", String(id));
  }
}

async function renderRoute() {
  let path = window.location.pathname;
  if (path.length > 1 && path.endsWith("/")) path = path.replace(/\/+$/, "");
  if (!isReportPath(path)) stopReportPolling();

  if (!state.token && path !== ROUTES.LOGIN && path !== ROUTES.LANDING) {
    navigate(ROUTES.LOGIN, true);
    return;
  }

  if (state.token && path === ROUTES.LOGIN) {
    navigate(ROUTES.APP_HOME, true);
    return;
  }

  hideAllPages();

  if (path === ROUTES.LANDING) {
    document.body.classList.add("landing-mode");
    els.landingPage.classList.remove("hidden");
    return;
  }

  document.body.classList.remove("landing-mode");
  els.appHero.classList.remove("hidden");

  if (path === ROUTES.LOGIN) {
    els.authCard.classList.remove("hidden");
    return;
  }

  if (path === ROUTES.APP_HOME) {
    els.appHomePage.classList.remove("hidden");
    renderHistoryList();
    return;
  }

  if (path === ROUTES.STEP1) {
    await loadCountries();
    hydrateStep1();
    els.stepNewPage.classList.remove("hidden");
    return;
  }

  if (path === ROUTES.STEP2) {
    renderDimensions();
    els.stepConcernsPage.classList.remove("hidden");
    return;
  }

  if (path === ROUTES.STEP3) {
    await loadSchools();
    els.stepSchoolsPage.classList.remove("hidden");
    return;
  }

  if (path === ROUTES.STEP4) {
    await loadSchools();
    renderConfirmList();
    els.stepConfirmPage.classList.remove("hidden");
    return;
  }

  if (isReportPath(path)) {
    els.resultCard.classList.remove("hidden");
    await loadReportById(getReportId(path));
    return;
  }

  navigate(state.token ? ROUTES.APP_HOME : ROUTES.LOGIN, true);
}

async function loginSuccess(token) {
  setToken(token);
  await fetchMe();
  await loadCountries();
  navigate(ROUTES.APP_HOME, true);
}

async function autoLoginIfTokenExists() {
  if (!state.token) return;
  try {
    await fetchMe();
    await loadCountries();
  } catch {
    clearToken();
  }
}

function bindEvents() {
  window.addEventListener("popstate", () => {
    renderRoute();
  });

  document.querySelectorAll(".tab").forEach((t) => {
    t.addEventListener("click", () => switchAuthTab(t.dataset.tab));
  });

  document.getElementById("pwdModeBtn").addEventListener("click", () => switchLoginMode("pwd"));
  document.getElementById("codeModeBtn").addEventListener("click", () => switchLoginMode("code"));

  document.getElementById("sendRegCode").addEventListener("click", async () => {
    try {
      await sendCode(document.getElementById("regPhone").value.trim(), "register", els.authTip);
    } catch (e) {
      tip(els.authTip, e.message, true);
    }
  });

  document.getElementById("registerBtn").addEventListener("click", async () => {
    try {
      const payload = {
        phone: document.getElementById("regPhone").value.trim(),
        code: document.getElementById("regCode").value.trim(),
        password: document.getElementById("regPassword").value
      };
      const data = await api("/api/auth/register", { method: "POST", body: JSON.stringify(payload) });
      tip(els.authTip, "注册成功，已登录。", false);
      await loginSuccess(data.access_token);
    } catch (e) {
      tip(els.authTip, e.message, true);
    }
  });

  document.getElementById("loginPwdBtn").addEventListener("click", async () => {
    try {
      const payload = {
        phone: document.getElementById("loginPhonePwd").value.trim(),
        password: document.getElementById("loginPassword").value
      };
      const data = await api("/api/auth/login/password", { method: "POST", body: JSON.stringify(payload) });
      tip(els.authTip, "登录成功。", false);
      await loginSuccess(data.access_token);
    } catch (e) {
      tip(els.authTip, e.message, true);
    }
  });

  document.getElementById("sendLoginCode").addEventListener("click", async () => {
    try {
      await sendCode(document.getElementById("loginPhoneCode").value.trim(), "login", els.authTip);
    } catch (e) {
      tip(els.authTip, e.message, true);
    }
  });

  document.getElementById("loginCodeBtn").addEventListener("click", async () => {
    try {
      const payload = {
        phone: document.getElementById("loginPhoneCode").value.trim(),
        code: document.getElementById("loginCode").value.trim()
      };
      const data = await api("/api/auth/login/code", { method: "POST", body: JSON.stringify(payload) });
      tip(els.authTip, "登录成功。", false);
      await loginSuccess(data.access_token);
    } catch (e) {
      tip(els.authTip, e.message, true);
    }
  });

  document.getElementById("logoutBtn").addEventListener("click", () => {
    clearToken();
    navigate(ROUTES.LOGIN, true);
  });

  document.getElementById("newReportBtn").addEventListener("click", () => {
    navigate(ROUTES.STEP1);
  });

  document.getElementById("appBackLandingBtn").addEventListener("click", () => {
    navigate(ROUTES.LANDING);
  });

  document.getElementById("reportBackHomeBtn").addEventListener("click", () => {
    navigate(ROUTES.APP_HOME);
  });

  document.getElementById("step1BackBtn").addEventListener("click", () => navigate(ROUTES.APP_HOME));
  document.getElementById("step1NextBtn").addEventListener("click", () => {
    const oldCountry = state.wizard.country;
    const country = els.countrySelect.value;
    const major = els.majorInput.value.trim();
    if (!country) {
      alert("请选择留学地区");
      return;
    }
    if (!major) {
      alert("请输入专业方向");
      return;
    }

    state.wizard.country = country;
    state.wizard.major = major;
    state.wizard.budget_max = Number(els.budgetInput.value || 0);

    if (oldCountry && oldCountry !== country) {
      state.selectedSchoolIds.clear();
      state.wizard.school_ids = [];
      state.schools = [];
      state.schoolsCountry = "";
      els.schoolSearch.value = "";
    }

    saveWizardDraft();
    navigate(ROUTES.STEP2);
  });

  document.getElementById("step2BackBtn").addEventListener("click", () => navigate(ROUTES.STEP1));
  document.getElementById("step2NextBtn").addEventListener("click", () => {
    syncWizardConcernsFromUI();
    if (!state.wizard.concerns.length) {
      alert("请至少选择一个关注点");
      return;
    }
    navigate(ROUTES.STEP3);
  });

  document.getElementById("step3BackBtn").addEventListener("click", () => navigate(ROUTES.STEP2));
  document.getElementById("step3NextBtn").addEventListener("click", () => {
    if (!state.selectedSchoolIds.size) {
      alert("请至少选择一个学校项目");
      return;
    }
    saveWizardDraft();
    navigate(ROUTES.STEP4);
  });

  document.getElementById("step4BackBtn").addEventListener("click", () => navigate(ROUTES.STEP3));

  els.schoolSearch.addEventListener("input", () => {
    renderSchoolsBySearch();
  });

  document.getElementById("uploadExcelBtn").addEventListener("click", async () => {
    const fileInput = document.getElementById("excelInput");
    if (!fileInput.files || !fileInput.files[0]) {
      tip(els.excelTip, "请先选择Excel文件", true);
      return;
    }

    try {
      const form = new FormData();
      form.append("file", fileInput.files[0]);

      const country = state.wizard.country;
      const response = await fetch(`/api/schools/upload-excel?country=${encodeURIComponent(country)}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${state.token}` },
        body: form
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Excel识别失败");

      data.matched_school_ids.forEach((id) => state.selectedSchoolIds.add(id));
      saveWizardDraft();
      renderSchoolsBySearch();
      renderSelectedSummary();
      renderConfirmList();

      tip(
        els.excelTip,
        `已匹配 ${data.matched_school_ids.length} 项。` +
          (data.unmatched_cells.length ? ` 未匹配样本: ${data.unmatched_cells.slice(0, 5).join(" / ")}` : "")
      );
    } catch (e) {
      tip(els.excelTip, e.message, true);
    }
  });

  document.getElementById("runAnalysisBtn").addEventListener("click", async () => {
    if (!state.selectedSchoolIds.size) {
      alert("请至少选择一个学校项目");
      return;
    }
    const payload = toRunPayload();
    if (!payload.country || !payload.major || !payload.selected_dimensions.length || !payload.school_ids.length) {
      alert("信息不完整，请返回上一步检查");
      return;
    }
    await triggerAnalysis(payload);
  });

  document.getElementById("pdfLink").addEventListener("click", async (e) => {
    e.preventDefault();
    const analysisId = els.pdfLink.dataset.analysisId;
    if (!analysisId) {
      alert("请先生成可下载的分析结果");
      return;
    }

    try {
      const response = await fetch(`/api/analysis/${analysisId}/pdf`, {
        method: "GET",
        headers: { Authorization: `Bearer ${state.token}` }
      });
      if (!response.ok) {
        let detail = "下载PDF失败";
        try {
          const data = await response.json();
          detail = data.detail || detail;
        } catch {
          // no-op
        }
        throw new Error(detail);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `study_report_${analysisId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message || "下载PDF失败");
    }
  });

  const landingStartTopBtn = document.getElementById("landingStartTopBtn");
  if (landingStartTopBtn) {
    landingStartTopBtn.addEventListener("click", () => navigate(ROUTES.LOGIN));
  }

  const landingStartBtn = document.getElementById("landingStartBtn");
  if (landingStartBtn) {
    landingStartBtn.addEventListener("click", () => navigate(ROUTES.LOGIN));
  }
}

async function bootstrap() {
  bindEvents();
  await autoLoginIfTokenExists();
  await renderRoute();
}

bootstrap();
