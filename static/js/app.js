/* Contato Facilities — Portal de Análise de Currículos. */
(function () {
  "use strict";

  // ---------------------------------------------------------------
  // Navegação
  // ---------------------------------------------------------------
  const sections = document.querySelectorAll("main > .section");
  const navButtons = document.querySelectorAll("#topnav .nav-btn");
  let switching = false;

  function applySection(id) {
    sections.forEach((s) => {
      s.classList.toggle("active", s.id === id);
      s.classList.remove("leaving");
    });
    navButtons.forEach((b) =>
      b.classList.toggle("active", b.dataset.target === id)
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (id === "jobs") loadJobs();
    if (id === "history") loadHistory();
    if (id === "audit") loadAudit();
    if (id === "settings") {
      renderThemeToggle();
      refreshSystemStatus();
    }
    if (window.LiquidTilt) window.LiquidTilt.bind(document);
  }

  function showSection(id) {
    if (switching) return;
    const current = document.querySelector("main > .section.active");
    if (!current || current.id === id) {
      applySection(id);
      return;
    }
    switching = true;
    current.classList.add("leaving");
    setTimeout(() => {
      applySection(id);
      switching = false;
    }, 170);
  }

  // ---------------------------------------------------------------
  // Tema (escuro / claro / auto) — persistido em localStorage
  // ---------------------------------------------------------------
  const THEME_KEY = "contato-theme";

  function effectiveTheme(pref) {
    if (pref === "light" || pref === "dark") return pref;
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  }

  function applyTheme(pref) {
    document.documentElement.dataset.theme = effectiveTheme(pref);
    document.documentElement.dataset.themePref = pref;
  }

  function loadThemePref() {
    return localStorage.getItem(THEME_KEY) || "dark";
  }

  function saveThemePref(pref) {
    localStorage.setItem(THEME_KEY, pref);
    applyTheme(pref);
    renderThemeToggle();
  }

  function renderThemeToggle() {
    const pref = loadThemePref();
    const toggle = document.getElementById("theme-toggle");
    const autoLink = document.getElementById("theme-auto-link");
    if (!toggle || !autoLink) return;
    // A thumb mostra o tema EFETIVO (resolve "auto" para a preferência do SO)
    toggle.dataset.pref = effectiveTheme(pref);
    autoLink.classList.toggle("active", pref === "auto");
  }

  // Aplica imediatamente para evitar flash
  applyTheme(loadThemePref());

  // Reage a mudanças do sistema quando o modo é "auto"
  if (window.matchMedia) {
    window
      .matchMedia("(prefers-color-scheme: light)")
      .addEventListener("change", () => {
        if (loadThemePref() === "auto") applyTheme("auto");
      });
  }

  document.addEventListener("click", (e) => {
    const target = e.target.closest("[data-target]");
    if (!target) return;
    e.preventDefault();
    showSection(target.dataset.target);
  });

  // ---------------------------------------------------------------
  // Toast
  // ---------------------------------------------------------------
  const toastEl = document.getElementById("toast");
  let toastTimer = null;
  function toast(message, kind = "") {
    toastEl.textContent = message;
    toastEl.className = "toast show " + kind;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastEl.className = "toast " + kind;
    }, 3600);
  }

  // ---------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------
  function escapeHTML(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function classKey(label) {
    if (!label) return "media";
    const l = label.toLowerCase();
    if (l.includes("alta")) return "alta";
    if (l.includes("baixa")) return "baixa";
    return "media";
  }

  function classColorVar(label) {
    const k = classKey(label);
    if (k === "alta") return "var(--ok)";
    if (k === "baixa") return "var(--bad)";
    return "var(--warn)";
  }

  function formatDate(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (_) {
      return iso;
    }
  }

  // ---------------------------------------------------------------
  // Upload + Análise
  // ---------------------------------------------------------------
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileInfo = document.getElementById("file-info");
  const fileName = document.getElementById("file-name");
  const fileRemove = document.getElementById("file-remove");
  const analyzeBtn = document.getElementById("analyze-btn");
  const uploadView = document.getElementById("analyze-upload");
  const loadingView = document.getElementById("analyze-loading");
  const resultView = document.getElementById("analyze-result");
  const loaderStep = document.getElementById("loader-step");
  const newAnalysisBtn = document.getElementById("new-analysis-btn");
  const errorPanel = document.getElementById("analyze-error");
  const errorTitle = document.getElementById("analyze-error-title");
  const errorMessage = document.getElementById("analyze-error-message");
  const errorCountdown = document.getElementById("analyze-error-countdown");
  let countdownTimer = null;

  function clearAnalyzeError() {
    errorPanel.hidden = true;
    errorPanel.classList.remove("warning");
    errorCountdown.hidden = true;
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }

  function showAnalyzeError(title, message, opts) {
    errorTitle.textContent = title;
    errorMessage.textContent = message;
    errorPanel.classList.toggle("warning", !!(opts && opts.warning));
    errorPanel.hidden = false;
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
    if (opts && opts.retryAfter) {
      let remaining = Math.ceil(opts.retryAfter);
      errorCountdown.textContent = `Tente novamente em ${remaining}s`;
      errorCountdown.hidden = false;
      countdownTimer = setInterval(() => {
        remaining -= 1;
        if (remaining <= 0) {
          clearInterval(countdownTimer);
          countdownTimer = null;
          errorCountdown.textContent = "Pronto para tentar novamente";
        } else {
          errorCountdown.textContent = `Tente novamente em ${remaining}s`;
        }
      }, 1000);
    } else {
      errorCountdown.hidden = true;
    }
  }

  let selectedFile = null;

  function setFile(file) {
    selectedFile = file;
    clearAnalyzeError();
    if (file) {
      fileName.textContent = `${file.name} · ${(file.size / 1024).toFixed(0)} KB`;
      fileInfo.hidden = false;
      analyzeBtn.disabled = false;
    } else {
      fileInfo.hidden = true;
      analyzeBtn.disabled = true;
      fileInput.value = "";
    }
  }

  fileInput.addEventListener("change", (e) => {
    const f = e.target.files && e.target.files[0];
    if (f) setFile(f);
  });

  fileRemove.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    setFile(null);
  });

  ["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragging");
    });
  });
  dropzone.addEventListener("drop", (e) => {
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) setFile(f);
  });

  function showAnalyzeState(state) {
    uploadView.hidden = state !== "upload";
    loadingView.hidden = state !== "loading";
    resultView.hidden = state !== "result";
  }

  const loadingSteps = [
    "Lendo arquivo e comparando com vagas",
    "Identificando experiência relevante",
    "Avaliando conhecimentos técnicos",
    "Detectando padrões de IA",
    "Compilando score ponderado",
  ];
  let loadingStepIndex = 0;
  let loadingStepTimer = null;

  function startLoadingSteps() {
    loadingStepIndex = 0;
    loaderStep.textContent = loadingSteps[0];
    loadingStepTimer = setInterval(() => {
      loadingStepIndex = (loadingStepIndex + 1) % loadingSteps.length;
      loaderStep.textContent = loadingSteps[loadingStepIndex];
    }, 2400);
  }
  function stopLoadingSteps() {
    if (loadingStepTimer) clearInterval(loadingStepTimer);
    loadingStepTimer = null;
  }

  function titleForErrorKind(kind) {
    switch (kind) {
      case "quota":
        return "Limite gratuito do Gemini atingido";
      case "config":
        return "Configuração ausente";
      case "input":
        return "Currículo ilegível";
      case "parse":
        return "Resposta do modelo inválida";
      case "api":
        return "Falha de comunicação";
      default:
        return "Não foi possível analisar";
    }
  }

  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    clearAnalyzeError();
    const fd = new FormData();
    fd.append("curriculo", selectedFile);

    showAnalyzeState("loading");
    startLoadingSteps();

    try {
      const resp = await fetch("/api/analyze", { method: "POST", body: fd });
      const data = await resp.json();
      stopLoadingSteps();

      if (!resp.ok) {
        showAnalyzeState("upload");
        const kind = data.kind || "generic";
        showAnalyzeError(
          titleForErrorKind(kind),
          data.error || "Falha ao analisar.",
          {
            retryAfter: data.retry_after,
            warning: kind === "quota" || kind === "input",
          }
        );
        return;
      }

      renderResult(data.resultado, {
        candidato: data.candidato_nome,
        arquivo: data.arquivo,
        criado_em: data.criado_em,
      });
      showAnalyzeState("result");
      toast("Análise concluída e salva no histórico.", "success");
    } catch (err) {
      stopLoadingSteps();
      showAnalyzeState("upload");
      showAnalyzeError("Erro de rede", err.message || String(err));
    }
  });

  newAnalysisBtn.addEventListener("click", () => {
    setFile(null);
    clearAnalyzeError();
    showAnalyzeState("upload");
  });

  // ---------------------------------------------------------------
  // Render do resultado
  // ---------------------------------------------------------------
  function renderResult(r, meta) {
    if (!r) return;

    // Banner do candidato
    document.getElementById("candidate-name").textContent =
      (meta && meta.candidato) || r.candidato_nome || "(sem nome)";
    const metaParts = [];
    if (meta && meta.arquivo) metaParts.push(meta.arquivo);
    if (meta && meta.criado_em) metaParts.push(formatDate(meta.criado_em));
    document.getElementById("candidate-meta").textContent = metaParts.join(" · ") || "—";

    // Score ring
    const score = Number(r.score_final || 0);
    const pct = Math.max(0, Math.min(100, (score / 10) * 100));
    const ring = document.getElementById("score-ring");
    ring.style.setProperty("--pct", String(pct));
    ring.style.setProperty("--ring-color", classColorVar(r.classificacao));
    document.getElementById("score-value").textContent = score.toFixed(1);

    // Classification
    const cls = document.getElementById("classification-badge");
    cls.className = "classification-badge " + classKey(r.classificacao);
    document.getElementById("classification-text").textContent =
      r.classificacao || "—";

    // Recommendation
    document.getElementById("final-recommendation").textContent =
      r.recomendacao_final || "—";

    const recJob = r.vaga_recomendada || {};
    document.getElementById("recommended-title").textContent = recJob.titulo || "—";
    document.getElementById("recommended-reason").textContent =
      recJob.justificativa || "";

    // Resumo
    document.getElementById("exec-summary").textContent = r.resumo_executivo || "—";

    // Detecção de IA
    const aiDet = r.deteccao_ia || {};
    const aiProb = Number(aiDet.probabilidade || 0);
    document.getElementById("ai-prob").textContent = aiProb + "%";
    document.getElementById("ai-bar-fill").style.width = aiProb + "%";

    const verdict = aiDet.veredito || "—";
    const verdictEl = document.getElementById("ai-verdict");
    verdictEl.textContent = verdict;
    let vKey = "humano";
    if (verdict.toLowerCase().includes("provável ia")) vKey = "provavel";
    else if (verdict.toLowerCase().includes("possível")) vKey = "possivel";
    verdictEl.className = "ai-verdict " + vKey;

    renderBullets("ai-indicators", aiDet.indicadores || [], "Nenhum indicador relevante.");
    renderBullets("strong-points", r.pontos_fortes || [], "Nenhum ponto forte destacado.");
    renderBullets("weak-points", r.pontos_atencao || [], "Nenhum ponto de atenção.");

    // Score por vaga — ordenado do maior para o menor
    const vagaList = document.getElementById("vaga-scores");
    vagaList.innerHTML = "";
    const sortedVagas = [...(r.scores_por_vaga || [])].sort(
      (a, b) => (Number(b.score) || 0) - (Number(a.score) || 0)
    );
    sortedVagas.forEach((v) => {
      const row = document.createElement("div");
      row.className = "vaga-score-row";
      const k = classKey(v.classificacao);
      row.innerHTML = `
        <div>
          <div class="title">${escapeHTML(v.vaga_titulo || "(sem título)")}</div>
          <div class="meta">${escapeHTML(v.classificacao || "")}</div>
        </div>
        <div class="score-mini ${k}">${Number(v.score || 0).toFixed(1)} / 10</div>
      `;
      vagaList.appendChild(row);
    });
  }

  function renderBullets(elId, items, fallback) {
    const ul = document.getElementById(elId);
    ul.innerHTML = "";
    if (!items || items.length === 0) {
      const li = document.createElement("li");
      li.textContent = fallback;
      li.style.color = "var(--text-3)";
      ul.appendChild(li);
      return;
    }
    items.forEach((it) => {
      const li = document.createElement("li");
      li.textContent = String(it);
      ul.appendChild(li);
    });
  }

  // ---------------------------------------------------------------
  // Vagas CRUD
  // ---------------------------------------------------------------
  const jobsGrid = document.getElementById("jobs-grid");
  const jobsEmpty = document.getElementById("jobs-empty");
  const jobModal = document.getElementById("job-modal");
  const jobModalTitle = document.getElementById("job-modal-title");
  const jobTituloEl = document.getElementById("job-titulo");
  const jobDescricaoEl = document.getElementById("job-descricao");
  const jobRequisitosEl = document.getElementById("job-requisitos");
  const jobSaveBtn = document.getElementById("job-save-btn");
  const jobCancelBtn = document.getElementById("job-cancel-btn");
  const newJobBtn = document.getElementById("new-job-btn");

  let editingJobId = null;

  function openJobModal(job) {
    editingJobId = job ? job.id : null;
    jobModalTitle.textContent = job ? "Editar vaga" : "Nova vaga";
    jobTituloEl.value = job ? job.titulo : "";
    jobDescricaoEl.value = job ? job.descricao : "";
    jobRequisitosEl.value = job ? job.requisitos || "" : "";
    jobModal.classList.add("show");
    setTimeout(() => jobTituloEl.focus(), 80);
  }

  function closeJobModal() {
    jobModal.classList.remove("show");
    editingJobId = null;
  }

  newJobBtn.addEventListener("click", () => openJobModal(null));
  jobCancelBtn.addEventListener("click", closeJobModal);
  jobModal.addEventListener("click", (e) => {
    if (e.target === jobModal) closeJobModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && jobModal.classList.contains("show")) closeJobModal();
  });

  jobSaveBtn.addEventListener("click", async () => {
    const payload = {
      titulo: jobTituloEl.value.trim(),
      descricao: jobDescricaoEl.value.trim(),
      requisitos: jobRequisitosEl.value.trim(),
    };
    if (!payload.titulo || !payload.descricao) {
      toast("Título e descrição são obrigatórios.", "error");
      return;
    }
    jobSaveBtn.disabled = true;
    try {
      const url = editingJobId ? `/api/jobs/${editingJobId}` : "/api/jobs";
      const method = editingJobId ? "PUT" : "POST";
      const resp = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Erro ao salvar.");
      toast(editingJobId ? "Vaga atualizada." : "Vaga criada.", "success");
      closeJobModal();
      loadJobs();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      jobSaveBtn.disabled = false;
    }
  });

  async function loadJobs() {
    jobsGrid.innerHTML = "";
    try {
      const resp = await fetch("/api/jobs");
      const jobs = await resp.json();
      if (!Array.isArray(jobs) || jobs.length === 0) {
        jobsEmpty.hidden = false;
        return;
      }
      jobsEmpty.hidden = true;
      jobs.forEach((job, idx) => {
        const card = document.createElement("div");
        card.className = "glass-tile glass-tile-3d job-card fade-up";
        if (idx < 4) card.classList.add("fade-up-delay-" + (idx + 1));
        card.innerHTML = `
          <div class="job-meta">Vaga</div>
          <h3 class="job-title">${escapeHTML(job.titulo)}</h3>
          <p class="job-desc">${escapeHTML(job.descricao)}</p>
          <div class="job-card-actions">
            <button class="btn btn-ghost" data-action="edit">Editar</button>
            <button class="btn btn-danger" data-action="delete">Excluir</button>
          </div>
        `;
        card.querySelector('[data-action="edit"]').addEventListener("click", (e) => {
          e.stopPropagation();
          openJobModal(job);
        });
        card.querySelector('[data-action="delete"]').addEventListener("click", async (e) => {
          e.stopPropagation();
          if (!confirm(`Excluir a vaga "${job.titulo}"?`)) return;
          const r = await fetch(`/api/jobs/${job.id}`, { method: "DELETE" });
          if (r.ok) {
            toast("Vaga excluída.", "success");
            loadJobs();
          } else {
            toast("Erro ao excluir.", "error");
          }
        });
        jobsGrid.appendChild(card);
      });
      if (window.LiquidTilt) window.LiquidTilt.bind(jobsGrid);
    } catch (err) {
      toast("Erro ao carregar vagas: " + err.message, "error");
    }
  }

  // ---------------------------------------------------------------
  // Histórico
  // ---------------------------------------------------------------
  const historyList = document.getElementById("history-list");
  const historyEmpty = document.getElementById("history-empty");
  const historySummary = document.getElementById("history-summary");

  async function loadHistory() {
    historyList.innerHTML = "";
    historySummary.innerHTML = "";
    try {
      const resp = await fetch("/api/analyses");
      const items = await resp.json();
      if (!Array.isArray(items) || items.length === 0) {
        historyEmpty.hidden = false;
        return;
      }
      historyEmpty.hidden = true;

      // Sumário
      const total = items.length;
      const alta = items.filter((i) => classKey(i.classificacao) === "alta").length;
      const media = items.filter((i) => classKey(i.classificacao) === "media").length;
      const baixa = items.filter((i) => classKey(i.classificacao) === "baixa").length;
      const avg =
        items.reduce((acc, i) => acc + (Number(i.score_final) || 0), 0) /
        Math.max(total, 1);

      historySummary.innerHTML = `
        <div class="summary-card"><div class="num">${total}</div><div class="label">Total</div></div>
        <div class="summary-card"><div class="num alta">${alta}</div><div class="label">Alta aderência</div></div>
        <div class="summary-card"><div class="num media">${media}</div><div class="label">Média aderência</div></div>
        <div class="summary-card"><div class="num baixa">${baixa}</div><div class="label">Baixa aderência</div></div>
        <div class="summary-card"><div class="num gold">${avg.toFixed(1)}</div><div class="label">Score médio</div></div>
      `;

      items.forEach((it) => {
        const row = document.createElement("div");
        row.className = "history-row";
        const k = classKey(it.classificacao);
        row.innerHTML = `
          <div class="candidate">
            <div class="candidate-name">${escapeHTML(it.candidato_nome || "(sem nome)")}</div>
            <div class="candidate-file">${escapeHTML(it.arquivo || "")}</div>
          </div>
          <div class="col-job" title="${escapeHTML(it.vaga_recomendada || "")}">
            ${escapeHTML(it.vaga_recomendada || "—")}
          </div>
          <div class="col-score ${k}">${(Number(it.score_final) || 0).toFixed(1)}</div>
          <div class="col-date">${escapeHTML(formatDate(it.criado_em))}</div>
          <button class="col-delete" title="Excluir" aria-label="Excluir">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
              <line x1="10" y1="11" x2="10" y2="17"/>
              <line x1="14" y1="11" x2="14" y2="17"/>
            </svg>
          </button>
        `;
        row.addEventListener("click", () => openAnalysis(it.id));
        row.querySelector(".col-delete").addEventListener("click", async (e) => {
          e.stopPropagation();
          if (!confirm(`Excluir a análise de "${it.candidato_nome}"?`)) return;
          const r = await fetch(`/api/analyses/${it.id}`, { method: "DELETE" });
          if (r.ok) {
            toast("Análise excluída.", "success");
            loadHistory();
          } else {
            toast("Erro ao excluir.", "error");
          }
        });
        historyList.appendChild(row);
      });
    } catch (err) {
      toast("Erro ao carregar histórico: " + err.message, "error");
    }
  }

  async function openAnalysis(id) {
    try {
      const resp = await fetch(`/api/analyses/${id}`);
      const data = await resp.json();
      if (!resp.ok) {
        toast(data.error || "Erro ao abrir análise.", "error");
        return;
      }
      renderResult(data.resultado, {
        candidato: data.candidato_nome,
        arquivo: data.arquivo,
        criado_em: data.criado_em,
      });
      showAnalyzeState("result");
      showSection("analyze");
    } catch (err) {
      toast("Erro de rede: " + err.message, "error");
    }
  }

  // ---------------------------------------------------------------
  // Auditoria
  // ---------------------------------------------------------------
  const auditList = document.getElementById("audit-list");
  const auditEmpty = document.getElementById("audit-empty");
  const auditFilters = document.getElementById("audit-filters");
  const clearAuditBtn = document.getElementById("clear-audit-btn");

  let auditFilterCategory = "";
  let auditFilterLevel = "";

  function categoryLabel(cat) {
    if (cat === "vaga") return "Vaga";
    if (cat === "analise") return "Análise";
    if (cat === "sistema") return "Sistema";
    return cat || "—";
  }

  function metaForAuditRow(ev) {
    const m = ev.meta || {};
    if (ev.category === "analise" && m.candidato && m.score != null) {
      return `${m.candidato} · ${m.vaga_recomendada || "—"} · score ${Number(m.score).toFixed(1)}`;
    }
    if (ev.category === "analise" && m.arquivo) {
      return m.arquivo + (m.motivo ? " · " + m.motivo : "");
    }
    if (ev.category === "vaga" && m.campos_alterados && m.campos_alterados.length) {
      return "Campos alterados: " + m.campos_alterados.join(", ");
    }
    return "";
  }

  auditFilters.addEventListener("click", (e) => {
    const btn = e.target.closest(".filter-chip");
    if (!btn) return;

    if ("filterCat" in btn.dataset) {
      auditFilterCategory = btn.dataset.filterCat;
      // limpa active dos chips de categoria
      auditFilters
        .querySelectorAll("[data-filter-cat]")
        .forEach((b) => b.classList.toggle("active", b === btn));
    } else if ("filterLevel" in btn.dataset) {
      const newLevel = btn.dataset.filterLevel;
      auditFilterLevel = auditFilterLevel === newLevel ? "" : newLevel;
      auditFilters
        .querySelectorAll("[data-filter-level]")
        .forEach((b) =>
          b.classList.toggle(
            "active",
            b.dataset.filterLevel === auditFilterLevel
          )
        );
    }
    loadAudit();
  });

  clearAuditBtn.addEventListener("click", async () => {
    if (!confirm("Limpar toda a trilha de auditoria? Esta ação não pode ser desfeita.")) {
      return;
    }
    try {
      const r = await fetch("/api/audit", { method: "DELETE" });
      const data = await r.json();
      if (r.ok) {
        toast(`Trilha limpa (${data.removidos} eventos).`, "success");
        loadAudit();
      } else {
        toast(data.error || "Erro ao limpar.", "error");
      }
    } catch (err) {
      toast("Erro de rede: " + err.message, "error");
    }
  });

  async function loadAudit() {
    auditList.innerHTML = "";
    try {
      const params = new URLSearchParams();
      if (auditFilterCategory) params.set("category", auditFilterCategory);
      if (auditFilterLevel) params.set("level", auditFilterLevel);
      const url = "/api/audit" + (params.toString() ? "?" + params : "");
      const resp = await fetch(url);
      const events = await resp.json();
      if (!Array.isArray(events) || events.length === 0) {
        auditEmpty.hidden = false;
        return;
      }
      auditEmpty.hidden = true;
      events.forEach((ev) => {
        const row = document.createElement("div");
        row.className = "audit-row level-" + (ev.level || "info");
        const meta = metaForAuditRow(ev);
        row.innerHTML = `
          <span class="level-pill" aria-hidden="true"></span>
          <span class="category-pill ${escapeHTML(ev.category || "")}">${escapeHTML(categoryLabel(ev.category))}</span>
          <div>
            <div class="audit-msg">${escapeHTML(ev.message || "")}</div>
            ${meta ? `<div class="audit-meta">${escapeHTML(meta)}</div>` : ""}
          </div>
          <div class="audit-date">${escapeHTML(formatDate(ev.criado_em))}</div>
        `;
        auditList.appendChild(row);
      });
    } catch (err) {
      toast("Erro ao carregar auditoria: " + err.message, "error");
    }
  }

  // ---------------------------------------------------------------
  // Opções
  // ---------------------------------------------------------------
  const themeToggleEl = document.getElementById("theme-toggle");
  const themeAutoLink = document.getElementById("theme-auto-link");

  themeToggleEl.addEventListener("click", (e) => {
    const btn = e.target.closest(".theme-toggle-btn");
    if (!btn) return;
    saveThemePref(btn.dataset.theme);
    toast(
      `Tema ${btn.dataset.theme === "light" ? "claro" : "escuro"} aplicado.`,
      "success"
    );
  });

  themeAutoLink.addEventListener("click", () => {
    saveThemePref("auto");
    toast("Tema seguindo o sistema operacional.", "success");
  });

  document
    .getElementById("settings-clear-analyses")
    .addEventListener("click", async () => {
      if (
        !confirm(
          "Apagar TODAS as análises do histórico? Esta ação não pode ser desfeita."
        )
      )
        return;
      try {
        const list = await (await fetch("/api/analyses")).json();
        if (!Array.isArray(list) || list.length === 0) {
          toast("Já não há análises no histórico.", "");
          return;
        }
        await Promise.all(
          list.map((a) => fetch(`/api/analyses/${a.id}`, { method: "DELETE" }))
        );
        toast(`${list.length} análise(s) apagada(s).`, "success");
        refreshSystemStatus();
      } catch (err) {
        toast("Erro: " + err.message, "error");
      }
    });

  document
    .getElementById("settings-clear-audit")
    .addEventListener("click", async () => {
      if (
        !confirm("Apagar toda a trilha de auditoria? Esta ação não pode ser desfeita.")
      )
        return;
      try {
        const r = await fetch("/api/audit", { method: "DELETE" });
        const data = await r.json();
        if (r.ok) {
          toast(`Trilha limpa (${data.removidos} eventos).`, "success");
          refreshSystemStatus();
        } else {
          toast(data.error || "Erro ao limpar.", "error");
        }
      } catch (err) {
        toast("Erro: " + err.message, "error");
      }
    });

  async function refreshSystemStatus() {
    const els = {
      gemini: document.getElementById("status-gemini"),
      model: document.getElementById("status-model"),
      jobs: document.getElementById("status-jobs"),
      analyses: document.getElementById("status-analyses"),
      events: document.getElementById("status-events"),
    };
    try {
      const [health, jobs, analyses, events] = await Promise.all([
        fetch("/api/health").then((r) => r.json()),
        fetch("/api/jobs").then((r) => r.json()),
        fetch("/api/analyses").then((r) => r.json()),
        fetch("/api/audit").then((r) => r.json()),
      ]);
      els.gemini.innerHTML = health.gemini_configured
        ? '<span class="ok">Configurada</span>'
        : '<span class="bad">Não configurada</span>';
      els.model.textContent = health.model || "—";
      els.jobs.textContent = Array.isArray(jobs) ? String(jobs.length) : "0";
      els.analyses.textContent = Array.isArray(analyses)
        ? String(analyses.length)
        : "0";
      els.events.textContent = Array.isArray(events) ? String(events.length) : "0";
    } catch (_) {
      /* ignora */
    }
  }

  // ---------------------------------------------------------------
  // Health
  // ---------------------------------------------------------------
  async function checkHealth() {
    try {
      const r = await fetch("/api/health");
      const d = await r.json();
      if (!d.gemini_configured) {
        toast(
          "Atenção: GEMINI_API_KEY não configurada — edite o arquivo .env.",
          "error"
        );
      }
    } catch (_) {
      /* ignora */
    }
  }

  checkHealth();

  // ---------------------------------------------------------------
  // Minimiza a topbar quando sai do topo da página. Só volta ao normal
  // quando a rolagem retorna ao topo — rolar um pouco para cima no meio
  // da página NÃO restaura (evita "piscar" durante a leitura).
  // ---------------------------------------------------------------
  (function setupTopbarMinimize() {
    const topbar = document.querySelector(".topbar");
    if (!topbar) return;
    const REVEAL_AT_TOP = 90; // só visível quando perto do topo
    let ticking = false;

    // Lê a posição da rolagem de várias fontes (compatibilidade).
    function getY() {
      return (
        window.pageYOffset ||
        document.documentElement.scrollTop ||
        document.body.scrollTop ||
        0
      );
    }
    function apply() {
      const y = getY();
      if (y < REVEAL_AT_TOP) {
        topbar.classList.remove("topbar-min");
      } else {
        topbar.classList.add("topbar-min");
      }
      ticking = false;
    }
    function onScroll() {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(apply);
      }
    }
    // capture:true capta a rolagem mesmo se ocorrer num contêiner interno
    // (não só na window), evitando que o listener nunca dispare.
    window.addEventListener("scroll", onScroll, { capture: true, passive: true });
    document.addEventListener("scroll", onScroll, { capture: true, passive: true });
    apply();
  })();
})();
