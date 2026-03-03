const ROUTES = {
  LANDING: "/",
  LOGIN: "/login",
  APP_HOME: "/app",
  CATALOG: "/app/catalog",
  CATALOG_SCHOOL_PREFIX: "/app/catalog/school",
  CATALOG_PROGRAM_PREFIX: "/app/catalog/program",
  ADMIN: "/app/admin",
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

const CONCERN_DIMENSIONS = [
  { key: "employment", label: "就业前景", icon: "💼", desc: "毕业后找工作的难易度和质量" },
  { key: "salary", label: "薪资水平", icon: "💰", desc: "毕业起薪和5年薪资潜力" },
  { key: "visa", label: "签证/移民", icon: "🛂", desc: "工作签证、PR路径的便利程度" },
  { key: "ranking", label: "学校排名", icon: "🏆", desc: "QS/US News等权威排名" },
  { key: "cost", label: "总体费用", icon: "📊", desc: "学费+生活费的综合成本" },
  { key: "returnee", label: "回国认可", icon: "🇨🇳", desc: "国内雇主和社会对该学历的认可度" },
  { key: "location", label: "地理位置", icon: "📍", desc: "就业圈、城市繁荣度、生活便利性" },
  { key: "curriculum", label: "课程质量", icon: "📚", desc: "课程设置、方向匹配、选课灵活度" },
  { key: "workload", label: "读书压力", icon: "😮‍💨", desc: "课业难度和学习强度" },
  { key: "safety", label: "安全环境", icon: "🛡️", desc: "城市治安和生活安全感" },
  { key: "living", label: "生活质量", icon: "🌆", desc: "娱乐、饮食、华人社区、气候" },
  { key: "alumni", label: "校友资源", icon: "🤝", desc: "校友网络强度和内推机会" },
  { key: "academic", label: "学术声誉", icon: "🔬", desc: "科研实力和学术排名" },
];
const CONCERN_MAP = Object.fromEntries(CONCERN_DIMENSIONS.map((x) => [x.key, x]));
const LEGACY_CONCERN_KEY_MAP = {
  学历提升: "academic",
  学费压力: "cost",
  学校排名: "ranking",
  当地就业: "employment",
  就业去向: "employment",
  移民: "visa",
  薪资: "salary",
  回国认可度: "returnee",
  读书压力: "workload",
  课程难度: "workload",
  安全度: "safety",
  生活开销: "cost",
  生活质量: "living",
  H1B移民: "visa",
};
const MIN_CONCERNS = 2;
const MAX_CONCERNS = 6;

const WIZARD_KEY = "wizardDraft";
const HISTORY_KEY = "analysisHistory";

function normalizeConcernKeys(values) {
  const result = [];
  const seen = new Set();
  const source = Array.isArray(values) ? values : [];
  source.forEach((raw) => {
    if (!raw) return;
    const key = LEGACY_CONCERN_KEY_MAP[raw] || String(raw).trim();
    if (!CONCERN_MAP[key] || seen.has(key)) return;
    seen.add(key);
    result.push(key);
  });
  return result;
}

function calcConcernWeights(orderedKeys) {
  const keys = normalizeConcernKeys(orderedKeys);
  const n = keys.length;
  if (!n) return {};
  const denominator = n * (n + 1) / 2;
  const weights = {};
  let used = 0;
  keys.forEach((key, index) => {
    if (index === n - 1) {
      weights[key] = Math.max(0, 100 - used);
      return;
    }
    const rank = index + 1;
    const value = Math.round((n - rank + 1) / denominator * 100);
    weights[key] = value;
    used += value;
  });
  return weights;
}

function loadWizardDraft() {
  try {
    const raw = localStorage.getItem(WIZARD_KEY);
    if (!raw) {
      const concerns = ["employment", "salary", "visa"];
      return {
        country: "",
        major: "CS",
        budget_max: 70000,
        concerns,
        weights: calcConcernWeights(concerns),
        school_ids: []
      };
    }
    const parsed = JSON.parse(raw);
    const concerns = normalizeConcernKeys(parsed.concerns || parsed.selected_dimensions);
    return {
      country: parsed.country || "",
      major: parsed.major || "CS",
      budget_max: Number(parsed.budget_max || 70000),
      concerns: concerns.length ? concerns : ["employment", "salary", "visa"],
      weights: typeof parsed.weights === "object" && parsed.weights ? parsed.weights : calcConcernWeights(concerns.length ? concerns : ["employment", "salary", "visa"]),
      school_ids: Array.isArray(parsed.school_ids) ? parsed.school_ids : []
    };
  } catch {
    const concerns = ["employment", "salary", "visa"];
    return {
      country: "",
      major: "CS",
      budget_max: 70000,
      concerns,
      weights: calcConcernWeights(concerns),
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
  catalogSchools: [],
  catalogRankingSource: "qs",
  currentCatalogSchoolName: "",
  currentCatalogProgramId: 0,
  adminSchools: [],
  adminInsights: [],
  adminChatMessages: [],
  adminMemory: null,
  adminActiveTab: "insights",
  selectedSchoolIds: new Set(),
  reportPollTimer: null,
  currentReportId: null,
  lastAnalysisPayload: null,
  wizard: loadWizardDraft(),
  reportHistory: loadReportHistory(),
  concernsStage: "select",
  concernsDragKey: "",
};

state.selectedSchoolIds = new Set(state.wizard.school_ids || []);
ensureWizardConcernState();

const els = {
  landingPage: document.getElementById("landingPage"),
  appHero: document.getElementById("appHero"),
  globalTopNav: document.getElementById("globalTopNav"),
  topNavSchoolBtn: document.getElementById("topNavSchoolBtn"),
  topNavAdviceBtn: document.getElementById("topNavAdviceBtn"),
  topNavAdminBtn: document.getElementById("topNavAdminBtn"),
  topNavUserRole: document.getElementById("topNavUserRole"),
  authCard: document.getElementById("authCard"),
  appHomePage: document.getElementById("appHomePage"),
  schoolCatalogPage: document.getElementById("schoolCatalogPage"),
  schoolDetailPage: document.getElementById("schoolDetailPage"),
  programDetailPage: document.getElementById("programDetailPage"),
  adminPage: document.getElementById("adminPage"),
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
  concernSelectStage: document.getElementById("concernSelectStage"),
  concernSortStage: document.getElementById("concernSortStage"),
  dimensionCardGrid: document.getElementById("dimensionCardGrid"),
  dimensionSelectHint: document.getElementById("dimensionSelectHint"),
  dimensionSortList: document.getElementById("dimensionSortList"),
  schoolSearch: document.getElementById("schoolSearch"),

  modelTag: document.getElementById("modelTag"),
  reportError: document.getElementById("reportError"),
  executiveSummaryCard: document.getElementById("executiveSummaryCard"),
  schoolsCards: document.getElementById("schoolsCards"),
  finalRecommendationCard: document.getElementById("finalRecommendationCard"),
  reportDisclaimer: document.getElementById("reportDisclaimer"),
  pdfLink: document.getElementById("pdfLink"),

  catalogRankQsBtn: document.getElementById("catalogRankQsBtn"),
  catalogRankUsnewsBtn: document.getElementById("catalogRankUsnewsBtn"),
  catalogRankTimesBtn: document.getElementById("catalogRankTimesBtn"),
  catalogCountTip: document.getElementById("catalogCountTip"),
  catalogSearchInput: document.getElementById("catalogSearchInput"),
  catalogList: document.getElementById("catalogList"),
  catalogBackHomeBtn: document.getElementById("catalogBackHomeBtn"),
  schoolDetailTitle: document.getElementById("schoolDetailTitle"),
  schoolDetailRankings: document.getElementById("schoolDetailRankings"),
  schoolDetailMeta: document.getElementById("schoolDetailMeta"),
  schoolDetailPrograms: document.getElementById("schoolDetailPrograms"),
  schoolDetailBackBtn: document.getElementById("schoolDetailBackBtn"),
  programDetailTitle: document.getElementById("programDetailTitle"),
  programDetailMeta: document.getElementById("programDetailMeta"),
  programDetailCourses: document.getElementById("programDetailCourses"),
  programDetailNotes: document.getElementById("programDetailNotes"),
  programDetailBackBtn: document.getElementById("programDetailBackBtn"),

  adminTabSchoolsBtn: document.getElementById("adminTabSchoolsBtn"),
  adminTabInsightsBtn: document.getElementById("adminTabInsightsBtn"),
  adminSchoolsPanel: document.getElementById("adminSchoolsPanel"),
  adminInsightsPanel: document.getElementById("adminInsightsPanel"),
  adminBackHomeBtn: document.getElementById("adminBackHomeBtn"),
  adminSchoolQuery: document.getElementById("adminSchoolQuery"),
  adminSchoolRefreshBtn: document.getElementById("adminSchoolRefreshBtn"),
  adminExcelInput: document.getElementById("adminExcelInput"),
  adminImportBtn: document.getElementById("adminImportBtn"),
  adminDownloadTemplateBtn: document.getElementById("adminDownloadTemplateBtn"),
  adminSchoolTip: document.getElementById("adminSchoolTip"),
  adminSchoolsTableBody: document.getElementById("adminSchoolsTableBody"),
  adminInsightStatus: document.getElementById("adminInsightStatus"),
  adminInsightQuery: document.getElementById("adminInsightQuery"),
  adminInsightRefreshBtn: document.getElementById("adminInsightRefreshBtn"),
  adminInsightTip: document.getElementById("adminInsightTip"),
  adminInsightsList: document.getElementById("adminInsightsList"),
  adminRagCountryInput: document.getElementById("adminRagCountryInput"),
  adminRagMajorInput: document.getElementById("adminRagMajorInput"),
  adminQuickSearch5Btn: document.getElementById("adminQuickSearch5Btn"),
  adminQuickSearch10Btn: document.getElementById("adminQuickSearch10Btn"),
  adminQuickMemoryBtn: document.getElementById("adminQuickMemoryBtn"),
  adminChatMessages: document.getElementById("adminChatMessages"),
  adminChatInput: document.getElementById("adminChatInput"),
  adminChatSendBtn: document.getElementById("adminChatSendBtn"),
  adminMemoryRefreshBtn: document.getElementById("adminMemoryRefreshBtn"),
  adminMemoryStats: document.getElementById("adminMemoryStats"),
  adminMemoryLongTerm: document.getElementById("adminMemoryLongTerm"),
  adminMemoryMeta: document.getElementById("adminMemoryMeta"),
  adminMemoryRetryList: document.getElementById("adminMemoryRetryList"),
  adminMemoryEditor: document.getElementById("adminMemoryEditor"),
  adminMemorySaveBtn: document.getElementById("adminMemorySaveBtn"),
  adminMemoryTip: document.getElementById("adminMemoryTip"),
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isAdminUser() {
  return state.currentUser?.role === "admin";
}

function updateGlobalTopNav(path) {
  const showNav =
    path === ROUTES.LANDING ||
    path === ROUTES.APP_HOME ||
    path.startsWith(ROUTES.CATALOG) ||
    path === ROUTES.ADMIN ||
    isReportPath(path);
  if (!els.globalTopNav) return;
  els.globalTopNav.classList.toggle("hidden", !showNav);

  if (els.topNavAdminBtn) {
    els.topNavAdminBtn.classList.toggle("hidden", !isAdminUser());
  }

  if (els.topNavUserRole) {
    const roleText = state.currentUser?.role ? `当前身份：${state.currentUser.role}` : "";
    els.topNavUserRole.textContent = roleText;
    els.topNavUserRole.classList.toggle("hidden", !roleText);
  }
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

function ensureWizardConcernState() {
  const concerns = normalizeConcernKeys(state.wizard.concerns);
  state.wizard.concerns = concerns.length ? concerns : ["employment", "salary", "visa"];
  const stored = state.wizard.weights && typeof state.wizard.weights === "object" ? state.wizard.weights : {};
  const normalized = {};
  state.wizard.concerns.forEach((key) => {
    const value = Number(stored[key]);
    if (Number.isFinite(value) && value > 0) normalized[key] = Math.round(value);
  });
  if (Object.keys(normalized).length !== state.wizard.concerns.length) {
    state.wizard.weights = calcConcernWeights(state.wizard.concerns);
  } else {
    const total = Object.values(normalized).reduce((sum, x) => sum + x, 0);
    if (total <= 0) {
      state.wizard.weights = calcConcernWeights(state.wizard.concerns);
    } else {
      const corrected = {};
      let used = 0;
      state.wizard.concerns.forEach((key, idx) => {
        if (idx === state.wizard.concerns.length - 1) {
          corrected[key] = Math.max(0, 100 - used);
        } else {
          const v = Math.round((normalized[key] / total) * 100);
          corrected[key] = v;
          used += v;
        }
      });
      state.wizard.weights = corrected;
    }
  }
}

function calcConcernWeightsStrict(ordered) {
  return calcConcernWeights(ordered);
}

function renderConcernSelectionHint() {
  const count = state.wizard.concerns.length;
  const maxed = count >= MAX_CONCERNS;
  let text = `已选 ${count} 个，建议选3-5个重点关注维度`;
  if (maxed) text += "。最多选6个，如需更换请先取消已选项";
  tip(els.dimensionSelectHint, text, false);
}

function toggleConcernSelection(key) {
  const list = normalizeConcernKeys(state.wizard.concerns);
  const exists = list.includes(key);
  if (exists) {
    state.wizard.concerns = list.filter((x) => x !== key);
  } else {
    if (list.length >= MAX_CONCERNS) {
      renderConcernSelectionHint();
      return;
    }
    state.wizard.concerns = [...list, key];
  }
  state.wizard.weights = calcConcernWeightsStrict(state.wizard.concerns);
  renderConcernsSelectStage();
  saveWizardDraft();
}

function renderConcernsSelectStage() {
  ensureWizardConcernState();
  const selected = new Set(state.wizard.concerns);
  const maxed = selected.size >= MAX_CONCERNS;
  els.dimensionCardGrid.innerHTML = "";
  CONCERN_DIMENSIONS.forEach((item) => {
    const isSelected = selected.has(item.key);
    const disabled = maxed && !isSelected;
    const card = document.createElement("button");
    card.type = "button";
    card.className = `dimension-card${isSelected ? " selected" : ""}${disabled ? " disabled" : ""}`;
    card.setAttribute("aria-pressed", isSelected ? "true" : "false");
    card.dataset.key = item.key;
    card.innerHTML = `
      <span class="dimension-icon">${item.icon}</span>
      <strong>${item.label}</strong>
      <small>${item.desc}</small>
      <span class="dimension-check">${isSelected ? "✓" : ""}</span>
    `;
    card.addEventListener("click", () => toggleConcernSelection(item.key));
    els.dimensionCardGrid.appendChild(card);
  });
  renderConcernSelectionHint();
  const nextBtn = document.getElementById("step2ToSortBtn");
  if (nextBtn) nextBtn.disabled = selected.size < MIN_CONCERNS;
}

function moveConcernKey(fromKey, toKey) {
  if (!fromKey || !toKey || fromKey === toKey) return;
  const list = [...state.wizard.concerns];
  const fromIndex = list.indexOf(fromKey);
  const toIndex = list.indexOf(toKey);
  if (fromIndex < 0 || toIndex < 0) return;
  const [moved] = list.splice(fromIndex, 1);
  list.splice(toIndex, 0, moved);
  state.wizard.concerns = list;
  state.wizard.weights = calcConcernWeightsStrict(list);
  renderConcernsSortStage();
  saveWizardDraft();
}

function renderConcernsSortStage() {
  ensureWizardConcernState();
  const weights = calcConcernWeightsStrict(state.wizard.concerns);
  state.wizard.weights = weights;
  const selected = state.wizard.concerns;
  els.dimensionSortList.innerHTML = "";

  selected.forEach((key, idx) => {
    const item = CONCERN_MAP[key];
    const row = document.createElement("div");
    row.className = "dimension-sort-item";
    row.draggable = true;
    row.dataset.key = key;
    const weight = Number(weights[key] || 0);
    row.innerHTML = `
      <div class="sort-left">
        <span class="drag-handle" title="拖拽排序">⠿</span>
        <span class="sort-rank">${idx + 1}</span>
        <div class="sort-title">
          <strong>${item?.label || key}</strong>
          <small>${item?.desc || "-"}</small>
        </div>
      </div>
      <div class="sort-right">
        <div class="sort-bar"><span style="width:${weight}%"></span></div>
        <b>${weight}%</b>
      </div>
    `;

    row.addEventListener("dragstart", () => {
      state.concernsDragKey = key;
      row.classList.add("dragging");
    });
    row.addEventListener("dragover", (event) => {
      event.preventDefault();
      row.classList.add("drag-over");
    });
    row.addEventListener("dragleave", () => row.classList.remove("drag-over"));
    row.addEventListener("drop", (event) => {
      event.preventDefault();
      row.classList.remove("drag-over");
      moveConcernKey(state.concernsDragKey, key);
      state.concernsDragKey = "";
    });
    row.addEventListener("dragend", () => {
      state.concernsDragKey = "";
      row.classList.remove("dragging");
      row.classList.remove("drag-over");
    });

    row.addEventListener("touchstart", (event) => {
      if (!event.target.closest(".drag-handle")) return;
      state.concernsDragKey = key;
      row.classList.add("dragging");
    }, { passive: true });

    els.dimensionSortList.appendChild(row);
  });

  els.dimensionSortList.ontouchmove = (event) => {
    if (!state.concernsDragKey) return;
    event.preventDefault();
    const touch = event.touches[0];
    const target = document.elementFromPoint(touch.clientX, touch.clientY)?.closest(".dimension-sort-item");
    if (!target) return;
    const targetKey = target.dataset.key || "";
    if (targetKey && targetKey !== state.concernsDragKey) {
      moveConcernKey(state.concernsDragKey, targetKey);
    }
  };
  els.dimensionSortList.ontouchend = () => {
    state.concernsDragKey = "";
    els.dimensionSortList.querySelectorAll(".dimension-sort-item").forEach((node) => node.classList.remove("dragging", "drag-over"));
  };
}

function setConcernsStage(stage) {
  state.concernsStage = stage === "sort" ? "sort" : "select";
  const isSort = state.concernsStage === "sort";
  els.concernSelectStage.classList.toggle("concern-stage-collapsed", isSort);
  els.concernSortStage.classList.toggle("concern-stage-collapsed", !isSort);
  if (isSort) renderConcernsSortStage();
  else renderConcernsSelectStage();
}

function renderConcernsStep() {
  ensureWizardConcernState();
  if (state.wizard.concerns.length >= MIN_CONCERNS && state.concernsStage === "sort") {
    setConcernsStage("sort");
  } else {
    setConcernsStage("select");
  }
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

function setCatalogRankButtonActive() {
  if (els.catalogRankQsBtn) els.catalogRankQsBtn.classList.toggle("active", state.catalogRankingSource === "qs");
  if (els.catalogRankUsnewsBtn) els.catalogRankUsnewsBtn.classList.toggle("active", state.catalogRankingSource === "usnews");
  if (els.catalogRankTimesBtn) els.catalogRankTimesBtn.classList.toggle("active", state.catalogRankingSource === "times");
}

function renderCatalogList() {
  if (!els.catalogList) return;
  const list = state.catalogSchools || [];
  if (els.catalogCountTip) {
    els.catalogCountTip.textContent = `当前共 ${list.length} 所学校（按${state.catalogRankingSource.toUpperCase()}排序）`;
  }

  els.catalogList.innerHTML = "";
  if (!list.length) {
    els.catalogList.innerHTML = '<div class="history-empty">暂无可展示学校</div>';
    return;
  }

  list.forEach((s) => {
    const row = document.createElement("div");
    row.className = "catalog-item";
    const rankText = Number(s.display_rank || 0) > 0 ? `#${formatNumeric(s.display_rank)}` : "-";
    row.innerHTML = `
      <div class="catalog-main">
        <div class="school-title">${formatPlaceholder(s.school_name)}</div>
        <div class="school-meta">${formatPlaceholder((s.countries || []).join(" / "), "国家未知")} · 项目数 ${formatPlaceholder(s.program_count, 0)}</div>
        <div class="school-meta">示例项目：${formatPlaceholder((s.sample_programs || []).join(" / "), "-")}</div>
      </div>
      <div class="catalog-metrics">
        <span>${state.catalogRankingSource.toUpperCase()} 排名 ${rankText}</span>
        <span>平均学费 $${formatNumeric(s.avg_tuition_usd) || "-"}</span>
        <span>平均生活费 $${formatNumeric(s.avg_living_cost_usd) || "-"}</span>
        <button class="mini" type="button">查看学校详情</button>
      </div>
    `;
    row.querySelector("button").addEventListener("click", () => {
      navigate(`${ROUTES.CATALOG_SCHOOL_PREFIX}/${encodeURIComponent(s.school_name)}`);
    });
    els.catalogList.appendChild(row);
  });
}

async function loadCatalogSchools() {
  setCatalogRankButtonActive();
  const keyword = (els.catalogSearchInput?.value || "").trim();
  const data = await api(
    `/api/school-directory?ranking_source=${encodeURIComponent(state.catalogRankingSource)}&q=${encodeURIComponent(keyword)}`,
    {},
    true
  );
  state.catalogSchools = Array.isArray(data) ? data : [];
  renderCatalogList();
}

async function loadCatalogSchoolDetail(schoolName) {
  const data = await api(
    `/api/school-directory/${encodeURIComponent(schoolName)}?ranking_source=${encodeURIComponent(state.catalogRankingSource)}`,
    {},
    true
  );
  state.currentCatalogSchoolName = schoolName;
  return data;
}

function renderSchoolDetail(data) {
  if (!data || !els.schoolDetailPage) return;
  els.schoolDetailTitle.textContent = formatPlaceholder(data.school_name);
  const rankings = data.rankings || {};
  els.schoolDetailRankings.innerHTML = `
    <span class="insight-tag">QS：${displayMetric(rankings.qs)}</span>
    <span class="insight-tag">USNews：${displayMetric(rankings.usnews)}</span>
    <span class="insight-tag">泰晤士：${displayMetric(rankings.times)}</span>
  `;
  els.schoolDetailMeta.textContent = `国家：${formatPlaceholder((data.countries || []).join(" / "), "-")}｜项目数：${formatPlaceholder(data.program_count, 0)}｜平均学费：$${formatNumeric(data.avg_tuition_usd) || "-"}`;
  const programs = Array.isArray(data.programs) ? data.programs : [];
  els.schoolDetailPrograms.innerHTML = "";
  if (!programs.length) {
    els.schoolDetailPrograms.innerHTML = '<div class="history-empty">暂无项目</div>';
    return;
  }
  programs.forEach((p) => {
    const row = document.createElement("div");
    row.className = "catalog-item";
    row.innerHTML = `
      <div class="catalog-main">
        <div class="school-title">${formatPlaceholder(p.program_name)}</div>
        <div class="school-meta">${formatPlaceholder(p.major_track)} / ${formatPlaceholder(p.degree)}</div>
      </div>
      <div class="catalog-metrics">
        <span>时长 ${displayMetric(p.program_duration_months)} 月</span>
        <span>课程数 ${displayMetric(p.course_count)}</span>
        <span>学费 $${formatNumeric(p.tuition_usd) || "-"}</span>
        <button class="mini" type="button">查看项目详情</button>
      </div>
    `;
    row.querySelector("button").addEventListener("click", () => {
      navigate(`${ROUTES.CATALOG_PROGRAM_PREFIX}/${encodeURIComponent(p.id)}`);
    });
    els.schoolDetailPrograms.appendChild(row);
  });
}

async function loadProgramDetail(programId) {
  const data = await api(`/api/school-programs/${encodeURIComponent(programId)}`, {}, true);
  state.currentCatalogProgramId = Number(programId) || 0;
  return data;
}

function renderProgramDetail(data) {
  if (!data) return;
  els.programDetailTitle.textContent = `${formatPlaceholder(data.school_name)} · ${formatPlaceholder(data.program_name)}`;
  els.programDetailMeta.innerHTML = `
    <span class="insight-tag">QS：${displayMetric(data.qs_rank)}</span>
    <span class="insight-tag">USNews：${displayMetric(data.usnews_rank)}</span>
    <span class="insight-tag">泰晤士：${displayMetric(data.times_rank)}</span>
    <span class="insight-tag">时长：${displayMetric(data.program_duration_months)} 月</span>
    <span class="insight-tag">学费：$${formatNumeric(data.tuition_usd) || "-"}</span>
    <span class="insight-tag">生活费：$${formatNumeric(data.living_cost_usd) || "-"}</span>
  `;
  const courses = Array.isArray(data.course_list_json) ? data.course_list_json : [];
  els.programDetailCourses.innerHTML = courses.length
    ? courses.map((x) => `<li>${escapeHtml(formatPlaceholder(x))}</li>`).join("")
    : "<li>-</li>";
  els.programDetailNotes.textContent = formatPlaceholder(data.notes, "暂无备注");
}

function switchAdminTab(tab) {
  state.adminActiveTab = tab;
  if (els.adminTabSchoolsBtn) els.adminTabSchoolsBtn.classList.toggle("active", tab === "schools");
  if (els.adminTabInsightsBtn) els.adminTabInsightsBtn.classList.toggle("active", tab === "insights");
  if (els.adminSchoolsPanel) els.adminSchoolsPanel.classList.toggle("hidden", tab !== "schools");
  if (els.adminInsightsPanel) els.adminInsightsPanel.classList.toggle("hidden", tab !== "insights");
}

function renderAdminSchools() {
  if (!els.adminSchoolsTableBody) return;
  els.adminSchoolsTableBody.innerHTML = "";
  if (!state.adminSchools.length) {
    els.adminSchoolsTableBody.innerHTML = '<tr><td colspan="9" class="ranking-empty">暂无数据</td></tr>';
    return;
  }
  state.adminSchools.forEach((s) => {
    const courseCount = Array.isArray(s.course_list_json) ? s.course_list_json.length : 0;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${s.id}</td>
      <td>${formatPlaceholder(s.country)}</td>
      <td>${formatPlaceholder(s.school_name)}</td>
      <td>${formatPlaceholder(s.program_name)}</td>
      <td>${displayMetric(s.program_duration_months)}</td>
      <td>${courseCount || "-"}</td>
      <td>${formatNumeric(s.tuition_usd) || "-"}</td>
      <td>${formatNumeric(s.living_cost_usd) || "-"}</td>
      <td>${formatNumeric(s.median_salary_usd) || "-"}</td>
    `;
    els.adminSchoolsTableBody.appendChild(tr);
  });
}

async function loadAdminSchools() {
  const q = (els.adminSchoolQuery?.value || "").trim();
  const data = await api(`/api/admin/schools?q=${encodeURIComponent(q)}&limit=200`, {}, true);
  state.adminSchools = Array.isArray(data) ? data : [];
  renderAdminSchools();
}

function renderAdminChatMessages() {
  if (!els.adminChatMessages) return;
  els.adminChatMessages.innerHTML = "";
  if (!state.adminChatMessages.length) {
    els.adminChatMessages.innerHTML = '<div class="history-empty">暂无对话</div>';
    return;
  }

  state.adminChatMessages.forEach((item) => {
    const row = document.createElement("div");
    row.className = `admin-chat-msg ${item.role === "user" ? "is-user" : "is-assistant"}`;
    const meta = item.meta ? `<div class="admin-chat-meta">${escapeHtml(item.meta)}</div>` : "";
    row.innerHTML = `
      <div class="admin-chat-role">${item.role === "user" ? "管理员" : "数据库检索员"}</div>
      <div class="admin-chat-content">${escapeHtml(item.text)}</div>
      ${meta}
    `;
    els.adminChatMessages.appendChild(row);
  });
  els.adminChatMessages.scrollTop = els.adminChatMessages.scrollHeight;
}

function pushAdminChat(role, text, meta = "") {
  const message = { role, text: text || "", meta: meta || "" };
  state.adminChatMessages.push(message);
  if (state.adminChatMessages.length > 30) {
    state.adminChatMessages = state.adminChatMessages.slice(-30);
  }
  renderAdminChatMessages();
}

async function requestAdminAssistant(payload) {
  return api("/api/admin/rag/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  }, true);
}

async function sendAdminChat(options = {}) {
  const message = (options.message || "").trim();
  const quickAction = options.quick_action || "";
  const country = (els.adminRagCountryInput?.value || "").trim();
  const major = (els.adminRagMajorInput?.value || "").trim();
  const limit = Number(options.limit || 5);

  if (message) pushAdminChat("user", message);
  if (quickAction) {
    let actionText = "";
    if (quickAction === "search_10") actionText = "继续搜索入库10个学校信息";
    if (quickAction === "search_5") actionText = "继续搜索入库5个学校信息";
    if (quickAction === "show_memory") actionText = "查看今日记忆";
    if (actionText) pushAdminChat("user", actionText);
  }

  try {
    const data = await requestAdminAssistant({
      message,
      quick_action: quickAction,
      country,
      major,
      limit,
    });
    const meta =
      Number(data.created || 0) > 0 || Number(data.scanned || 0) > 0
        ? `本轮扫描 ${data.scanned || 0} 项，新增 ${data.created || 0} 条待审批，跳过 ${data.skipped || 0} 条`
        : data.memory_excerpt || "";
    pushAdminChat("assistant", data.reply || "已收到。", meta);
    if (Number(data.created || 0) > 0 || Number(data.scanned || 0) > 0) {
      await loadAdminInsights();
      switchAdminTab("insights");
      tip(els.adminInsightTip, `新增待审批 ${data.created || 0} 条，已刷新审批队列`);
    }
    await loadAdminMemory();
  } catch (e) {
    pushAdminChat("assistant", e.message || "检索员暂时不可用，请稍后重试。");
  }
}

async function greetAdminAssistant() {
  state.adminChatMessages = [];
  renderAdminChatMessages();
  await sendAdminChat({ quick_action: "greet" });
}

async function updateInsightDraft(insightId, payload) {
  return api(`/api/admin/insights/${insightId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }, true);
}

async function approveInsight(insightId, payload) {
  return api(`/api/admin/insights/${insightId}/approve`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, true);
}

async function rejectInsight(insightId, payload) {
  return api(`/api/admin/insights/${insightId}/reject`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, true);
}

function readInsightStructured(item) {
  const payload = item?.search_payload && typeof item.search_payload === "object" ? item.search_payload : {};
  const structured = parseJsonLoose(payload.structured_json) || {};
  const facts = Array.isArray(structured.facts) ? structured.facts : [];

  let duration = parseNumberOrNull(structured.duration_months ?? structured.program_duration_months);
  if (duration === null) {
    const durationFact = facts.find((x) => {
      const key = toStringSafe(x?.field).toLowerCase();
      return ["duration", "duration_months", "program_duration_months"].includes(key);
    });
    duration = parseNumberOrNull(durationFact?.value);
  }

  let courses = toArraySafe(structured.course_list ?? structured.course_list_json);
  if (!courses.length) {
    facts.forEach((x) => {
      const key = toStringSafe(x?.field).toLowerCase();
      if (["course_list", "courses", "curriculum"].includes(key)) {
        courses = [...courses, ...toArraySafe(x?.value)];
      }
    });
  }
  courses = [...new Set(courses)].slice(0, 20);

  const summary = toStringSafe(structured.summary) || toStringSafe(item?.edited_text || item?.raw_text);
  return { summary, duration, courses, facts, payloadItems: Array.isArray(payload.items) ? payload.items : [] };
}

function renderAdminInsights() {
  if (!els.adminInsightsList) return;
  els.adminInsightsList.innerHTML = "";
  if (!state.adminInsights.length) {
    els.adminInsightsList.innerHTML = '<div class="history-empty">暂无可审批资料</div>';
    return;
  }

  state.adminInsights.forEach((item) => {
    const card = document.createElement("article");
    card.className = "admin-insight-card";
    const structured = readInsightStructured(item);
    const payloadItems = structured.payloadItems.slice(0, 6);
    const sourceHtml = payloadItems.length
      ? payloadItems
          .map((x) => {
            const title = escapeHtml(formatPlaceholder(x?.title || x?.query));
            const snippet = escapeHtml(formatPlaceholder(x?.snippet));
            const hasUrl = typeof x?.url === "string" && /^https?:\/\//i.test(x.url);
            const url = hasUrl ? x.url : "";
            const sourceBtn = hasUrl
              ? `<a class="source-link-pill" href="${url}" target="_blank" rel="noreferrer">来源网站</a>`
              : "";
            return `
              <li class="admin-source-item">
                <div class="admin-source-title">${title}</div>
                <div class="admin-source-snippet">${snippet}</div>
                <div class="admin-source-foot">${sourceBtn}</div>
              </li>
            `;
          })
          .join("")
      : "<li>暂无来源明细</li>";

    const factRows = structured.facts.length
      ? structured.facts
          .map((x) => {
            const fieldName = escapeHtml(formatPlaceholder(x?.field));
            const value = escapeHtml(formatPlaceholder(x?.value));
            const evidence = escapeHtml(formatPlaceholder(x?.evidence, ""));
            const url = toStringSafe(x?.source_url);
            const urlBtn = /^https?:\/\//i.test(url)
              ? `<a class="source-link-pill" href="${url}" target="_blank" rel="noreferrer">来源网站</a>`
              : "";
            return `
              <li class="admin-fact-item">
                <div class="admin-fact-head">
                  <strong>${fieldName}</strong>
                  ${urlBtn}
                </div>
                <div class="admin-fact-value">${value}</div>
                ${evidence ? `<div class="admin-fact-evidence">${evidence}</div>` : ""}
              </li>
            `;
          })
          .join("")
      : '<li class="history-empty">暂无结构化字段</li>';

    const courseHtml = structured.courses.length
      ? structured.courses.map((c) => `<li>${escapeHtml(c)}</li>`).join("")
      : "<li>-</li>";

    card.innerHTML = `
      <div class="admin-insight-head">
        <h4>${formatPlaceholder(item.school_name)} · ${formatPlaceholder(item.program_name)}</h4>
        <span class="history-status ${item.status === "approved" ? "status-completed" : item.status === "rejected" ? "status-failed" : "status-pending"}">${formatPlaceholder(item.status)}</span>
      </div>
      <div class="admin-insight-grid">
        <section class="admin-insight-summary-box">
          <h5>结构化摘要</h5>
          <p>${escapeHtml(structured.summary || "-")}</p>
          <div class="admin-insight-tags">
            <span class="insight-tag">数据来源：${escapeHtml(formatPlaceholder(item.source_provider, "web"))}</span>
            <span class="insight-tag">项目时长：${structured.duration === null ? "-" : `${formatNumeric(structured.duration)}个月`}</span>
            <span class="insight-tag">选课数：${structured.courses.length || "-"}</span>
          </div>
        </section>
        <section class="admin-insight-course-box">
          <h5>选课列表清单</h5>
          <ul class="admin-course-list">${courseHtml}</ul>
        </section>
      </div>
      <div class="admin-insight-struct">
        <h5>结构化字段（analysis JSON）</h5>
        <ul class="admin-facts-list">${factRows}</ul>
      </div>
      <div class="admin-insight-block">
        <label>AI检索原文（文本）</label>
        <div class="admin-insight-raw">${escapeHtml(formatPlaceholder(item.raw_text))}</div>
      </div>
      <div class="admin-insight-block">
        <label>修改后文本（可编辑）</label>
        <textarea class="admin-insight-edit">${escapeHtml(formatPlaceholder(item.edited_text || item.raw_text))}</textarea>
      </div>
      <div class="admin-insight-block">
        <label>审核备注</label>
        <input class="admin-insight-note" placeholder="可选：记录否决或修改原因" />
      </div>
      <div class="admin-insight-sources">
        <label>检索来源</label>
        <ol>${sourceHtml}</ol>
      </div>
      <div class="admin-insight-actions">
        <button class="mini" data-action="save">保存修改</button>
        <button class="mini primary" data-action="approve">确定入库</button>
        <button class="mini danger" data-action="reject">否决</button>
      </div>
    `;

    const editEl = card.querySelector(".admin-insight-edit");
    const noteEl = card.querySelector(".admin-insight-note");
    editEl.value = formatPlaceholder(item.edited_text || item.raw_text, "");
    noteEl.value = formatPlaceholder(item.review_note, "");
    card.querySelector('[data-action="save"]').addEventListener("click", async () => {
      try {
        await updateInsightDraft(item.id, {
          edited_text: editEl.value.trim(),
          review_note: noteEl.value.trim(),
        });
        tip(els.adminInsightTip, "修改已保存");
      } catch (e) {
        tip(els.adminInsightTip, e.message || "保存失败", true);
      }
    });
    card.querySelector('[data-action="approve"]').addEventListener("click", async () => {
      try {
        await approveInsight(item.id, {
          final_text: editEl.value.trim(),
          review_note: noteEl.value.trim(),
        });
        tip(els.adminInsightTip, "已通过并入库");
        await loadAdminInsights();
      } catch (e) {
        tip(els.adminInsightTip, e.message || "审批失败", true);
      }
    });
    card.querySelector('[data-action="reject"]').addEventListener("click", async () => {
      try {
        await rejectInsight(item.id, { review_note: noteEl.value.trim() || "人工否决" });
        tip(els.adminInsightTip, "已否决");
        await loadAdminInsights();
      } catch (e) {
        tip(els.adminInsightTip, e.message || "否决失败", true);
      }
    });

    els.adminInsightsList.appendChild(card);
  });
}

async function loadAdminInsights() {
  const status = els.adminInsightStatus?.value || "pending";
  const q = (els.adminInsightQuery?.value || "").trim();
  const data = await api(
    `/api/admin/insights?status=${encodeURIComponent(status)}&q=${encodeURIComponent(q)}&limit=200`,
    {},
    true
  );
  state.adminInsights = Array.isArray(data) ? data : [];
  renderAdminInsights();
}

function renderAdminMemory() {
  const memory = state.adminMemory;
  if (!memory) return;
  const retryCount = Array.isArray(memory.retry_queue) ? memory.retry_queue.length : 0;
  const failCount = Array.isArray(memory.failure_history) ? memory.failure_history.length : 0;
  const rankingSources = Array.isArray(memory.ranking_sources) ? memory.ranking_sources : [];
  const rankingText = rankingSources.length
    ? rankingSources.map((x) => String(x || "").toUpperCase()).join(" > ")
    : "未设置";
  const priorityTargets = Array.isArray(memory.priority_targets) ? memory.priority_targets : [];

  if (els.adminMemoryStats) {
    els.adminMemoryStats.innerHTML = `
      <span class="insight-tag">待搜 ${memory.todo?.length || 0}</span>
      <span class="insight-tag">已搜 ${memory.done?.length || 0}</span>
      <span class="insight-tag">重试 ${retryCount}</span>
      <span class="insight-tag">失败 ${failCount}</span>
    `;
  }

  if (els.adminMemoryLongTerm) {
    els.adminMemoryLongTerm.innerHTML = `
      <div class="admin-memory-kv"><span>长期策略</span><strong>${escapeHtml(formatPlaceholder(memory.long_term_instruction, "-"))}</strong></div>
      <div class="admin-memory-kv"><span>榜单优先级</span><strong>${escapeHtml(rankingText)}</strong></div>
      <div class="admin-memory-kv"><span>长期目标</span><strong>${escapeHtml(priorityTargets.length ? priorityTargets.join("；") : "-")}</strong></div>
    `;
  }

  if (els.adminMemoryMeta) {
    const latestLog = Array.isArray(memory.logs) && memory.logs.length ? memory.logs[memory.logs.length - 1] : "";
    els.adminMemoryMeta.textContent = latestLog ? `最新日志：${latestLog}` : "暂无运行日志。";
  }
  if (els.adminMemoryRetryList) {
    const retries = Array.isArray(memory.retry_queue) ? memory.retry_queue : [];
    const failures = Array.isArray(memory.failure_history) ? memory.failure_history.slice(-8).reverse() : [];
    if (!retries.length && !failures.length) {
      els.adminMemoryRetryList.innerHTML = '<div class="history-empty">暂无重试/失败记录</div>';
    } else {
      const retryHtml = retries.length
        ? retries
            .map(
              (x) =>
                `<li><strong>${escapeHtml(formatPlaceholder(x.target))}</strong> · 次数 ${escapeHtml(formatPlaceholder(x.attempts, 0))} · 下次 ${escapeHtml(formatPlaceholder(x.next_retry_at))}<div>${escapeHtml(formatPlaceholder(x.last_reason))}</div></li>`
            )
            .join("")
        : "<li>暂无重试任务</li>";
      const failureHtml = failures.length
        ? failures
            .map(
              (x) =>
                `<li><strong>${escapeHtml(formatPlaceholder(x.target))}</strong> · ${escapeHtml(formatPlaceholder(x.time))}<div>${escapeHtml(formatPlaceholder(x.reason))}</div></li>`
            )
            .join("")
        : "<li>暂无失败记录</li>";
      els.adminMemoryRetryList.innerHTML = `
        <div class="admin-memory-columns">
          <section><h5>自动重试队列</h5><ol>${retryHtml}</ol></section>
          <section><h5>最近失败原因</h5><ol>${failureHtml}</ol></section>
        </div>
      `;
    }
  }
  if (els.adminMemoryEditor) {
    els.adminMemoryEditor.value = memory.raw_markdown || "";
  }
}

async function loadAdminMemory() {
  const data = await api("/api/admin/rag/memory", {}, true);
  state.adminMemory = data || null;
  renderAdminMemory();
}

async function saveAdminMemory() {
  const raw = (els.adminMemoryEditor?.value || "").trim();
  const data = await api("/api/admin/rag/memory", {
    method: "PATCH",
    body: JSON.stringify({ raw_markdown: raw }),
  }, true);
  state.adminMemory = data || null;
  renderAdminMemory();
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

function normalizeQueryOutputSchema(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((group) => {
      if (!group || typeof group !== "object") return null;
      const groupName = toStringSafe(group.group || group.name || group.title) || "字段分组";
      const fieldsRaw = Array.isArray(group.fields) ? group.fields : [];
      const fields = fieldsRaw
        .map((field) => {
          if (!field || typeof field !== "object") return null;
          const key = toStringSafe(field.key);
          const label = toStringSafe(field.label || field.name || field.title || field.key);
          if (!key) return null;
          return { key, label: label || key };
        })
        .filter(Boolean);
      if (!fields.length) return null;
      return { group: groupName, fields };
    })
    .filter(Boolean);
}

function normalizeQueryOutputValues(raw, schema) {
  const valueObj = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  const normalized = {};
  schema.forEach((group) => {
    group.fields.forEach((field) => {
      const rawText = toStringSafe(valueObj[field.key]);
      normalized[field.key] =
        rawText && !["0", "0.0", "none", "null", "n/a", "nan"].includes(rawText.toLowerCase())
          ? rawText
          : "-";
    });
  });
  return normalized;
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
  const queryOutputSchema = normalizeQueryOutputSchema(parsed.query_output_schema);
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
        queryOutput: normalizeQueryOutputValues(
          item?.query_output,
          queryOutputSchema
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
        queryOutput: normalizeQueryOutputValues(
          item?.query_output,
          queryOutputSchema
        ),
      }));

  return {
    ok: true,
    value: {
      rankingRows,
      dimensionWeights,
      schoolAssessments,
      queryOutputSchema,
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
  const queryOutputSchema = Array.isArray(report.queryOutputSchema) ? report.queryOutputSchema : [];

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
          queryOutput: {},
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
    const queryOutput = s.queryOutput && typeof s.queryOutput === "object" ? s.queryOutput : {};
    const queryGroupsHtml = queryOutputSchema.length
      ? queryOutputSchema
          .map((group) => {
            const rows = group.fields
              .map((field) => {
                const value = formatPlaceholder(queryOutput[field.key], "-");
                return `
                  <div class="query-kv">
                    <span>${formatPlaceholder(field.label)}</span>
                    <strong>${value}</strong>
                  </div>
                `;
              })
              .join("");
            return `
              <details class="query-group">
                <summary>${formatPlaceholder(group.group)}</summary>
                <div class="query-grid">${rows}</div>
              </details>
            `;
          })
          .join("")
      : "";

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

          ${queryGroupsHtml ? `
            <section class="assessment-section assessment-query-output">
              <h4>标准化查询字段（v2）</h4>
              ${queryGroupsHtml}
            </section>
          ` : ""}
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
  ensureWizardConcernState();
  const concerns = [...state.wizard.concerns];
  const weights = calcConcernWeightsStrict(concerns);
  state.wizard.weights = weights;
  saveWizardDraft();
  return {
    country: state.wizard.country,
    major: state.wizard.major || "CS",
    budget_max: Number(state.wizard.budget_max || 0),
    concerns,
    selected_dimensions: concerns,
    weights,
    schools: [...state.selectedSchoolIds],
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
      "/api/report/create",
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
    els.schoolCatalogPage,
    els.schoolDetailPage,
    els.programDetailPage,
    els.adminPage,
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

function isCatalogSchoolPath(path) {
  return path.startsWith(`${ROUTES.CATALOG_SCHOOL_PREFIX}/`);
}

function isCatalogProgramPath(path) {
  return path.startsWith(`${ROUTES.CATALOG_PROGRAM_PREFIX}/`);
}

function getCatalogSchoolName(path) {
  const prefix = `${ROUTES.CATALOG_SCHOOL_PREFIX}/`;
  if (!path.startsWith(prefix)) return "";
  try {
    return decodeURIComponent(path.slice(prefix.length));
  } catch {
    return path.slice(prefix.length);
  }
}

function getCatalogProgramId(path) {
  const prefix = `${ROUTES.CATALOG_PROGRAM_PREFIX}/`;
  if (!path.startsWith(prefix)) return "";
  return path.slice(prefix.length);
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
  updateGlobalTopNav(path);

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

  if (path === ROUTES.CATALOG) {
    await loadCatalogSchools();
    els.schoolCatalogPage.classList.remove("hidden");
    return;
  }

  if (isCatalogSchoolPath(path)) {
    const schoolName = getCatalogSchoolName(path);
    if (!schoolName) {
      navigate(ROUTES.CATALOG, true);
      return;
    }
    const data = await loadCatalogSchoolDetail(schoolName);
    renderSchoolDetail(data);
    els.schoolDetailPage.classList.remove("hidden");
    return;
  }

  if (isCatalogProgramPath(path)) {
    const programId = getCatalogProgramId(path);
    if (!programId) {
      navigate(ROUTES.CATALOG, true);
      return;
    }
    const data = await loadProgramDetail(programId);
    renderProgramDetail(data);
    els.programDetailPage.classList.remove("hidden");
    return;
  }

  if (path === ROUTES.ADMIN) {
    if (!isAdminUser()) {
      navigate(ROUTES.APP_HOME, true);
      return;
    }
    await greetAdminAssistant();
    await loadAdminMemory();
    switchAdminTab(state.adminActiveTab || "insights");
    if (state.adminActiveTab === "insights") {
      await loadAdminInsights();
    } else {
      await loadAdminSchools();
    }
    els.adminPage.classList.remove("hidden");
    return;
  }

  if (path === ROUTES.STEP1) {
    await loadCountries();
    hydrateStep1();
    els.stepNewPage.classList.remove("hidden");
    return;
  }

  if (path === ROUTES.STEP2) {
    renderConcernsStep();
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

  if (els.catalogBackHomeBtn) {
    els.catalogBackHomeBtn.addEventListener("click", () => navigate(ROUTES.APP_HOME));
  }
  if (els.adminBackHomeBtn) {
    els.adminBackHomeBtn.addEventListener("click", () => navigate(ROUTES.APP_HOME));
  }

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
    state.concernsStage = "select";
    navigate(ROUTES.STEP2);
  });

  document.getElementById("step2BackBtn").addEventListener("click", () => navigate(ROUTES.STEP1));
  document.getElementById("step2ToSortBtn").addEventListener("click", () => {
    ensureWizardConcernState();
    if (state.wizard.concerns.length < MIN_CONCERNS) {
      alert("请至少选择2个关注维度");
      return;
    }
    state.wizard.weights = calcConcernWeightsStrict(state.wizard.concerns);
    setConcernsStage("sort");
    saveWizardDraft();
  });
  document.getElementById("concernBackSelectBtn").addEventListener("click", () => {
    setConcernsStage("select");
  });
  document.getElementById("step2NextBtn").addEventListener("click", () => {
    ensureWizardConcernState();
    if (state.wizard.concerns.length < MIN_CONCERNS) {
      alert("请至少选择2个关注维度");
      setConcernsStage("select");
      return;
    }
    state.wizard.weights = calcConcernWeightsStrict(state.wizard.concerns);
    saveWizardDraft();
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
    if (!payload.country || !payload.major || payload.selected_dimensions.length < MIN_CONCERNS || !payload.school_ids.length) {
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

  if (els.topNavSchoolBtn) {
    els.topNavSchoolBtn.addEventListener("click", async () => {
      if (!state.token) {
        navigate(ROUTES.LOGIN);
        return;
      }
      await loadCatalogSchools();
      navigate(ROUTES.CATALOG);
    });
  }
  if (els.topNavAdviceBtn) {
    els.topNavAdviceBtn.addEventListener("click", () => {
      if (!state.token) {
        navigate(ROUTES.LOGIN);
        return;
      }
      navigate(ROUTES.APP_HOME);
    });
  }
  if (els.topNavAdminBtn) {
    els.topNavAdminBtn.addEventListener("click", () => {
      if (!state.token) {
        navigate(ROUTES.LOGIN);
        return;
      }
      if (!isAdminUser()) {
        alert("仅管理员可访问");
        return;
      }
      navigate(ROUTES.ADMIN);
    });
  }

  if (els.catalogRankQsBtn) {
    els.catalogRankQsBtn.addEventListener("click", async () => {
      state.catalogRankingSource = "qs";
      await loadCatalogSchools();
    });
  }
  if (els.catalogRankUsnewsBtn) {
    els.catalogRankUsnewsBtn.addEventListener("click", async () => {
      state.catalogRankingSource = "usnews";
      await loadCatalogSchools();
    });
  }
  if (els.catalogRankTimesBtn) {
    els.catalogRankTimesBtn.addEventListener("click", async () => {
      state.catalogRankingSource = "times";
      await loadCatalogSchools();
    });
  }
  if (els.catalogSearchInput) {
    els.catalogSearchInput.addEventListener("input", async () => {
      await loadCatalogSchools();
    });
  }
  if (els.schoolDetailBackBtn) {
    els.schoolDetailBackBtn.addEventListener("click", () => {
      navigate(ROUTES.CATALOG);
    });
  }
  if (els.programDetailBackBtn) {
    els.programDetailBackBtn.addEventListener("click", () => {
      if (state.currentCatalogSchoolName) {
        navigate(`${ROUTES.CATALOG_SCHOOL_PREFIX}/${encodeURIComponent(state.currentCatalogSchoolName)}`);
        return;
      }
      navigate(ROUTES.CATALOG);
    });
  }

  if (els.adminTabSchoolsBtn) {
    els.adminTabSchoolsBtn.addEventListener("click", async () => {
      switchAdminTab("schools");
      await loadAdminSchools();
    });
  }
  if (els.adminTabInsightsBtn) {
    els.adminTabInsightsBtn.addEventListener("click", async () => {
      switchAdminTab("insights");
      await loadAdminInsights();
    });
  }
  if (els.adminSchoolRefreshBtn) {
    els.adminSchoolRefreshBtn.addEventListener("click", async () => {
      try {
        await loadAdminSchools();
        tip(els.adminSchoolTip, `已加载 ${state.adminSchools.length} 条学校数据`);
      } catch (e) {
        tip(els.adminSchoolTip, e.message || "加载失败", true);
      }
    });
  }
  if (els.adminDownloadTemplateBtn) {
    els.adminDownloadTemplateBtn.addEventListener("click", async () => {
      try {
        const response = await fetch("/api/admin/schools/template", {
          method: "GET",
          headers: { Authorization: `Bearer ${state.token}` },
        });
        if (!response.ok) throw new Error("下载模板失败");
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "school_import_template.csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      } catch (e) {
        tip(els.adminSchoolTip, e.message || "下载模板失败", true);
      }
    });
  }
  if (els.adminImportBtn) {
    els.adminImportBtn.addEventListener("click", async () => {
      if (!els.adminExcelInput?.files?.[0]) {
        tip(els.adminSchoolTip, "请先选择Excel文件", true);
        return;
      }
      try {
        const form = new FormData();
        form.append("file", els.adminExcelInput.files[0]);
        const response = await fetch("/api/admin/schools/import-excel", {
          method: "POST",
          headers: { Authorization: `Bearer ${state.token}` },
          body: form,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "导入失败");
        tip(els.adminSchoolTip, `导入完成：新增 ${data.created}，更新 ${data.updated}`);
        await loadAdminSchools();
      } catch (e) {
        tip(els.adminSchoolTip, e.message || "导入失败", true);
      }
    });
  }
  if (els.adminInsightRefreshBtn) {
    els.adminInsightRefreshBtn.addEventListener("click", async () => {
      try {
        await loadAdminInsights();
        tip(els.adminInsightTip, `已加载 ${state.adminInsights.length} 条资料`);
      } catch (e) {
        tip(els.adminInsightTip, e.message || "加载失败", true);
      }
    });
  }
  if (els.adminInsightStatus) {
    els.adminInsightStatus.addEventListener("change", async () => {
      await loadAdminInsights();
    });
  }
  if (els.adminInsightQuery) {
    els.adminInsightQuery.addEventListener("input", async () => {
      await loadAdminInsights();
    });
  }

  if (els.adminQuickSearch5Btn) {
    els.adminQuickSearch5Btn.addEventListener("click", async () => {
      await sendAdminChat({ quick_action: "search_5", limit: 5 });
    });
  }
  if (els.adminQuickSearch10Btn) {
    els.adminQuickSearch10Btn.addEventListener("click", async () => {
      await sendAdminChat({ quick_action: "search_10", limit: 10 });
    });
  }
  if (els.adminQuickMemoryBtn) {
    els.adminQuickMemoryBtn.addEventListener("click", async () => {
      await sendAdminChat({ quick_action: "show_memory" });
    });
  }
  if (els.adminMemoryRefreshBtn) {
    els.adminMemoryRefreshBtn.addEventListener("click", async () => {
      try {
        await loadAdminMemory();
        tip(els.adminMemoryTip, "记忆已刷新");
      } catch (e) {
        tip(els.adminMemoryTip, e.message || "刷新失败", true);
      }
    });
  }
  if (els.adminMemorySaveBtn) {
    els.adminMemorySaveBtn.addEventListener("click", async () => {
      try {
        await saveAdminMemory();
        tip(els.adminMemoryTip, "记忆已保存");
      } catch (e) {
        tip(els.adminMemoryTip, e.message || "保存失败", true);
      }
    });
  }
  if (els.adminChatSendBtn) {
    els.adminChatSendBtn.addEventListener("click", async () => {
      const msg = (els.adminChatInput?.value || "").trim();
      if (!msg) return;
      if (els.adminChatInput) els.adminChatInput.value = "";
      await sendAdminChat({ message: msg });
    });
  }
  if (els.adminChatInput) {
    els.adminChatInput.addEventListener("keydown", async (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      const msg = (els.adminChatInput?.value || "").trim();
      if (!msg) return;
      els.adminChatInput.value = "";
      await sendAdminChat({ message: msg });
    });
  }
}

async function bootstrap() {
  bindEvents();
  await autoLoginIfTokenExists();
  await renderRoute();
}

bootstrap();
