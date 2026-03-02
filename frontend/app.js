const state = {
  token: localStorage.getItem("token") || "",
  currentUser: null,
  countries: [],
  schools: [],
  adminSchools: [],
  selectedSchoolIds: new Set(),
  dimensions: [
    "学历提升", "学费压力", "学校排名", "当地就业", "就业去向", "移民",
    "薪资", "回国认可度", "读书压力", "课程难度", "安全度", "生活开销"
  ]
};

const els = {
  authCard: document.getElementById("authCard"),
  appCard: document.getElementById("appCard"),
  resultCard: document.getElementById("resultCard"),
  adminCard: document.getElementById("adminCard"),
  authTip: document.getElementById("authTip"),
  excelTip: document.getElementById("excelTip"),
  countrySelect: document.getElementById("countrySelect"),
  schoolList: document.getElementById("schoolList"),
  selectedSummary: document.getElementById("selectedSummary"),
  dimensionBox: document.getElementById("dimensionBox"),
  schoolSearch: document.getElementById("schoolSearch"),
  modelTag: document.getElementById("modelTag"),
  weightsBox: document.getElementById("weightsBox"),
  rankingTableBody: document.querySelector("#rankingTable tbody"),
  summaryBox: document.getElementById("summaryBox"),
  pdfLink: document.getElementById("pdfLink"),
  adminTableBody: document.querySelector("#adminTable tbody"),
  adminTip: document.getElementById("adminTip"),
  adminImportTip: document.getElementById("adminImportTip"),
  adminFormTitle: document.getElementById("adminFormTitle")
};

function tip(el, msg, isError = false) {
  el.textContent = msg || "";
  el.style.color = isError ? "#b4303f" : "#4f5d75";
}

function toNumber(v) {
  const n = Number(v || 0);
  return Number.isFinite(n) ? n : 0;
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
  els.dimensionBox.innerHTML = "";
  state.dimensions.forEach((d, idx) => {
    const label = document.createElement("label");
    label.className = "chip";
    label.innerHTML = `<input type="checkbox" name="dimension" value="${d}" ${idx < 3 ? "checked" : ""}/> ${d}`;
    els.dimensionBox.appendChild(label);
  });
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
      renderSelectedSummary();
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
  localStorage.removeItem("token");
}

function showApp() {
  els.authCard.classList.add("hidden");
  els.appCard.classList.remove("hidden");

  const isAdmin = state.currentUser && state.currentUser.role === "admin";
  els.adminCard.classList.toggle("hidden", !isAdmin);
}

function logout() {
  clearToken();
  els.authCard.classList.remove("hidden");
  els.appCard.classList.add("hidden");
  els.resultCard.classList.add("hidden");
  els.adminCard.classList.add("hidden");
}

async function fetchMe() {
  if (!state.token) return null;
  const me = await api("/api/auth/me", {}, true);
  state.currentUser = me;
  return me;
}

async function loadCountries() {
  const data = await api("/api/countries");
  state.countries = data.countries || [];
  els.countrySelect.innerHTML = "";
  state.countries.forEach((c) => {
    const op = document.createElement("option");
    op.value = c;
    op.textContent = c;
    els.countrySelect.appendChild(op);
  });
}

async function loadSchools() {
  const country = els.countrySelect.value;
  if (!country || !state.token) return;
  const q = els.schoolSearch.value.trim();
  const data = await api(`/api/schools?country=${encodeURIComponent(country)}&q=${encodeURIComponent(q)}`, {}, true);
  state.schools = data;
  renderSchools(state.schools);
  renderSelectedSummary();
}

function renderResult(data) {
  els.resultCard.classList.remove("hidden");
  els.modelTag.textContent = `模型: ${data.model_used}`;

  els.weightsBox.innerHTML = "";
  Object.entries(data.weights).forEach(([k, v]) => {
    const box = document.createElement("div");
    box.className = "weight-item";
    box.innerHTML = `<strong>${k}</strong><div>${v} 分</div>`;
    els.weightsBox.appendChild(box);
  });

  els.rankingTableBody.innerHTML = "";
  data.ranking.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.rank}</td><td>${r.school}</td><td>${r.program}</td><td>${r.total_score}</td>`;
    els.rankingTableBody.appendChild(tr);
  });

  els.summaryBox.textContent = data.summary_markdown;
  els.pdfLink.href = "#";
  els.pdfLink.dataset.analysisId = String(data.analysis_id);
}

function adminFormPayload() {
  return {
    country: document.getElementById("fCountry").value.trim(),
    school_name: document.getElementById("fSchoolName").value.trim(),
    program_name: document.getElementById("fProgramName").value.trim(),
    major_track: document.getElementById("fMajorTrack").value.trim() || "CS",
    degree: document.getElementById("fDegree").value.trim() || "Master",
    tuition_usd: toNumber(document.getElementById("fTuition").value),
    living_cost_usd: toNumber(document.getElementById("fLivingCost").value),
    ranking_score: toNumber(document.getElementById("fRankingScore").value),
    median_salary_usd: toNumber(document.getElementById("fMedianSalary").value),
    safety_score: toNumber(document.getElementById("fSafetyScore").value),
    course_difficulty: toNumber(document.getElementById("fCourseDifficulty").value),
    employment_support: toNumber(document.getElementById("fEmploymentSupport").value),
    visa_support: toNumber(document.getElementById("fVisaSupport").value),
    alumni_network: toNumber(document.getElementById("fAlumniNetwork").value),
    immigration_friendly: toNumber(document.getElementById("fImmigrationFriendly").value),
    domestic_recognition: toNumber(document.getElementById("fDomesticRecognition").value),
    notes: document.getElementById("fNotes").value.trim()
  };
}

function resetAdminForm() {
  document.getElementById("adminEditId").value = "";
  document.getElementById("fCountry").value = "";
  document.getElementById("fSchoolName").value = "";
  document.getElementById("fProgramName").value = "";
  document.getElementById("fMajorTrack").value = "CS";
  document.getElementById("fDegree").value = "Master";
  document.getElementById("fTuition").value = "0";
  document.getElementById("fLivingCost").value = "0";
  document.getElementById("fRankingScore").value = "0";
  document.getElementById("fMedianSalary").value = "0";
  document.getElementById("fSafetyScore").value = "0";
  document.getElementById("fCourseDifficulty").value = "0";
  document.getElementById("fEmploymentSupport").value = "0";
  document.getElementById("fVisaSupport").value = "0";
  document.getElementById("fAlumniNetwork").value = "0";
  document.getElementById("fImmigrationFriendly").value = "0";
  document.getElementById("fDomesticRecognition").value = "0";
  document.getElementById("fNotes").value = "";
  els.adminFormTitle.textContent = "新增学校项目";
}

function fillAdminForm(row) {
  document.getElementById("adminEditId").value = String(row.id);
  document.getElementById("fCountry").value = row.country || "";
  document.getElementById("fSchoolName").value = row.school_name || "";
  document.getElementById("fProgramName").value = row.program_name || "";
  document.getElementById("fMajorTrack").value = row.major_track || "CS";
  document.getElementById("fDegree").value = row.degree || "Master";
  document.getElementById("fTuition").value = row.tuition_usd ?? 0;
  document.getElementById("fLivingCost").value = row.living_cost_usd ?? 0;
  document.getElementById("fRankingScore").value = row.ranking_score ?? 0;
  document.getElementById("fMedianSalary").value = row.median_salary_usd ?? 0;
  document.getElementById("fSafetyScore").value = row.safety_score ?? 0;
  document.getElementById("fCourseDifficulty").value = row.course_difficulty ?? 0;
  document.getElementById("fEmploymentSupport").value = row.employment_support ?? 0;
  document.getElementById("fVisaSupport").value = row.visa_support ?? 0;
  document.getElementById("fAlumniNetwork").value = row.alumni_network ?? 0;
  document.getElementById("fImmigrationFriendly").value = row.immigration_friendly ?? 0;
  document.getElementById("fDomesticRecognition").value = row.domestic_recognition ?? 0;
  document.getElementById("fNotes").value = row.notes || "";
  els.adminFormTitle.textContent = `编辑学校项目 #${row.id}`;
}

function renderAdminTable(rows) {
  els.adminTableBody.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.id}</td>
      <td>${row.country}</td>
      <td>${row.school_name}</td>
      <td>${row.program_name}</td>
      <td>${row.tuition_usd}</td>
      <td>${row.living_cost_usd}</td>
      <td>${row.median_salary_usd}</td>
      <td>
        <button class="mini" data-edit="${row.id}">编辑</button>
        <button class="mini danger" data-del="${row.id}">删除</button>
      </td>
    `;
    els.adminTableBody.appendChild(tr);
  });

  els.adminTableBody.querySelectorAll("button[data-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.edit);
      const row = state.adminSchools.find((x) => x.id === id);
      if (row) fillAdminForm(row);
    });
  });

  els.adminTableBody.querySelectorAll("button[data-del]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.del);
      if (!confirm(`确认删除 #${id} ?`)) return;
      try {
        await api(`/api/admin/schools/${id}`, { method: "DELETE" }, true);
        tip(els.adminTip, `已删除 #${id}`);
        await loadAdminSchools();
        await loadSchools();
      } catch (e) {
        tip(els.adminTip, e.message, true);
      }
    });
  });
}

async function loadAdminSchools() {
  if (!state.currentUser || state.currentUser.role !== "admin") return;
  const country = document.getElementById("adminCountryFilter").value.trim();
  const q = document.getElementById("adminKeyword").value.trim();

  const params = new URLSearchParams();
  if (country) params.set("country", country);
  if (q) params.set("q", q);
  params.set("limit", "300");

  const list = await api(`/api/admin/schools?${params.toString()}`, {}, true);
  state.adminSchools = list;
  renderAdminTable(list);
}

async function loginSuccess(token) {
  setToken(token);
  await fetchMe();
  showApp();
  await loadCountries();
  await loadSchools();
  if (state.currentUser && state.currentUser.role === "admin") {
    await loadAdminSchools();
  }
}

async function autoLoginIfTokenExists() {
  if (!state.token) return;
  try {
    await fetchMe();
    showApp();
  } catch {
    logout();
  }
}

function bindEvents() {
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

  document.getElementById("logoutBtn").addEventListener("click", logout);

  els.countrySelect.addEventListener("change", async () => {
    state.selectedSchoolIds.clear();
    await loadSchools();
  });

  els.schoolSearch.addEventListener("input", () => {
    const keyword = els.schoolSearch.value.trim().toLowerCase();
    const filtered = state.schools.filter((s) => {
      const text = `${s.school_name} ${s.program_name}`.toLowerCase();
      return text.includes(keyword);
    });
    renderSchools(filtered);
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

      const country = els.countrySelect.value;
      const response = await fetch(`/api/schools/upload-excel?country=${encodeURIComponent(country)}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${state.token}` },
        body: form
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Excel识别失败");

      data.matched_school_ids.forEach((id) => state.selectedSchoolIds.add(id));
      renderSchools(state.schools);
      renderSelectedSummary();

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
    const country = els.countrySelect.value;
    const dimensions = selectedDimensions();
    const schoolIds = [...state.selectedSchoolIds];

    if (!country) {
      alert("请先选择国家");
      return;
    }
    if (dimensions.length === 0) {
      alert("请至少选择一个关注维度");
      return;
    }
    if (schoolIds.length === 0) {
      alert("请至少选择一个学校项目");
      return;
    }

    try {
      const payload = {
        country,
        major: document.getElementById("majorInput").value.trim() || "CS",
        budget_max: Number(document.getElementById("budgetInput").value || 0),
        selected_dimensions: dimensions,
        school_ids: schoolIds
      };
      const data = await api("/api/analysis/run", {
        method: "POST",
        body: JSON.stringify(payload)
      }, true);
      renderResult(data);
    } catch (e) {
      alert(e.message);
    }
  });

  document.getElementById("pdfLink").addEventListener("click", async (e) => {
    e.preventDefault();
    const analysisId = els.pdfLink.dataset.analysisId;
    if (!analysisId) {
      alert("请先生成分析结果");
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

  document.getElementById("adminRefreshBtn").addEventListener("click", async () => {
    try {
      await loadAdminSchools();
      tip(els.adminTip, `已加载 ${state.adminSchools.length} 条`);
    } catch (e) {
      tip(els.adminTip, e.message, true);
    }
  });

  document.getElementById("adminTemplateLink").addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      const response = await fetch("/api/admin/schools/template", {
        method: "GET",
        headers: { Authorization: `Bearer ${state.token}` }
      });
      if (!response.ok) {
        let detail = "下载模板失败";
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
      a.download = "school_import_template.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      tip(els.adminTip, "模板已下载");
    } catch (e2) {
      tip(els.adminTip, e2.message, true);
    }
  });

  document.getElementById("adminSaveBtn").addEventListener("click", async () => {
    try {
      const payload = adminFormPayload();
      if (!payload.country || !payload.school_name || !payload.program_name) {
        tip(els.adminTip, "country / school_name / program_name 必填", true);
        return;
      }

      const editId = document.getElementById("adminEditId").value;
      if (editId) {
        await api(`/api/admin/schools/${editId}`, {
          method: "PUT",
          body: JSON.stringify(payload)
        }, true);
        tip(els.adminTip, `已更新 #${editId}`);
      } else {
        await api("/api/admin/schools", {
          method: "POST",
          body: JSON.stringify(payload)
        }, true);
        tip(els.adminTip, "新增成功");
      }
      resetAdminForm();
      await loadAdminSchools();
      await loadSchools();
    } catch (e) {
      tip(els.adminTip, e.message, true);
    }
  });

  document.getElementById("adminResetBtn").addEventListener("click", resetAdminForm);

  document.getElementById("adminImportBtn").addEventListener("click", async () => {
    const fileInput = document.getElementById("adminExcelInput");
    if (!fileInput.files || !fileInput.files[0]) {
      tip(els.adminImportTip, "请先选择Excel文件", true);
      return;
    }

    try {
      const form = new FormData();
      form.append("file", fileInput.files[0]);
      const response = await fetch("/api/admin/schools/import-excel", {
        method: "POST",
        headers: { Authorization: `Bearer ${state.token}` },
        body: form
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "导入失败");

      const errPreview = data.errors && data.errors.length ? `\n错误样本: ${data.errors.slice(0, 5).join(" | ")}` : "";
      tip(els.adminImportTip, `导入完成：新增 ${data.created}，更新 ${data.updated}${errPreview}`);
      await loadAdminSchools();
      await loadSchools();
    } catch (e) {
      tip(els.adminImportTip, e.message, true);
    }
  });
}

async function bootstrap() {
  renderDimensions();
  bindEvents();
  resetAdminForm();

  await autoLoginIfTokenExists();
  await loadCountries();

  if (state.token) {
    await loadSchools();
    if (state.currentUser && state.currentUser.role === "admin") {
      await loadAdminSchools();
    }
  }
}

bootstrap();
