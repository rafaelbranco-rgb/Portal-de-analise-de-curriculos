/* Contato Facilities — Portal de Análise de Currículos. */
(function () {
  "use strict";

  // ---------------------------------------------------------------
  // Sessão: toda chamada ao servidor passa por aqui. Se a sessão caiu
  // (HTTP 401), volta para a tela de login em vez de mostrar erro solto.
  // A função declarada com o nome `fetch` sombreia o fetch nativo dentro
  // deste arquivo, então nenhuma chamada existente escapa da checagem.
  // ---------------------------------------------------------------
  const nativeFetch = window.fetch.bind(window);

  async function fetch(url, opts) {
    const resp = await nativeFetch(url, opts);
    if (resp.status === 401) {
      window.location.href = "/login?expirado=1";
      throw new Error("Sessão expirada");
    }
    return resp;
  }

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
      loadUsers();
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

  function formatBytes(n) {
    const v = Number(n) || 0;
    if (v <= 0) return "";
    if (v < 1024) return v + " B";
    if (v < 1024 * 1024) return (v / 1024).toFixed(0) + " KB";
    return (v / (1024 * 1024)).toFixed(1) + " MB";
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
        id: data.id,
        candidato: data.candidato_nome,
        arquivo: data.arquivo,
        criado_em: data.criado_em,
        tem_arquivo: data.tem_arquivo,
        arquivo_mime: data.arquivo_mime,
        arquivo_tamanho: data.arquivo_tamanho,
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

    // Currículo original anexado à página do candidato
    renderCurriculo(meta || {});

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

    // Indicador de PCD (consultivo)
    renderPcd(r.analise_pcd);

    renderBullets("strong-points", r.pontos_fortes || [], "Nenhum ponto forte destacado.");
    renderBullets("weak-points", r.pontos_atencao || [], "Nenhum ponto de atenção.");

    // Score por vaga — ordenado do maior para o menor
    const vagaList = document.getElementById("vaga-scores");
    vagaList.innerHTML = "";
    const sortedVagas = [...(r.scores_por_vaga || [])].sort(
      (a, b) => (Number(b.score) || 0) - (Number(a.score) || 0)
    );
    sortedVagas.forEach((v) => {
      vagaList.appendChild(buildVagaRow(v));
    });
  }

  // ---------------------------------------------------------------
  // Currículo anexado à página do candidato
  // ---------------------------------------------------------------
  const cvBlock = document.getElementById("cv-attachment");
  const cvFileName = document.getElementById("cv-file-name");
  const cvActions = document.getElementById("cv-actions");
  const cvEmpty = document.getElementById("cv-empty");
  const cvPreview = document.getElementById("cv-preview");
  const cvPreviewBtn = document.getElementById("cv-preview-btn");
  const cvFrame = document.getElementById("cv-frame");
  const cvOpenLink = document.getElementById("cv-open-link");
  const cvDownloadLink = document.getElementById("cv-download-link");

  function renderCurriculo(meta) {
    if (!cvBlock) return;

    // Fecha a pré-visualização da análise anterior.
    cvPreview.hidden = true;
    cvFrame.src = "about:blank";
    cvPreviewBtn.textContent = "Ver aqui";

    if (!meta.id) {
      cvBlock.hidden = true;
      return;
    }
    cvBlock.hidden = false;

    const tamanho = formatBytes(meta.arquivo_tamanho);
    cvFileName.textContent =
      (meta.arquivo || "currículo") + (tamanho ? " · " + tamanho : "");

    if (!meta.tem_arquivo) {
      cvActions.hidden = true;
      cvEmpty.hidden = false;
      return;
    }
    cvActions.hidden = false;
    cvEmpty.hidden = true;

    const url = `/api/analyses/${meta.id}/curriculo`;
    cvOpenLink.href = url;
    cvDownloadLink.href = url + "?download=1";

    // PDF e TXT abrem dentro da página; DOCX o navegador não renderiza.
    const mime = meta.arquivo_mime || "";
    const podeVerAqui = mime.indexOf("pdf") >= 0 || mime.indexOf("text/") === 0;
    cvPreviewBtn.hidden = !podeVerAqui;
    cvPreviewBtn.dataset.url = url;
  }

  if (cvPreviewBtn) {
    cvPreviewBtn.addEventListener("click", () => {
      const abrindo = cvPreview.hidden;
      cvFrame.src = abrindo ? cvPreviewBtn.dataset.url || "about:blank" : "about:blank";
      cvPreview.hidden = !abrindo;
      cvPreviewBtn.textContent = abrindo ? "Fechar" : "Ver aqui";
    });
  }

  // Mapeia o indicador do agente para rótulo padrão + classe de cor.
  const PCD_INDICADORES = {
    sem_interferencia: { key: "ok", label: "Sem interferência prevista" },
    compativel_com_adaptacoes: { key: "warn", label: "Compatível com adaptações" },
    requer_avaliacao_ocupacional: { key: "info", label: "Requer avaliação ocupacional" },
    nao_informado: { key: "muted", label: "Não informado" },
  };

  function renderPcd(pcd) {
    const block = document.getElementById("pcd-block");
    // Sem dado de PCD ou explicitamente não informado → esconde o bloco.
    const indicador = pcd && pcd.indicador;
    if (!pcd || !pcd.is_pcd || indicador === "nao_informado" || !indicador) {
      block.hidden = true;
      return;
    }
    block.hidden = false;

    const meta = PCD_INDICADORES[indicador] || PCD_INDICADORES.nao_informado;
    const card = document.getElementById("pcd-indicator");
    card.className = "pcd-indicator " + meta.key;

    document.getElementById("pcd-titulo").textContent = pcd.titulo || meta.label;
    document.getElementById("pcd-parecer").textContent = pcd.parecer || "—";

    const cond = document.getElementById("pcd-condicao");
    const condTxt = (pcd.condicao_declarada || "").trim();
    if (condTxt && condTxt.toLowerCase() !== "não informado") {
      cond.textContent = "Condição declarada: " + condTxt;
      cond.hidden = false;
    } else {
      cond.textContent = "";
      cond.hidden = true;
    }

    const atencao = pcd.pontos_atencao || [];
    const atWrap = document.getElementById("pcd-atencao-wrap");
    if (atencao.length) {
      atWrap.hidden = false;
      renderBullets("pcd-atencao", atencao, "");
    } else {
      atWrap.hidden = true;
    }

    const adapt = pcd.adaptacoes_sugeridas || [];
    const wrap = document.getElementById("pcd-adaptacoes-wrap");
    if (adapt.length) {
      wrap.hidden = false;
      renderBullets("pcd-adaptacoes", adapt, "");
    } else {
      wrap.hidden = true;
    }
  }

  const NOTA_LABELS = {
    experiencia: "Experiência",
    tecnico: "Técnico",
    formacao: "Formação",
    soft_skills: "Soft skills",
    estabilidade: "Estabilidade",
  };

  // Linha de score por vaga: cabeçalho clicável que expande para mostrar
  // resumo executivo, pontos fortes, pontos de atenção e notas por critério.
  function buildVagaRow(v) {
    const row = document.createElement("div");
    row.className = "vaga-score-row";
    const k = classKey(v.classificacao);

    const head = document.createElement("button");
    head.type = "button";
    head.className = "vaga-score-head";
    head.setAttribute("aria-expanded", "false");
    head.innerHTML = `
      <div class="vaga-score-info">
        <div class="title">${escapeHTML(v.vaga_titulo || "(sem título)")}</div>
        <div class="meta">${escapeHTML(v.classificacao || "")}</div>
      </div>
      <div class="score-mini ${k}">
        ${Number(v.score || 0).toFixed(1)} / 10
        <svg class="chevron" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <path d="M6 9l6 6 6-6" fill="none" stroke="currentColor"
            stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
    `;

    const detail = document.createElement("div");
    detail.className = "vaga-score-detail";
    detail.innerHTML = buildVagaDetailHTML(v);

    head.addEventListener("click", () => {
      const open = row.classList.toggle("open");
      head.setAttribute("aria-expanded", open ? "true" : "false");
    });

    row.appendChild(head);
    row.appendChild(detail);
    return row;
  }

  function buildVagaDetailHTML(v) {
    const parts = [];
    const resumo = v.resumo_executivo || v.resumo || "";
    if (resumo) {
      parts.push(`
        <div class="vaga-detail-block">
          <h5>Resumo executivo</h5>
          <p>${escapeHTML(String(resumo))}</p>
        </div>
      `);
    }
    parts.push(buildVagaDetailList("Pontos fortes", v.pontos_fortes, "strong"));
    parts.push(buildVagaDetailList("Pontos de atenção", v.pontos_atencao, "weak"));

    const notas = v.notas || {};
    const notaKeys = Object.keys(NOTA_LABELS).filter((nk) => notas[nk] != null);
    if (notaKeys.length) {
      const items = notaKeys
        .map((nk) => {
          const val = Number(notas[nk]) || 0;
          const pct = Math.max(0, Math.min(100, (val / 10) * 100));
          return `
            <div class="nota-row">
              <span class="nota-label">${NOTA_LABELS[nk]}</span>
              <span class="nota-bar"><span style="width:${pct}%"></span></span>
              <span class="nota-val">${val.toFixed(1)}</span>
            </div>
          `;
        })
        .join("");
      parts.push(`
        <div class="vaga-detail-block">
          <h5>Notas por critério</h5>
          <div class="nota-grid">${items}</div>
        </div>
      `);
    }

    const html = parts.filter(Boolean).join("");
    return (
      html ||
      `<p class="vaga-detail-empty">Sem detalhes adicionais para esta vaga.</p>`
    );
  }

  function buildVagaDetailList(title, items, variant) {
    if (!items || !items.length) return "";
    const lis = items.map((it) => `<li>${escapeHTML(String(it))}</li>`).join("");
    return `
      <div class="vaga-detail-block">
        <h5>${title}</h5>
        <ul class="vaga-detail-list ${variant}">${lis}</ul>
      </div>
    `;
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
  const historyFilterEmpty = document.getElementById("history-filter-empty");
  const historySummary = document.getElementById("history-summary");
  const historyFilters = document.getElementById("history-filters");

  let historyItems = [];
  let pcdFilter = "all"; // "all" | "pcd"

  // Considera PCD apenas quando o agente confirmou condição declarada com
  // indicador efetivo (ignora "nao_informado").
  function isPcd(it) {
    const p = it && it.pcd;
    return !!(p && p.is_pcd && p.indicador && p.indicador !== "nao_informado");
  }

  async function loadHistory() {
    try {
      const resp = await fetch("/api/analyses");
      const items = await resp.json();
      historyItems = Array.isArray(items) ? items : [];
    } catch (err) {
      toast("Erro ao carregar histórico: " + err.message, "error");
      return;
    }
    renderHistory();
  }

  function renderHistory() {
    historyList.innerHTML = "";
    historySummary.innerHTML = "";
    historyFilterEmpty.hidden = true;

    if (!historyItems.length) {
      historyEmpty.hidden = false;
      historyFilters.hidden = true;
      return;
    }
    historyEmpty.hidden = true;
    historyFilters.hidden = false;

    // Sumário — sempre sobre o conjunto completo (visão geral).
    const total = historyItems.length;
    const alta = historyItems.filter((i) => classKey(i.classificacao) === "alta").length;
    const media = historyItems.filter((i) => classKey(i.classificacao) === "media").length;
    const baixa = historyItems.filter((i) => classKey(i.classificacao) === "baixa").length;
    const pcdCount = historyItems.filter(isPcd).length;
    const avg =
      historyItems.reduce((acc, i) => acc + (Number(i.score_final) || 0), 0) /
      Math.max(total, 1);

    historySummary.innerHTML = `
      <div class="summary-card"><div class="num">${total}</div><div class="label">Total</div></div>
      <div class="summary-card"><div class="num alta">${alta}</div><div class="label">Alta aderência</div></div>
      <div class="summary-card"><div class="num media">${media}</div><div class="label">Média aderência</div></div>
      <div class="summary-card"><div class="num baixa">${baixa}</div><div class="label">Baixa aderência</div></div>
      <div class="summary-card"><div class="num pcd">${pcdCount}</div><div class="label">PCD</div></div>
      <div class="summary-card"><div class="num gold">${avg.toFixed(1)}</div><div class="label">Score médio</div></div>
    `;

    const rows = pcdFilter === "pcd" ? historyItems.filter(isPcd) : historyItems;
    if (!rows.length) {
      historyFilterEmpty.hidden = false;
      return;
    }

    rows.forEach((it) => {
      const row = document.createElement("div");
      row.className = "history-row";
      const k = classKey(it.classificacao);
      const pcdTag = isPcd(it)
        ? `<span class="pcd-tag" title="Pessoa com deficiência — parecer de acessibilidade no laudo">
             <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
               <circle cx="12" cy="4" r="2"/><path d="M19 13h-6V6"/><path d="M13 9.5l5 1.5"/>
               <path d="M9 8.5l1.5 6.5h4l3 5"/><circle cx="9" cy="18" r="3.5"/>
             </svg>PCD</span>`
        : "";
      const cvTag = it.tem_arquivo
        ? `<span class="cv-tag" title="Currículo guardado — abre no laudo">
             <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
               <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
             </svg>
           </span>`
        : "";
      row.innerHTML = `
        <div class="candidate">
          <div class="candidate-name"><span class="cand-name-text">${escapeHTML(it.candidato_nome || "(sem nome)")}</span>${pcdTag}${cvTag}</div>
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
  }

  // Recolher/expandir a seção de Acessibilidade / PCD.
  const pcdToggle = document.getElementById("pcd-toggle");
  if (pcdToggle) {
    pcdToggle.addEventListener("click", () => {
      const block = document.getElementById("pcd-block");
      const open = block.classList.toggle("open");
      pcdToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  if (historyFilters) {
    historyFilters.addEventListener("click", (e) => {
      const chip = e.target.closest("[data-pcd-filter]");
      if (!chip) return;
      pcdFilter = chip.getAttribute("data-pcd-filter");
      historyFilters
        .querySelectorAll(".filter-chip")
        .forEach((c) => c.classList.toggle("active", c === chip));
      renderHistory();
    });
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
        id: data.id,
        candidato: data.candidato_nome,
        arquivo: data.arquivo,
        criado_em: data.criado_em,
        tem_arquivo: data.tem_arquivo,
        arquivo_mime: data.arquivo_mime,
        arquivo_tamanho: data.arquivo_tamanho,
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
    if (cat === "triagem") return "Triagem";
    if (cat === "acesso") return "Acesso";
    if (cat === "usuario") return "Usuário";
    if (cat === "sistema") return "Sistema";
    return cat || "—";
  }

  function metaForAuditRow(ev) {
    const m = ev.meta || {};
    if (ev.category === "acesso" || ev.category === "usuario") {
      return m.usuario || m.email || "";
    }
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
      users: document.getElementById("status-users"),
      secret: document.getElementById("status-secret"),
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
      els.users.textContent =
        health.usuarios == null ? "—" : String(health.usuarios);
      els.secret.innerHTML = health.secret_key_configurada
        ? '<span class="ok">Configurada</span>'
        : '<span class="bad">Derivada (defina SECRET_KEY)</span>';
    } catch (_) {
      /* ignora */
    }
  }

  // ---------------------------------------------------------------
  // Sessão, usuários e senhas
  // ---------------------------------------------------------------
  const navUser = document.getElementById("nav-user");
  const logoutBtn = document.getElementById("logout-btn");
  const accountName = document.getElementById("account-name");
  const usersList = document.getElementById("users-list");
  const newUserBtn = document.getElementById("new-user-btn");
  const changeMyPasswordBtn = document.getElementById("change-my-password-btn");

  const userModal = document.getElementById("user-modal");
  const userNomeEl = document.getElementById("user-nome");
  const userEmailEl = document.getElementById("user-email");
  const userSenhaEl = document.getElementById("user-senha");
  const userSenha2El = document.getElementById("user-senha2");
  const userSaveBtn = document.getElementById("user-save-btn");
  const userCancelBtn = document.getElementById("user-cancel-btn");

  const senhaModal = document.getElementById("senha-modal");
  const senhaModalTitle = document.getElementById("senha-modal-title");
  const senhaModalDesc = document.getElementById("senha-modal-desc");
  const senhaAtualField = document.getElementById("senha-atual-field");
  const senhaAtualEl = document.getElementById("senha-atual");
  const senhaNovaEl = document.getElementById("senha-nova");
  const senhaNova2El = document.getElementById("senha-nova2");
  const senhaSaveBtn = document.getElementById("senha-save-btn");
  const senhaCancelBtn = document.getElementById("senha-cancel-btn");

  let me = null;
  let senhaAlvo = null; // null = trocar a própria senha; {id, nome} = redefinir

  async function loadMe() {
    try {
      const resp = await fetch("/api/auth/me");
      me = await resp.json();
    } catch (_) {
      return;
    }
    const label = me.nome || me.email || "—";
    if (navUser) {
      navUser.textContent = label;
      navUser.title = "Conectado como " + (me.email || label);
    }
    if (accountName) {
      accountName.textContent = me.email ? `${label} · ${me.email}` : label;
    }
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await fetch("/api/auth/logout", { method: "POST" });
      } catch (_) {
        /* sai de qualquer forma */
      }
      window.location.href = "/login";
    });
  }

  async function loadUsers() {
    if (!usersList) return;
    try {
      const resp = await fetch("/api/users");
      const users = await resp.json();
      if (!Array.isArray(users)) return;
      usersList.innerHTML = "";
      users.forEach((u) => {
        const row = document.createElement("div");
        row.className = "user-row";
        row.innerHTML = `
          <div class="user-ident">
            <div class="user-name">
              ${escapeHTML(u.nome || "—")}
              ${u.eu ? '<span class="user-you">você</span>' : ""}
            </div>
            <div class="user-email">${escapeHTML(u.email || "")}</div>
          </div>
          <div class="user-access">${
            u.ultimo_acesso
              ? "Último acesso: " + escapeHTML(formatDate(u.ultimo_acesso))
              : "Nunca acessou"
          }</div>
          <div class="user-row-actions">
            <button class="btn btn-ghost" data-action="senha">Redefinir senha</button>
            <button class="btn btn-danger" data-action="remover" ${u.eu ? "disabled" : ""}>
              Remover
            </button>
          </div>
        `;
        row
          .querySelector('[data-action="senha"]')
          .addEventListener("click", () => {
            if (u.eu) openSenhaModal(null);
            else openSenhaModal({ id: u.id, nome: u.nome || u.email });
          });
        row
          .querySelector('[data-action="remover"]')
          .addEventListener("click", async () => {
            if (
              !confirm(
                `Remover o acesso de "${u.nome || u.email}"? A pessoa não conseguirá mais entrar.`
              )
            )
              return;
            try {
              const r = await fetch(`/api/users/${u.id}`, { method: "DELETE" });
              const d = await r.json();
              if (!r.ok) throw new Error(d.error || "Erro ao remover.");
              toast("Usuário removido.", "success");
              loadUsers();
            } catch (err) {
              toast(err.message, "error");
            }
          });
        usersList.appendChild(row);
      });
    } catch (err) {
      toast("Erro ao carregar usuários: " + err.message, "error");
    }
  }

  function openUserModal() {
    userNomeEl.value = "";
    userEmailEl.value = "";
    userSenhaEl.value = "";
    userSenha2El.value = "";
    userModal.classList.add("show");
    setTimeout(() => userNomeEl.focus(), 80);
  }

  function closeUserModal() {
    userModal.classList.remove("show");
  }

  if (newUserBtn) newUserBtn.addEventListener("click", openUserModal);
  if (userCancelBtn) userCancelBtn.addEventListener("click", closeUserModal);
  if (userModal) {
    userModal.addEventListener("click", (e) => {
      if (e.target === userModal) closeUserModal();
    });
  }

  if (userSaveBtn) {
    userSaveBtn.addEventListener("click", async () => {
      const senha = userSenhaEl.value;
      if (senha !== userSenha2El.value) {
        toast("As senhas não coincidem.", "error");
        return;
      }
      if (senha.length < 8) {
        toast("A senha precisa ter pelo menos 8 caracteres.", "error");
        return;
      }
      userSaveBtn.disabled = true;
      try {
        const r = await fetch("/api/users", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            nome: userNomeEl.value.trim(),
            email: userEmailEl.value.trim(),
            senha: senha,
          }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || "Erro ao criar usuário.");
        toast("Usuário criado. Avise a pessoa da senha definida.", "success");
        closeUserModal();
        loadUsers();
      } catch (err) {
        toast(err.message, "error");
      } finally {
        userSaveBtn.disabled = false;
      }
    });
  }

  function openSenhaModal(alvo) {
    senhaAlvo = alvo;
    senhaAtualEl.value = "";
    senhaNovaEl.value = "";
    senhaNova2El.value = "";
    if (alvo) {
      senhaModalTitle.textContent = "Redefinir senha";
      senhaModalDesc.textContent =
        `Defina uma nova senha para ${alvo.nome} e avise a pessoa. ` +
        "A senha antiga deixa de funcionar na hora.";
      senhaAtualField.hidden = true;
    } else {
      senhaModalTitle.textContent = "Trocar minha senha";
      senhaModalDesc.textContent = "";
      senhaAtualField.hidden = false;
    }
    senhaModal.classList.add("show");
    setTimeout(() => (alvo ? senhaNovaEl : senhaAtualEl).focus(), 80);
  }

  function closeSenhaModal() {
    senhaModal.classList.remove("show");
    senhaAlvo = null;
  }

  if (changeMyPasswordBtn) {
    changeMyPasswordBtn.addEventListener("click", () => openSenhaModal(null));
  }
  if (senhaCancelBtn) senhaCancelBtn.addEventListener("click", closeSenhaModal);
  if (senhaModal) {
    senhaModal.addEventListener("click", (e) => {
      if (e.target === senhaModal) closeSenhaModal();
    });
  }

  if (senhaSaveBtn) {
    senhaSaveBtn.addEventListener("click", async () => {
      const nova = senhaNovaEl.value;
      if (nova !== senhaNova2El.value) {
        toast("As senhas não coincidem.", "error");
        return;
      }
      if (nova.length < 8) {
        toast("A senha precisa ter pelo menos 8 caracteres.", "error");
        return;
      }
      senhaSaveBtn.disabled = true;
      try {
        const url = senhaAlvo
          ? `/api/users/${senhaAlvo.id}/senha`
          : "/api/auth/senha";
        const body = senhaAlvo
          ? { senha: nova }
          : { senha_atual: senhaAtualEl.value, nova_senha: nova };
        const r = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || "Erro ao salvar a senha.");
        toast(senhaAlvo ? "Senha redefinida." : "Senha alterada.", "success");
        closeSenhaModal();
        loadUsers();
      } catch (err) {
        toast(err.message, "error");
      } finally {
        senhaSaveBtn.disabled = false;
      }
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (userModal && userModal.classList.contains("show")) closeUserModal();
    if (senhaModal && senhaModal.classList.contains("show")) closeSenhaModal();
  });

  loadMe();

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
