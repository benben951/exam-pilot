const STORAGE_KEY = "examPilotStateV1";

const starterCards = [
  {
    subject: "831经济学",
    topic: "委托代理",
    front: "委托代理模型的两条核心约束是什么？",
    back: "参与约束和激励相容约束。先保证代理人愿意接受合同，再保证代理人按委托人希望的努力水平行动。"
  },
  {
    subject: "数学",
    topic: "错题复盘",
    front: "一道数学错题复盘时，最少要记录哪三件事？",
    back: "错误类型、正确路径、下次识别信号。不要只抄解析。"
  },
  {
    subject: "英语一",
    topic: "阅读",
    front: "考研英语阅读错题最常见的三类问题是什么？",
    back: "定位错、同义替换没识别、被无中生有或范围错误的选项带走。"
  },
  {
    subject: "高考文科",
    topic: "刷题诊断",
    front: "高考文科刷题系统最应该记录什么？",
    back: "题目来源、知识点、错误原因、是否会迁移、下次复习时间。只记录分数不够。"
  }
];

const genericCardPatterns = [
  "最应该先掌握的关键词是什么？",
  "阶段，学习这份资料时应该验证什么？"
];

const starterMastery = [
  { subject: "数学", topic: "基础诊断", score: 35 },
  { subject: "英语一", topic: "阅读定位", score: 40 },
  { subject: "831经济学", topic: "模型卡片", score: 25 },
  { subject: "高考文科", topic: "基础诊断", score: 30 },
  { subject: "雅思", topic: "外企信号", score: 30 }
];

const subjectKeywords = [
  { subject: "数学", tags: ["极限", "导数", "积分", "矩阵", "线性代数", "微分方程", "知能行", "函数", "二次型"] },
  { subject: "英语一", tags: ["阅读", "长难句", "翻译", "作文", "同义替换", "完形", "新题型", "考研英语"] },
  { subject: "831经济学", tags: ["微观", "宏观", "经济学", "消费者", "生产者", "博弈", "委托代理", "Solow", "IS-LM", "货币"] },
  { subject: "政治", tags: ["马原", "毛中特", "史纲", "思修", "肖八", "肖四", "时政", "选择题"] },
  { subject: "高考语文", tags: ["高考语文", "语文", "现代文", "文言文", "古诗", "作文", "病句", "成语", "阅读理解"] },
  { subject: "高考数学", tags: ["高考数学", "函数", "数列", "立体几何", "解析几何", "概率", "导数", "三角函数", "圆锥曲线"] },
  { subject: "高考英语", tags: ["高考英语", "完形填空", "语法填空", "七选五", "续写", "应用文", "英语阅读"] },
  { subject: "高考历史", tags: ["高考历史", "中国古代史", "中国近代史", "世界史", "史料", "历史解释", "唯物史观"] },
  { subject: "高考政治", tags: ["高考政治", "经济生活", "政治生活", "文化生活", "哲学", "中特", "主观题"] },
  { subject: "高考地理", tags: ["高考地理", "自然地理", "人文地理", "区域地理", "等值线", "气候", "地貌", "人口", "产业"] },
  { subject: "雅思", tags: ["IELTS", "雅思", "口语", "听力", "小作文", "大作文", "part 2", "part 3"] },
  { subject: "技术/竞赛", tags: ["Python", "模型", "baseline", "AUC", "Kaggle", "TAAC", "agent", "RAG", "GitHub"] }
];

let state = loadState();
let currentCard = 0;
let remoteWeakness = null;
let monitoringReport = null;
let materialSearchPayload = null;
let selectedMaterialDetail = null;
let agentTasks = [];
let memoryObservations = [];
let speakingRecorder = null;
let speakingChunks = [];
let speakingStartedAt = null;
let speakingDurationSec = 0;
let currentSpeakingQuestion = null;
let lastSpeakingFeedback = null;
let speakingRecognition = null;
let speakingRecognitionActive = false;
let speakingFinalTranscript = "";
let economicsCards = [];

const speakingQuestions = {
  part1: [
    "Do you work or study?",
    "What do you usually do after work?",
    "Do you prefer studying alone or with other people?",
    "How often do you use technology in your daily life?",
    "What is one thing you like about your hometown?"
  ],
  part2: [
    "Describe a skill you learned that is useful for your work or study.",
    "Describe a person who encouraged you to make an important decision.",
    "Describe a difficult task you completed successfully.",
    "Describe a place where you can concentrate well.",
    "Describe a project you made with the help of AI."
  ],
  part3: [
    "Why do some people learn new skills faster than others?",
    "How has technology changed the way people prepare for exams?",
    "Should companies provide more training for young employees?",
    "What qualities are important for people who want to change their career?",
    "Do you think AI will make education fairer or more unequal?"
  ]
};

const speakingTargets = {
  part1: "建议 30-45 秒回答，重点练自然、直接、少停顿。",
  part2: "建议 90-120 秒回答，先给故事线，再补细节和感受。",
  part3: "建议 45-70 秒回答，先观点，再原因、例子和让步。"
};

const phasePlan = [
  {
    name: "7月：考研打底",
    focus: "数学二知能行稳定推进，831建立微观/宏观主干，雅思轻冲刺。",
    targets: ["数学每天 2 小时", "831 每天 45-90 分钟", "Anki 每周新增 30-50 张", "雅思主动训练每周 4 次"]
  },
  {
    name: "8-9月：雅思与求职窗口",
    focus: "可以考雅思和投北京外企，但数学和831不断线。",
    targets: ["数学每周 12 小时以上", "831 每周 6 小时以上", "完成外企简历和项目讲稿", "雅思考前两周做小冲刺"]
  },
  {
    name: "10月：政治启动与真题转换",
    focus: "政治用苍盾/肖1000启动，英语切回英语一真题，831进入真题输出。",
    targets: ["政治选择题每天 30-45 分钟", "英语一阅读真题每周 3 篇", "831 每周 2 道完整大题", "数学错题复测"]
  },
  {
    name: "11-12月：冲刺收口",
    focus: "模拟、错题、背诵框架，不再大面积开新坑。",
    targets: ["数学套卷/专题模拟", "831 真题二刷", "政治肖八肖四", "英语作文模板和阅读手感"]
  }
];

function loadState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw) {
    const parsed = JSON.parse(raw);
    return {
      records: parsed.records || [],
      cards: sanitizeCards(parsed.cards || starterCards),
      mastery: parsed.mastery || starterMastery,
      reviews: parsed.reviews || [],
      deepseekChats: parsed.deepseekChats || [],
      materials: parsed.materials || [],
      quizzes: parsed.quizzes || []
    };
  }
  return {
    records: [],
    cards: starterCards,
    mastery: starterMastery,
    reviews: [],
    deepseekChats: [],
    materials: [],
    quizzes: []
  };
}

function sanitizeCards(cards) {
  const seen = new Set();
  return cards.filter((card) => {
    const front = card.front || "";
    const isOldGeneric = genericCardPatterns.some((pattern) => front.includes(pattern));
    if (isOldGeneric) return false;
    const key = `${card.subject}|${card.topic}|${front}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  render();
}

function resetDemo() {
  state = {
    records: [],
    cards: starterCards,
    mastery: starterMastery,
    reviews: [],
    deepseekChats: [],
    materials: [],
    quizzes: []
  };
  currentCard = 0;
  saveState();
}

function switchView(viewId) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  document.getElementById(viewId).classList.add("active");
  document.querySelector(`[data-view="${viewId}"]`).classList.add("active");
  const titleMap = { dashboard: "总览", materials: "学习文件", diagnosis: "基线诊断", cards: "闪卡测验", economics: "831经济学", speaking: "IELTS口语", review: "周复盘", agent: "Agent", export: "数据" };
  document.getElementById("view-title").textContent = titleMap[viewId];
}

function updateMasteryFromRecord(record) {
  const existing = state.mastery.find((item) => item.subject === record.subject);
  const targetScore = Math.max(5, Math.min(95, Math.round(Number(record.accuracy) || 0)));
  if (existing) {
    existing.score = Math.round(existing.score * 0.65 + targetScore * 0.35);
    existing.topic = record.errorType;
  } else {
    state.mastery.push({ subject: record.subject, topic: record.errorType, score: targetScore });
  }
}

function renderMetrics() {
  const totalHours = state.records.reduce((sum, record) => sum + Number(record.hours || 0), 0);
  const rules = state.records.filter((record) => record.rule && record.rule.trim()).length;
  const weakest = [...state.mastery].sort((a, b) => a.score - b.score)[0];
  document.getElementById("metric-hours").textContent = totalHours.toFixed(1);
  document.getElementById("metric-rules").textContent = rules;
  document.getElementById("metric-cards").textContent = state.cards.length;
  document.getElementById("metric-materials").textContent = state.materials.length;
  document.getElementById("metric-risk").textContent = weakest ? weakest.subject : "待诊断";
}

function renderMonitoringReport() {
  const summary = document.getElementById("monitoring-summary");
  const reasons = document.getElementById("monitoring-reasons");
  const actions = document.getElementById("monitoring-actions");
  if (!summary || !reasons || !actions) return;
  const report = monitoringReport;
  if (!report) {
    summary.innerHTML = "<span>等待本地监测数据</span>";
    reasons.innerHTML = "<li>后端不可用时，启动本地服务即可查看报告。</li>";
    actions.innerHTML = "<li>先记录一次学习或周复盘。</li>";
    return;
  }
  const labels = { unknown: "待建立基线", low: "低风险", medium: "中风险", high: "高风险" };
  summary.innerHTML = `
    <div><strong>${report.studyHours.toFixed(1)}h</strong><span>近 ${report.windowDays} 天</span></div>
    <div><strong>${report.activeDays}</strong><span>活跃天数</span></div>
    <div><strong>${report.averageAccuracy}%</strong><span>平均正确率</span></div>
    <div><strong>${report.streakDays}</strong><span>连续记录</span></div>
    <div class="monitoring-risk ${report.riskLevel}"><strong>${labels[report.riskLevel] || report.riskLevel}</strong><span>当前状态</span></div>
  `;
  reasons.innerHTML = (report.riskReasons || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  actions.innerHTML = (report.nextActions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderMastery() {
  const container = document.getElementById("mastery-list");
  container.innerHTML = "";
  state.mastery.forEach((item) => {
    const node = document.createElement("div");
    node.className = "mastery-item";
    node.innerHTML = `
      <div class="mastery-top">
        <strong>${escapeHtml(item.subject)} · ${escapeHtml(item.topic)}</strong>
        <span>${item.score}%</span>
      </div>
      <div class="bar"><span style="width:${item.score}%"></span></div>
    `;
    container.appendChild(node);
  });
}

function renderActions() {
  const weakest = [...state.mastery].sort((a, b) => a.score - b.score).slice(0, 3);
  const actions = weakest.length
    ? weakest.map((item) => `${item.subject}：围绕“${item.topic}”做一次 30-60 分钟复盘或小测。`)
    : ["先完成一次基线诊断。"];
  actions.push("今天至少沉淀一条下次规则。");
  const container = document.getElementById("daily-actions");
  container.innerHTML = actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderPhasePlan() {
  const container = document.getElementById("phase-list");
  if (!container) return;
  container.innerHTML = phasePlan.map((phase, index) => `
    <article class="phase-item ${index === currentPhaseIndex() ? "active" : ""}">
      <strong>${escapeHtml(phase.name)}</strong>
      <p>${escapeHtml(phase.focus)}</p>
      <ul>
        ${phase.targets.map((target) => `<li>${escapeHtml(target)}</li>`).join("")}
      </ul>
    </article>
  `).join("");
}

function currentPhaseIndex() {
  const month = new Date().getMonth() + 1;
  if (month <= 7) return 0;
  if (month <= 9) return 1;
  if (month === 10) return 2;
  return 3;
}

function renderRecords() {
  const container = document.getElementById("record-list");
  document.getElementById("record-count").textContent = `${state.records.length} 条`;
  container.innerHTML = "";
  state.records.slice().reverse().forEach((record) => {
    const node = document.createElement("article");
    node.className = "record-item";
    node.innerHTML = `
      <h4>${escapeHtml(record.subject)} · ${record.accuracy}% · ${escapeHtml(record.errorType)}</h4>
      <p>${escapeHtml(record.note || "无学习记录")}</p>
      <p><strong>规则：</strong>${escapeHtml(record.rule || "待补充")}</p>
      <p>${escapeHtml(record.createdAt)}</p>
    `;
    container.appendChild(node);
  });
}

function renderReviewHistory() {
  const history = document.getElementById("review-history");
  const count = document.getElementById("review-history-count");
  if (!history || !count) return;
  count.textContent = `${state.reviews.length} 条`;
  history.innerHTML = state.reviews.length
    ? state.reviews.slice().reverse().map((review, index) => `
      <article class="review-history-item">
        <button class="search-result" data-review-index="${state.reviews.length - 1 - index}" type="button">
          <strong>${escapeHtml(review.createdAt || "未记录时间")}</strong>
          <small>${escapeHtml((review.output || "").slice(0, 160))}</small>
        </button>
      </article>
    `).join("")
    : `<div class="empty-state">还没有复盘记录。每周日保存一次，后面就能回溯你的阶段变化。</div>`;
}

function renderCard() {
  const card = state.cards[currentCard];
  const topic = document.getElementById("card-topic");
  const front = document.getElementById("card-front");
  const back = document.getElementById("card-back");
  if (!card) {
    topic.textContent = "暂无卡片";
    front.textContent = "先导入或生成闪卡";
    back.textContent = "";
    document.getElementById("card-position").textContent = "0 / 0";
    return;
  }
  topic.textContent = `${card.subject || "学习"} · ${card.topic || "通用"}`;
  front.textContent = card.front;
  back.textContent = card.back;
  back.classList.add("hidden");
  document.getElementById("card-position").textContent = `${currentCard + 1} / ${state.cards.length}`;
}

function renderExport() {
  document.getElementById("data-output").value = JSON.stringify(state, null, 2);
}

function scoreSubject(text) {
  const normalized = text.toLowerCase();
  const scored = subjectKeywords.map((item) => {
    const score = item.tags.reduce((sum, tag) => sum + (normalized.includes(tag.toLowerCase()) ? 1 : 0), 0);
    return { ...item, score };
  }).sort((a, b) => b.score - a.score);
  return scored[0].score > 0 ? scored[0].subject : "通用学习";
}

function extractTags(text) {
  const found = [];
  subjectKeywords.forEach((item) => {
    item.tags.forEach((tag) => {
      if (text.toLowerCase().includes(tag.toLowerCase())) found.push(tag);
    });
  });
  return [...new Set(found)].slice(0, 8);
}

function inferStage(text, tags) {
  const advancedSignals = ["真题", "综合", "限时", "证明", "推导", "复盘", "错题", "模型"];
  const intermediateSignals = ["练习", "例题", "方法", "题型", "应用", "模板"];
  const advancedScore = advancedSignals.filter((word) => text.includes(word)).length;
  const intermediateScore = intermediateSignals.filter((word) => text.includes(word)).length;
  if (advancedScore >= 2 || tags.length >= 6 || text.length > 1600) return "高级";
  if (intermediateScore >= 1 || tags.length >= 3 || text.length > 600) return "中级";
  return "初级";
}

function summarizeMaterial(text) {
  const clean = text.replace(/\s+/g, " ").trim();
  return clean.slice(0, 160) || "未提取到文本摘要";
}

function addMaterial({ title, text }) {
  if (!text.trim()) return;
  const tags = extractTags(text);
  const subject = scoreSubject(text);
  const stage = inferStage(text, tags);
  const material = {
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    title: title || `学习资料 ${state.materials.length + 1}`,
    subject,
    stage,
    tags,
    summary: summarizeMaterial(text),
    text,
    createdAt: new Date().toLocaleString("zh-CN")
  };
  state.materials.push(material);
  upsertMastery(material.subject, material.stage, stageToScore(material.stage));
  state.cards.push(...cardsFromMaterial(material));
}

function addMaterialRecord(material) {
  if (state.materials.some((item) => item.path && material.path && item.path === material.path)) return;
  const normalized = {
    id: material.id || (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`),
    title: material.title || "未命名资料",
    subject: material.subject || scoreSubject(material.text || material.title || ""),
    stage: material.stage || inferStage(material.text || "", material.tags || []),
    materialType: material.materialType || "资料索引",
    quizEligible: Boolean(material.quizEligible),
    hasExtractedText: Boolean(material.hasExtractedText),
    tags: material.tags || extractTags(material.text || material.title || ""),
    summary: material.summary || summarizeMaterial(material.text || ""),
    text: material.text || material.summary || material.title || "",
    path: material.path || "",
    isPriority: Boolean(material.isPriority),
    createdAt: material.createdAt || new Date().toLocaleString("zh-CN")
  };
  state.materials.push(normalized);
  upsertMastery(normalized.subject, normalized.stage, normalized.isPriority ? 52 : stageToScore(normalized.stage));
  state.cards.push(...contentCardsFromMaterial(normalized));
  state.cards = sanitizeCards(state.cards);
}

async function loadBackendCards() {
  const response = await fetch("/api/flashcards");
  if (!response.ok) throw new Error("flashcard api unavailable");
  const payload = await response.json();
  const cards = (payload.cards || []).map((card) => ({
    id: card.id,
    subject: card.subject,
    topic: card.topic,
    front: card.front,
    back: `${card.back}\n\n来源：${card.source || "后端题库"}`,
    card_type: card.card_type,
    quality: card.quality
  }));
  state.cards = sanitizeCards([...state.cards, ...cards]);
  return cards.length;
}

async function postStudyRecord(record) {
  try {
    const response = await fetch("/api/records", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(record)
    });
    if (!response.ok) return null;
    const payload = await response.json();
    remoteWeakness = payload.weaknesses || remoteWeakness;
    return payload.record || null;
  } catch (error) {
    return null;
  }
}

async function loadBackendRecords() {
  try {
    const response = await fetch("/api/records");
    if (!response.ok) return;
    const payload = await response.json();
    remoteWeakness = payload.weaknesses || remoteWeakness;
    const records = payload.records || [];
    if (!state.records.length && records.length) {
      state.records = records;
      saveState();
    } else {
      render();
    }
  } catch (error) {
    // LocalStorage remains the offline fallback.
  }
}

async function loadWeaknessReport() {
  try {
    const response = await fetch("/api/weaknesses");
    if (!response.ok) return;
    remoteWeakness = await response.json();
    render();
  } catch (error) {
    // Backend is optional for the static demo.
  }
}

async function loadMonitoringReport() {
  try {
    const response = await fetch("/api/monitoring");
    if (!response.ok) return;
    monitoringReport = await response.json();
    renderMonitoringReport();
  } catch (error) {
    renderMonitoringReport();
  }
}

async function loadAgentTasks() {
  try {
    const response = await fetch("/api/tasks");
    if (!response.ok) return;
    const payload = await response.json();
    agentTasks = payload.tasks || [];
    renderAgentOps();
  } catch (error) {
    // Agent board is optional in static mode.
  }
}

async function saveAgentTask(task) {
  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(task)
  });
  if (!response.ok) throw new Error("task api unavailable");
  const payload = await response.json();
  agentTasks = payload.tasks || [];
  renderAgentOps();
}

async function loadMemoryObservations(query = "") {
  try {
    const response = await fetch(`/api/memory?q=${encodeURIComponent(query)}`);
    if (!response.ok) return;
    const payload = await response.json();
    memoryObservations = payload.observations || [];
    renderAgentOps();
  } catch (error) {
    // Memory stays local-backend only.
  }
}

async function saveMemoryObservation(observation) {
  const response = await fetch("/api/memory", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(observation)
  });
  if (!response.ok) throw new Error("memory api unavailable");
  const payload = await response.json();
  memoryObservations = payload.observations || [];
  renderAgentOps();
}

async function searchMaterials(query) {
  const response = await fetch(`/api/materials/search?q=${encodeURIComponent(query || "")}&limit=12`);
  if (!response.ok) throw new Error("search api unavailable");
  materialSearchPayload = await response.json();
  selectedMaterialDetail = null;
  renderEvidenceSearch();
}

async function loadMaterialDetail(materialId) {
  const response = await fetch(`/api/materials/detail?id=${encodeURIComponent(materialId)}`);
  if (!response.ok) throw new Error("material detail unavailable");
  selectedMaterialDetail = await response.json();
  renderEvidenceSearch();
}

function upsertMastery(subject, topic, score) {
  const existing = state.mastery.find((item) => item.subject === subject && item.topic === topic);
  if (existing) {
    existing.score = Math.round(existing.score * 0.75 + score * 0.25);
  } else {
    state.mastery.push({ subject, topic, score });
  }
}

function stageToScore(stage) {
  if (stage === "高级") return 62;
  if (stage === "中级") return 45;
  return 25;
}

function cardsFromMaterial(material) {
  return contentCardsFromMaterial({ ...material, quizEligible: true, hasExtractedText: true });
}

function contentCardsFromMaterial(material) {
  if (material.materialType === "经验贴") return [];
  if (!material.quizEligible && !material.hasExtractedText) return [];
  const text = (material.text || "").replace(/\s+/g, " ").trim();
  if (text.length < 80) return [];
  const cards = [];
  const tags = material.tags.length ? material.tags : [material.subject];
  const snippets = selectStudySnippets(text, tags).slice(0, 3);
  snippets.forEach((snippet, index) => {
    const topic = tags[index % tags.length] || material.subject;
    cards.push({
      subject: material.subject,
      topic,
      front: `根据《${material.title}》，请主动回忆“${topic}”相关的一条可考规则或解题要点。`,
      back: snippet
    });
  });
  return cards;
}

function selectStudySnippets(text, tags) {
  const sentences = text
    .split(/[。！？；\n]/)
    .map((item) => item.trim())
    .filter((item) => item.length >= 28 && item.length <= 180);
  const tagged = sentences.filter((sentence) => tags.some((tag) => sentence.includes(tag)));
  const useful = tagged.length ? tagged : sentences;
  return useful.slice(0, 6);
}

function stageAdvice(stage) {
  if (stage === "高级") return "做迁移题、限时题或真题复盘，验证能否独立输出完整答案结构。";
  if (stage === "中级") return "做同类题，解释适用条件、方法选择和常见陷阱。";
  return "先主动回忆概念定义、公式含义和关键词，不急着刷难题。";
}

function generateQuizItems() {
  const quizMaterials = state.materials
    .filter((material) => material.quizEligible || material.hasExtractedText)
    .filter((material) => material.materialType !== "经验贴")
    .slice(-12);
  state.quizzes = quizMaterials.flatMap((material) => {
    const tag = material.tags[0] || material.subject;
    const text = (material.text || material.summary || "").replace(/\s+/g, " ").trim();
    const snippet = selectStudySnippets(text, material.tags || [tag])[0] || material.summary;
    return [
      {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
        materialId: material.id,
        subject: material.subject,
        topic: tag,
        stage: material.stage,
        question: `不看资料，回答《${material.title}》中“${tag}”相关的一个核心考点。`,
        expected: snippet,
        status: "未作答",
        createdAt: new Date().toLocaleString("zh-CN")
      },
      {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
        materialId: material.id,
        subject: material.subject,
        topic: material.stage,
        stage: material.stage,
        question: `${material.stage} 阶段：围绕“${tag}”设计一道同类题或复盘动作。`,
        expected: stageAdvice(material.stage),
        status: "未作答",
        createdAt: new Date().toLocaleString("zh-CN")
      }
    ];
  });
}

function answerQuiz(id, isCorrect) {
  const quiz = state.quizzes.find((item) => item.id === id);
  if (!quiz) return;
  quiz.status = isCorrect ? "已掌握" : "需复盘";
  const score = isCorrect ? 8 : -10;
  const existing = state.mastery.find((item) => item.subject === quiz.subject);
  if (existing) {
    existing.topic = quiz.topic;
    existing.score = Math.max(5, Math.min(95, existing.score + score));
  } else {
    state.mastery.push({ subject: quiz.subject, topic: quiz.topic, score: isCorrect ? 55 : 25 });
  }
  if (!isCorrect) {
    const record = {
      kind: "quiz",
      subject: quiz.subject,
      hours: 0,
      accuracy: 0,
      errorType: "阶段测验错误",
      note: quiz.question,
      rule: `回到资料《${findMaterialTitle(quiz.materialId)}》，围绕“${quiz.topic}”做一次主动回忆和同类题。`,
      createdAt: new Date().toLocaleString("zh-CN")
    };
    state.records.push(record);
    postStudyRecord(record).then((saved) => {
      if (saved) loadWeaknessReport();
    });
  }
}

function findMaterialTitle(id) {
  return state.materials.find((item) => item.id === id)?.title || "未知资料";
}

function renderMaterials() {
  const list = document.getElementById("material-list");
  const recommendations = document.getElementById("recommendation-list");
  const quizList = document.getElementById("quiz-list");
  const materialCount = document.getElementById("material-count");
  const quizCount = document.getElementById("quiz-count");
  if (!list || !recommendations || !quizList) return;

  materialCount.textContent = `${state.materials.length} 份`;
  list.innerHTML = state.materials.slice().reverse().map((material) => `
    <article class="material-item">
      <div>
        <strong>${escapeHtml(material.title)}</strong>
        <p>${escapeHtml(material.summary)}</p>
      </div>
      <div class="tag-row">
        <span>${escapeHtml(material.subject)}</span>
        <span>${escapeHtml(material.stage)}</span>
        ${material.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}
      </div>
    </article>
  `).join("") || `<div class="empty-state">还没有学习文件。先上传 txt/md，或者粘贴一段资料。</div>`;

  const weak = [...state.mastery].sort((a, b) => a.score - b.score).slice(0, 5);
  recommendations.innerHTML = weak.map((item) => `
    <article class="recommendation-item">
      <strong>${escapeHtml(item.subject)} · ${escapeHtml(item.topic)}</strong>
      <p>${escapeHtml(recommendationFor(item))}</p>
    </article>
  `).join("");

  quizCount.textContent = `${state.quizzes.length} 题`;
  quizList.innerHTML = state.quizzes.map((quiz) => `
    <article class="quiz-item">
      <div>
        <strong>${escapeHtml(quiz.subject)} · ${escapeHtml(quiz.stage)}</strong>
        <p>${escapeHtml(quiz.question)}</p>
        <small>参考：${escapeHtml(quiz.expected)}</small>
      </div>
      <div class="quiz-actions">
        <span>${escapeHtml(quiz.status)}</span>
        <button class="ghost-button" data-quiz="${quiz.id}" data-result="wrong" type="button">做错了</button>
        <button class="primary-button" data-quiz="${quiz.id}" data-result="right" type="button">做对了</button>
      </div>
    </article>
  `).join("") || `<div class="empty-state">点击“生成阶段测验”，系统会从最近资料里出题。</div>`;
}

function renderBackendWeakness() {
  const weaknessList = document.getElementById("backend-weakness-list");
  const gapList = document.getElementById("backend-gap-list");
  if (!weaknessList || !gapList) return;
  if (!remoteWeakness) {
    weaknessList.innerHTML = `<div class="empty-state">后端薄弱点还没有加载。启动本地服务后会自动汇总诊断记录和题库质量。</div>`;
    gapList.innerHTML = `<div class="empty-state">资料缺口会显示待 OCR、已解析和失败状态。</div>`;
    return;
  }

  const subjectWeak = remoteWeakness.subjectWeaknesses || [];
  const cardWeak = remoteWeakness.flashcardWeaknesses || [];
  const merged = [
    ...subjectWeak.map((item) => ({
      title: `${item.subject} · 正确率 ${item.score}%`,
      detail: `${item.source || "诊断记录"}，样本 ${item.count} 条。下一步：围绕最低正确率科目做 20 分钟主动回忆。`
    })),
    ...cardWeak.slice(0, 4).map((item) => ({
      title: `${item.subject} · ${item.topic}`,
      detail: `题库平均质量 ${item.score}，卡片 ${item.count} 张。下一步：检索这个主题，补成“定义-条件-陷阱-真题”四格笔记。`
    }))
  ].slice(0, 8);

  weaknessList.innerHTML = merged.length
    ? merged.map((item) => `
      <article class="weakness-item">
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.detail)}</p>
      </article>
    `).join("")
    : `<div class="empty-state">还没有足够的做题记录。先录入一次诊断，系统就会开始计算薄弱点。</div>`;

  const status = remoteWeakness.materialStatus || {};
  const gaps = remoteWeakness.ocrGaps || [];
  const statusText = Object.entries(status).map(([key, value]) => `${key}: ${value}`).join(" / ") || "暂无状态";
  gapList.innerHTML = `
    <article class="weakness-item">
      <strong>资料状态</strong>
      <p>${escapeHtml(statusText)}</p>
    </article>
    ${gaps.slice(0, 5).map((item) => `
      <article class="weakness-item">
        <strong>${escapeHtml(item.title)}</strong>
        <p>待 OCR · ${escapeHtml(item.path)}</p>
      </article>
    `).join("")}
  `;
}

function renderEvidenceSearch() {
  const results = document.getElementById("material-search-results");
  const detail = document.getElementById("material-detail");
  if (!results || !detail) return;
  if (!materialSearchPayload) {
    results.innerHTML = `<div class="empty-state">输入关键词后，会从本地 DB 的 materials/chunks 里找资料和证据片段。</div>`;
    detail.innerHTML = `<div class="empty-state">点开某个资料后，这里会显示摘要、路径、证据片段和已生成卡片。</div>`;
    return;
  }
  const materials = materialSearchPayload.materials || [];
  const evidence = materialSearchPayload.evidence || [];
  results.innerHTML = `
    <div class="search-summary">找到 ${materials.length} 份资料，${evidence.length} 条证据片段</div>
    ${materials.map((material) => `
      <button class="search-result" data-material-id="${escapeHtml(material.id)}" type="button">
        <strong>${escapeHtml(material.title)}</strong>
        <span>${escapeHtml(material.subject || "通用")} · ${escapeHtml(material.status || "unknown")} · ${escapeHtml(material.materialType || "")}</span>
        <small>${escapeHtml(material.summary || material.path || "")}</small>
      </button>
    `).join("")}
    ${!materials.length ? `<div class="empty-state">没有命中资料。试试更短的关键词，比如“效用”“831”“长难句”。</div>` : ""}
  `;

  if (!selectedMaterialDetail) {
    detail.innerHTML = evidence.length
      ? evidence.slice(0, 8).map((item) => `
        <article class="evidence-item">
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.excerpt)}</p>
          <small>${escapeHtml(item.path)} · chunk ${item.chunkIndex}</small>
        </article>
      `).join("")
      : `<div class="empty-state">暂无证据片段。</div>`;
    return;
  }

  const material = selectedMaterialDetail.material;
  const chunks = selectedMaterialDetail.chunks || [];
  const cards = selectedMaterialDetail.flashcards || [];
  detail.innerHTML = `
    <article class="detail-card">
      <strong>${escapeHtml(material.title)}</strong>
      <p>${escapeHtml(material.summary || "暂无摘要")}</p>
      <div class="tag-row">
        <span>${escapeHtml(material.subject || "通用")}</span>
        <span>${escapeHtml(material.status || "unknown")}</span>
        <span>${escapeHtml(String(material.extractedChars || 0))} chars</span>
      </div>
      <small>${escapeHtml(material.path || "")}</small>
    </article>
    ${chunks.slice(0, 5).map((chunk) => `
      <article class="evidence-item">
        <strong>证据 chunk ${chunk.chunkIndex}</strong>
        <p>${escapeHtml(chunk.text.slice(0, 360))}</p>
        <small>${escapeHtml(chunk.tags || "")}</small>
      </article>
    `).join("")}
    ${cards.slice(0, 4).map((card) => `
      <article class="evidence-item">
        <strong>${escapeHtml(card.topic || "闪卡")}</strong>
        <p>${escapeHtml(card.front)}</p>
        <small>${escapeHtml(card.back.slice(0, 180))}</small>
      </article>
    `).join("")}
  `;
}

function renderAgentOps() {
  const taskBoard = document.getElementById("task-board");
  const memoryList = document.getElementById("memory-list");
  if (!taskBoard || !memoryList) return;

  const lanes = [
    { key: "todo", label: "待做" },
    { key: "doing", label: "进行中" },
    { key: "blocked", label: "卡住" },
    { key: "done", label: "完成" }
  ];

  taskBoard.innerHTML = lanes.map((lane) => {
    const tasks = agentTasks.filter((task) => (task.status || "todo") === lane.key);
    return `
      <section class="task-lane">
        <h4>${lane.label}<span>${tasks.length}</span></h4>
        ${tasks.map((task) => `
          <article class="task-card">
            <strong>${escapeHtml(task.title)}</strong>
            <p>${escapeHtml(task.detail || task.source || "暂无详情")}</p>
            <div class="tag-row">
              <span>${escapeHtml(task.lane || "system")}</span>
              <span>${escapeHtml(task.priority || "medium")}</span>
            </div>
            <div class="mini-actions">
              ${["todo", "doing", "blocked", "done"].map((status) => `
                <button class="ghost-button" data-task-id="${escapeHtml(task.id)}" data-task-status="${status}" type="button">${status}</button>
              `).join("")}
            </div>
          </article>
        `).join("") || `<div class="empty-state">暂无任务</div>`}
      </section>
    `;
  }).join("");

  memoryList.innerHTML = memoryObservations.length
    ? memoryObservations.slice(0, 12).map((item) => `
      <article class="memory-item">
        <strong>${escapeHtml(item.subject)} · ${escapeHtml(item.kind)}</strong>
        <p>${escapeHtml(item.text)}</p>
        <small>${escapeHtml(item.createdAt)} ${item.source ? `· ${escapeHtml(item.source)}` : ""}</small>
      </article>
    `).join("")
    : `<div class="empty-state">还没有长期记忆。先记录一条“这个策略有效/这个资料重要/这个错因反复出现”。</div>`;
}

function pickSpeakingQuestion(part = "part1") {
  const bank = speakingQuestions[part] || speakingQuestions.part1;
  const previous = currentSpeakingQuestion?.question;
  const candidates = bank.filter((question) => question !== previous);
  const question = (candidates.length ? candidates : bank)[Math.floor(Math.random() * (candidates.length || bank.length))];
  currentSpeakingQuestion = { part, question };
  speakingDurationSec = 0;
  const transcript = document.getElementById("speaking-transcript");
  if (transcript) transcript.value = "";
  renderSpeaking();
}

function renderSpeaking() {
  const partSelect = document.getElementById("speaking-part");
  if (!partSelect) return;
  if (!currentSpeakingQuestion) {
    currentSpeakingQuestion = { part: partSelect.value, question: speakingQuestions[partSelect.value][0] };
  }
  document.getElementById("speaking-part-label").textContent = currentSpeakingQuestion.part.toUpperCase().replace("PART", "Part ");
  document.getElementById("speaking-question").textContent = currentSpeakingQuestion.question;
  document.getElementById("speaking-target").textContent = speakingTargets[currentSpeakingQuestion.part] || speakingTargets.part1;
  if (lastSpeakingFeedback) {
    renderSpeakingFeedback(lastSpeakingFeedback);
  }
}

function localSpeakingFeedback({ transcript, part, question, durationSec }) {
  const clean = transcript.replace(/\s+/g, " ").trim();
  const words = clean ? clean.split(/\s+/).length : 0;
  const fillerMatches = clean.match(/\b(um|uh|er|like|you know|actually|basically)\b/gi) || [];
  const sentenceCount = (clean.match(/[.!?。！？]/g) || []).length || Math.max(1, Math.ceil(words / 18));
  const wordsPerSentence = words / sentenceCount;
  const targetMin = part === "part2" ? 90 : part === "part3" ? 45 : 25;
  const targetMax = part === "part2" ? 140 : part === "part3" ? 80 : 55;
  let band = 5.5;
  if (words >= 60) band += 0.4;
  if (words >= 120) band += 0.3;
  if (durationSec >= targetMin && durationSec <= targetMax) band += 0.3;
  if (fillerMatches.length > 4) band -= 0.3;
  if (wordsPerSentence > 28 || wordsPerSentence < 7) band -= 0.2;
  band = Math.max(4.5, Math.min(7.5, Math.round(band * 2) / 2));
  return {
    bandEstimate: `${band}`,
    fluency: words < 40 ? "回答长度偏短。先练 3 句稳定结构：直接回答、补原因、给例子。" : `词数约 ${words}，长度基本可用。下一步减少填充词和重复开头。`,
    vocabulary: "目前按转写文本粗评：建议每次回答至少加入 2 个主题词和 1 个更具体的动词/形容词。",
    grammar: "优先保证简单句准确，再加入 because/although/which 引导的复合句。不要为了复杂而牺牲清晰。",
    pronunciation: "未配置 Azure Speech Pronunciation Assessment，暂不能给音素级发音分数。",
    topProblems: [
      fillerMatches.length ? `填充词偏多：${[...new Set(fillerMatches.map((item) => item.toLowerCase()))].join(", ")}` : "还需要真实转写或更长回答来判断停顿问题。",
      durationSec ? `本次录音约 ${durationSec} 秒。` : "还没有可用录音时长。",
      "发音细节需要接入 Azure Speech key 后评估。"
    ],
    betterVersion: buildBetterSpeakingVersion(question, part),
    nextQuestion: speakingQuestions[part][(speakingQuestions[part].indexOf(question) + 1) % speakingQuestions[part].length],
    source: "local_fallback",
    pronunciationStatus: "not_configured"
  };
}

function buildBetterSpeakingVersion(question, part) {
  if (part === "part2") {
    return `I would like to talk about this topic in three parts: what happened, why it mattered to me, and what I learned from it. For example, when I prepared for a demanding project, I had to break the task into smaller steps and review my progress every day. It was challenging, but it made me more disciplined and confident.`;
  }
  if (part === "part3") {
    return `In my view, it depends on both personal motivation and the environment. Some people improve quickly because they receive clear feedback and practise consistently. However, resources also matter, because good tools and teachers can reduce wasted effort.`;
  }
  return `Yes, I do. I think it is important because it affects my daily routine. For example, I often use it when I study or work, and it helps me save time and stay organised.`;
}

function buildDeepSeekStudyPrompt(question) {
  const recentReviews = state.reviews.slice(-3).map((item) => item.output).join("\n\n---\n\n");
  const weakest = [...state.mastery].sort((a, b) => a.score - b.score).slice(0, 5);
  return [
    "你是郭兆杰的在职考研复盘教练。请用中文回答，具体、可执行、不要空话。",
    "总优先级：数学二 > 831经济学 > 雅思/英语一 > 政治 > 求职技术。",
    "当前阶段任务：",
    JSON.stringify(phasePlan[currentPhaseIndex()], null, 2),
    "最近复盘：",
    recentReviews || "暂无复盘。",
    "当前薄弱项：",
    JSON.stringify(weakest, null, 2),
    "我的问题：",
    question,
    "请输出：1. 判断 2. 具体调整 3. 今天/明天动作 4. 需要记录的数据。"
  ].join("\n\n");
}

async function askDeepSeek() {
  const input = document.getElementById("deepseek-question");
  const output = document.getElementById("review-output");
  const question = input.value.trim();
  if (!question) {
    output.textContent = "先输入你想问的问题。";
    return;
  }
  output.textContent = "正在调用 DeepSeek/本地 AI 接口...";
  try {
    const response = await fetch("/api/deepseek/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: buildDeepSeekStudyPrompt(question), state })
    });
    const payload = await response.json();
    if (!response.ok) {
      output.textContent = payload.message || payload.error || "AI 接口暂不可用。";
      return;
    }
    const answer = payload.analysis || JSON.stringify(payload, null, 2);
    state.deepseekChats.push({ question, answer, createdAt: new Date().toLocaleString("zh-CN") });
    output.textContent = answer;
    input.value = "";
    saveState();
  } catch (error) {
    output.textContent = "AI 接口调用失败：请确认后端已启动，并检查 .env.local 里的 API 配置。";
  }
}

function renderSpeakingFeedback(feedback) {
  const container = document.getElementById("speaking-feedback");
  if (!container) return;
  document.getElementById("speaking-api-status").textContent = feedback.source === "model" ? "AI feedback" : "Local fallback";
  const problems = feedback.topProblems || [];
  container.innerHTML = `
    <article class="feedback-score">
      <span>Band Estimate</span>
      <strong>${escapeHtml(feedback.bandEstimate || "待评估")}</strong>
      <small>${escapeHtml(feedback.pronunciationStatus === "not_configured" ? "发音 API 未配置" : "已含发音评估")}</small>
    </article>
    <article class="feedback-block"><strong>流利度</strong><p>${escapeHtml(feedback.fluency || "")}</p></article>
    <article class="feedback-block"><strong>词汇</strong><p>${escapeHtml(feedback.vocabulary || "")}</p></article>
    <article class="feedback-block"><strong>语法</strong><p>${escapeHtml(feedback.grammar || "")}</p></article>
    <article class="feedback-block"><strong>发音</strong><p>${escapeHtml(feedback.pronunciation || "")}</p></article>
    <article class="feedback-block"><strong>优先修正</strong><ul>${problems.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></article>
    <article class="feedback-block"><strong>参考改写</strong><p>${escapeHtml(feedback.betterVersion || "")}</p></article>
    <article class="feedback-block"><strong>下一题</strong><p>${escapeHtml(feedback.nextQuestion || "")}</p></article>
  `;
}

function renderEconomicsCards() {
  const list = document.getElementById("econ-card-list");
  const count = document.getElementById("econ-preview-count");
  const sync = document.getElementById("econ-sync");
  if (!list || !count || !sync) return;
  count.textContent = `${economicsCards.length} 张`;
  sync.disabled = economicsCards.length === 0;
  if (!economicsCards.length) {
    list.innerHTML = `<div class="empty-state">生成后会在这里预览卡片正面、背面和考试提示。</div>`;
    return;
  }
  list.innerHTML = economicsCards.map((card, index) => `
    <article class="econ-card-preview">
      <div class="econ-card-top">
        <strong>${escapeHtml(card.topic || "831经济学")}</strong>
        <button class="ghost-button" data-econ-remove="${index}" type="button">删除</button>
      </div>
      <p><b>正面：</b>${escapeHtml(card.front || "")}</p>
      <p><b>背面：</b>${escapeHtml(card.back || "")}</p>
      <small>${escapeHtml(card.exam_note || "")}</small>
    </article>
  `).join("");
}

async function generateEconomicsCards() {
  const status = document.getElementById("econ-status");
  const text = document.getElementById("econ-input").value.trim();
  if (!text) {
    status.textContent = "先粘贴一小节材料";
    return;
  }
  const payload = {
    text,
    deck: document.getElementById("econ-deck").value,
    topic: document.getElementById("econ-topic").value.trim() || "831经济学",
    source: document.getElementById("econ-source").value.trim() || "ExamPilot 831经济学网页",
    limit: Number(document.getElementById("econ-limit").value || 8)
  };
  status.textContent = "正在生成卡片...";
  try {
    const response = await fetch("/api/economics/cards/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.error || "生成失败");
    economicsCards = data.cards || [];
    status.textContent = `已生成 ${economicsCards.length} 张，先检查再同步`;
    renderEconomicsCards();
  } catch (error) {
    status.textContent = `生成失败：${error.message}`;
  }
}

async function syncEconomicsCards() {
  const status = document.getElementById("econ-status");
  if (!economicsCards.length) return;
  status.textContent = "正在同步到 Anki...";
  try {
    const response = await fetch("/api/economics/cards/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cards: economicsCards })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.hint || data.message || data.error || "同步失败");
    status.textContent = `同步完成：新增 ${data.added} 张，跳过 ${data.failed} 张`;
  } catch (error) {
    status.textContent = `同步失败：${error.message}`;
  }
}

async function startSpeakingRecording() {
  if (!navigator.mediaDevices?.getUserMedia) {
    document.getElementById("recording-status").innerHTML = `<strong>浏览器不支持录音</strong><span>可以先手动输入转写文本练反馈。</span>`;
    return;
  }
  stopSpeechRecognition();
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  speakingChunks = [];
  const options = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? { mimeType: "audio/webm;codecs=opus" } : undefined;
  speakingRecorder = new MediaRecorder(stream, options);
  speakingStartedAt = Date.now();
  speakingRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) speakingChunks.push(event.data);
  };
  speakingRecorder.onstop = () => {
    speakingDurationSec = Math.max(1, Math.round((Date.now() - speakingStartedAt) / 1000));
    stream.getTracks().forEach((track) => track.stop());
    const blob = new Blob(speakingChunks, { type: speakingRecorder.mimeType || "audio/webm" });
    const audio = document.getElementById("speaking-audio");
    if (audio.src) URL.revokeObjectURL(audio.src);
    audio.src = URL.createObjectURL(blob);
    audio.load();
    const sizeKb = Math.round(blob.size / 1024);
    document.getElementById("recording-status").innerHTML = `<strong>录音完成</strong><span>${speakingDurationSec} 秒，音频约 ${sizeKb} KB。若要自动转写，请用“自动识别”单独练一遍，或后续接 Whisper/Azure 从音频转写。</span>`;
    document.getElementById("record-start").disabled = false;
    document.getElementById("record-stop").disabled = true;
  };
  speakingRecorder.start(250);
  document.getElementById("recording-status").innerHTML = `<strong>录音中</strong><span>正在保存真实音频。为了避免麦克风冲突，自动识别已切到单独按钮。</span>`;
  document.getElementById("record-start").disabled = true;
  document.getElementById("record-stop").disabled = false;
}

function stopSpeakingRecording() {
  stopSpeechRecognition();
  if (speakingRecorder && speakingRecorder.state === "recording") {
    speakingRecorder.stop();
  }
}

function startSpeechRecognition({ silentIfUnsupported = false } = {}) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const button = document.getElementById("speech-recognize");
  const transcript = document.getElementById("speaking-transcript");
  if (!SpeechRecognition) {
    if (!silentIfUnsupported) {
      document.getElementById("recording-status").innerHTML = `<strong>暂不支持自动识别</strong><span>当前浏览器没有 Web Speech API。后续可接 Whisper 或 Azure Speech 做稳定转写。</span>`;
    }
    if (button) {
      button.textContent = "识别不可用";
      button.disabled = true;
    }
    return;
  }
  if (speakingRecognitionActive) return;
  speakingFinalTranscript = transcript.value.trim();
  speakingRecognition = new SpeechRecognition();
  speakingRecognition.lang = "en-US";
  speakingRecognition.continuous = true;
  speakingRecognition.interimResults = true;
  speakingRecognition.maxAlternatives = 1;
  speakingRecognition.onresult = (event) => {
    let interim = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const text = event.results[index][0].transcript;
      if (event.results[index].isFinal) {
        speakingFinalTranscript = `${speakingFinalTranscript} ${text}`.trim();
      } else {
        interim += text;
      }
    }
    transcript.value = `${speakingFinalTranscript}${interim ? ` ${interim}` : ""}`.trim();
  };
  speakingRecognition.onerror = () => {
    speakingRecognitionActive = false;
    if (button) button.textContent = "重新识别";
  };
  speakingRecognition.onend = () => {
    speakingRecognitionActive = false;
    if (button) button.textContent = "自动识别";
  };
  speakingRecognitionActive = true;
  if (button) button.textContent = "识别中";
  speakingRecognition.start();
}

function stopSpeechRecognition() {
  if (speakingRecognition && speakingRecognitionActive) {
    speakingRecognition.stop();
  }
  speakingRecognitionActive = false;
  const button = document.getElementById("speech-recognize");
  if (button) button.textContent = "自动识别";
}

async function submitSpeakingAnalysis() {
  const transcript = document.getElementById("speaking-transcript").value.trim();
  const feedbackPanel = document.getElementById("speaking-feedback");
  if (!transcript) {
    feedbackPanel.innerHTML = `<div class="empty-state">先把你刚才说的英文转写到文本框里，我再给你做内容、流利度、词汇和语法反馈。</div>`;
    return;
  }
  const payload = {
    part: currentSpeakingQuestion.part,
    question: currentSpeakingQuestion.question,
    transcript,
    durationSec: speakingDurationSec
  };
  feedbackPanel.innerHTML = `<div class="empty-state">正在分析这次口语回答...</div>`;
  try {
    const response = await fetch("/api/ielts/speaking/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.error || "speaking api unavailable");
    lastSpeakingFeedback = data.feedback || data;
  } catch (error) {
    lastSpeakingFeedback = localSpeakingFeedback(payload);
  }
  renderSpeakingFeedback(lastSpeakingFeedback);
}

async function saveSpeakingAsRecord() {
  if (!lastSpeakingFeedback || !currentSpeakingQuestion) return;
  const record = {
    kind: "ielts_speaking",
    subject: "雅思",
    hours: Math.max(0.1, speakingDurationSec / 3600),
    accuracy: Number.parseFloat(lastSpeakingFeedback.bandEstimate) ? Math.round(Number.parseFloat(lastSpeakingFeedback.bandEstimate) * 12.5) : 60,
    errorType: "口语输出",
    note: `${currentSpeakingQuestion.part}：${currentSpeakingQuestion.question}\n${document.getElementById("speaking-transcript").value.trim()}`,
    rule: (lastSpeakingFeedback.topProblems || []).join("；") || "下一次回答要补充原因、例子和清晰结尾。",
    createdAt: new Date().toLocaleString("zh-CN")
  };
  state.records.push(record);
  updateMasteryFromRecord(record);
  saveState();
  await postStudyRecord(record);
  document.getElementById("speaking-api-status").textContent = "已保存";
}

function recommendationFor(item) {
  if (item.subject.startsWith("高考")) {
    if (item.score < 35) return "先回到课本与基础题：明确考点、题型和标准答案表达。";
    if (item.score < 60) return "进入专题刷题：按题型整理错因，并做同类题复测。";
    return "进入综合卷和限时训练：重点看材料提取、答题模板和稳定性。";
  }
  if (item.score < 35) return "先回到初级：做概念卡片和主动回忆，不要急着刷综合题。";
  if (item.score < 60) return "进入中级：做同类题，记录错误类型和下次识别信号。";
  return "进入高级：做限时真题或迁移题，验证是否能独立输出。";
}

function render() {
  renderMetrics();
  renderMonitoringReport();
  renderMastery();
  renderActions();
  renderPhasePlan();
  renderRecords();
  renderReviewHistory();
  renderCard();
  renderMaterials();
  renderSpeaking();
  renderBackendWeakness();
  renderEvidenceSearch();
  renderAgentOps();
  renderExport();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

document.getElementById("save-now").addEventListener("click", saveState);
document.getElementById("reset-demo").addEventListener("click", resetDemo);

document.getElementById("diagnosis-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const record = {
    kind: "diagnosis",
    subject: data.get("subject"),
    hours: Number(data.get("hours")),
    accuracy: Number(data.get("accuracy")),
    errorType: data.get("errorType"),
    note: data.get("note"),
    rule: data.get("rule"),
    createdAt: new Date().toLocaleString("zh-CN")
  };
  state.records.push(record);
  updateMasteryFromRecord(record);
  if (record.rule) {
    state.cards.push({
      subject: record.subject,
      topic: record.errorType,
      front: `下次遇到“${record.errorType}”类问题时，应该先检查什么？`,
      back: record.rule
    });
  }
  event.currentTarget.reset();
  saveState();
  postStudyRecord(record).then((saved) => {
    if (saved) loadWeaknessReport();
  });
});

document.getElementById("show-answer").addEventListener("click", () => {
  document.getElementById("card-back").classList.toggle("hidden");
});

document.getElementById("prev-card").addEventListener("click", () => {
  if (!state.cards.length) return;
  currentCard = (currentCard - 1 + state.cards.length) % state.cards.length;
  renderCard();
});

document.getElementById("next-card").addEventListener("click", () => {
  if (!state.cards.length) return;
  currentCard = (currentCard + 1) % state.cards.length;
  renderCard();
});

document.getElementById("load-db-cards").addEventListener("click", async () => {
  const button = document.getElementById("load-db-cards");
  button.textContent = "加载中...";
  button.disabled = true;
  try {
    const count = await loadBackendCards();
    button.textContent = `已加载 ${count} 张`;
    saveState();
  } catch (error) {
    button.textContent = "后端题库不可用";
  } finally {
    setTimeout(() => {
      button.textContent = "加载后端题库";
      button.disabled = false;
    }, 1600);
  }
});

document.getElementById("import-cards").addEventListener("click", () => {
  const raw = document.getElementById("card-import").value.trim();
  if (!raw) return;
  const cards = raw
    .split(/\n+/)
    .map((line) => JSON.parse(line))
    .filter((card) => card.front && card.back);
  state.cards.push(...cards);
  document.getElementById("card-import").value = "";
  saveState();
});

document.getElementById("material-file").addEventListener("change", async (event) => {
  const files = Array.from(event.currentTarget.files || []);
  for (const file of files) {
    const text = await file.text();
    addMaterial({ title: file.name, text });
  }
  event.currentTarget.value = "";
  saveState();
});

document.getElementById("add-material-text").addEventListener("click", () => {
  const textarea = document.getElementById("material-text");
  const text = textarea.value.trim();
  if (!text) return;
  addMaterial({ title: `粘贴资料 ${state.materials.length + 1}`, text });
  textarea.value = "";
  saveState();
});

document.getElementById("generate-quiz").addEventListener("click", () => {
  generateQuizItems();
  saveState();
});

document.getElementById("preload-materials").addEventListener("click", async () => {
  const button = document.getElementById("preload-materials");
  button.textContent = "导入中...";
  button.disabled = true;
  try {
    const response = await fetch("/api/materials/preload");
    if (!response.ok) throw new Error("local api unavailable");
    const payload = await response.json();
    payload.materials.forEach(addMaterialRecord);
    await loadBackendCards();
    generateQuizItems();
    saveState();
  } catch (error) {
    document.getElementById("material-text").value = "本地 API 未启动。请在项目目录运行：python server.py";
  } finally {
    button.textContent = "导入本地笔记";
    button.disabled = false;
  }
});

document.getElementById("quiz-list").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-quiz]");
  if (!button) return;
  answerQuiz(button.dataset.quiz, button.dataset.result === "right");
  saveState();
});

document.getElementById("review-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const weakest = [...state.mastery].sort((a, b) => a.score - b.score)[0];
  const currentPhase = phasePlan[currentPhaseIndex()];
  const output = [
    `本周总评：当前阶段是「${currentPhase.name}」，主线继续围绕 ${weakest ? weakest.subject : "基线诊断"} 推进。`,
    `阶段目标：${currentPhase.focus}`,
    "",
    `数学：${data.get("math") || "待补充"}`,
    `英语：${data.get("english") || "待补充"}`,
    `831：${data.get("economics") || "待补充"}`,
    `雅思/技术：${data.get("other") || "待补充"}`,
    "",
    "下周 3 个重点：",
    "1. 早晨固定给数学和英语，不被其他任务抢走。",
    `2. 优先修复最低掌握项：${weakest ? `${weakest.subject} · ${weakest.topic}` : "待诊断" }。`,
    "3. 每天至少沉淀一条可复测规则。",
    "",
    "停止做：只看解析、不复测、不记录错误类型。"
  ].join("\n");
  state.reviews.push({ output, createdAt: new Date().toLocaleString("zh-CN") });
  postStudyRecord({
    kind: "weekly_review",
    subject: "周复盘",
    hours: 0,
    accuracy: weakest ? weakest.score : 0,
    errorType: weakest ? `${weakest.subject} · ${weakest.topic}` : "待诊断",
    note: output,
    rule: "下周至少完成 3 个优先级任务，并把错误原因写成可复测规则。",
    createdAt: new Date().toLocaleString("zh-CN")
  }).then((saved) => {
    if (saved) loadWeaknessReport();
  });
  document.getElementById("review-output").textContent = output;
  saveState();
});

const reviewHistory = document.getElementById("review-history");
if (reviewHistory) {
  reviewHistory.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-review-index]");
    if (!button) return;
    const review = state.reviews[Number(button.dataset.reviewIndex)];
    if (review) document.getElementById("review-output").textContent = review.output;
  });
}

const deepseekAsk = document.getElementById("deepseek-ask");
if (deepseekAsk) {
  deepseekAsk.addEventListener("click", askDeepSeek);
}

document.getElementById("export-json").addEventListener("click", renderExport);

function buildCodexPrompt() {
  const weakest = [...state.mastery].sort((a, b) => a.score - b.score).slice(0, 5);
  return [
    "用 ExamPilot 分析我的学习数据，并给出下一步学习建议。",
    "",
    "学习文件：",
    JSON.stringify(state.materials.map(({ title, subject, stage, tags, summary }) => ({ title, subject, stage, tags, summary })), null, 2),
    "",
    "最近错题/诊断：",
    JSON.stringify(state.records.slice(-10), null, 2),
    "",
    "薄弱知识点：",
    JSON.stringify(weakest, null, 2),
    "",
    "请输出：1. 当前阶段判断 2. 三个最高优先级知识点 3. 下周计划 4. 需要生成的题目类型。"
  ].join("\n");
}

document.getElementById("copy-codex-prompt").addEventListener("click", async () => {
  const prompt = buildCodexPrompt();
  await navigator.clipboard.writeText(prompt);
  document.getElementById("data-output").value = prompt;
});

document.getElementById("ai-analyze").addEventListener("click", async () => {
  const output = document.getElementById("data-output");
  output.value = "正在调用本地 AI 分析接口...";
  try {
    const response = await fetch("/api/ai/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: buildCodexPrompt(), state })
    });
    const payload = await response.json();
    if (!response.ok) {
      output.value = payload.message || payload.error || "AI 接口暂不可用。";
      return;
    }
    output.value = payload.analysis || JSON.stringify(payload, null, 2);
  } catch (error) {
    output.value = "AI 接口调用失败：请确认后端已启动。";
  }
});

document.getElementById("clear-data").addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY);
  resetDemo();
});

const materialSearchButton = document.getElementById("material-search-button");
if (materialSearchButton) {
  materialSearchButton.addEventListener("click", async () => {
    const input = document.getElementById("material-search-input");
    const query = input ? input.value.trim() : "";
    const results = document.getElementById("material-search-results");
    if (results) results.innerHTML = `<div class="empty-state">正在检索本地资料库...</div>`;
    try {
      await searchMaterials(query);
    } catch (error) {
      if (results) results.innerHTML = `<div class="empty-state">检索 API 暂不可用，请确认 python server.py 正在运行。</div>`;
    }
  });
}

const materialSearchInput = document.getElementById("material-search-input");
if (materialSearchInput) {
  materialSearchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      materialSearchButton?.click();
    }
  });
}

const materialSearchResults = document.getElementById("material-search-results");
if (materialSearchResults) {
  materialSearchResults.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-material-id]");
    if (!button) return;
    const detail = document.getElementById("material-detail");
    if (detail) detail.innerHTML = `<div class="empty-state">正在打开资料证据...</div>`;
    try {
      await loadMaterialDetail(button.dataset.materialId);
    } catch (error) {
      if (detail) detail.innerHTML = `<div class="empty-state">资料详情暂不可用。</div>`;
    }
  });
}

const econGenerate = document.getElementById("econ-generate");
if (econGenerate) {
  econGenerate.addEventListener("click", generateEconomicsCards);
}

const econSync = document.getElementById("econ-sync");
if (econSync) {
  econSync.addEventListener("click", syncEconomicsCards);
}

const econCardList = document.getElementById("econ-card-list");
if (econCardList) {
  econCardList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-econ-remove]");
    if (!button) return;
    economicsCards.splice(Number(button.dataset.econRemove), 1);
    renderEconomicsCards();
  });
}

const speakingPart = document.getElementById("speaking-part");
if (speakingPart) {
  speakingPart.addEventListener("change", () => pickSpeakingQuestion(speakingPart.value));
}

const speakingNewQuestion = document.getElementById("speaking-new-question");
if (speakingNewQuestion) {
  speakingNewQuestion.addEventListener("click", () => pickSpeakingQuestion(document.getElementById("speaking-part").value));
}

const recordStart = document.getElementById("record-start");
if (recordStart) {
  recordStart.addEventListener("click", async () => {
    try {
      await startSpeakingRecording();
    } catch (error) {
      document.getElementById("recording-status").innerHTML = `<strong>麦克风不可用</strong><span>请允许浏览器麦克风权限，或先手动输入转写文本。</span>`;
      document.getElementById("record-start").disabled = false;
      document.getElementById("record-stop").disabled = true;
    }
  });
}

const recordStop = document.getElementById("record-stop");
if (recordStop) {
  recordStop.addEventListener("click", stopSpeakingRecording);
}

const speechRecognize = document.getElementById("speech-recognize");
if (speechRecognize) {
  speechRecognize.addEventListener("click", () => {
    if (speakingRecognitionActive) {
      stopSpeechRecognition();
    } else {
      startSpeechRecognition();
    }
  });
}

const speakingSubmit = document.getElementById("speaking-submit");
if (speakingSubmit) {
  speakingSubmit.addEventListener("click", submitSpeakingAnalysis);
}

const speakingSaveMemory = document.getElementById("speaking-save-memory");
if (speakingSaveMemory) {
  speakingSaveMemory.addEventListener("click", saveSpeakingAsRecord);
}

const taskForm = document.getElementById("task-form");
if (taskForm) {
  taskForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const task = {
      title: data.get("title"),
      lane: data.get("lane"),
      priority: data.get("priority"),
      status: "todo",
      detail: "手动添加",
      owner: "郭兆杰"
    };
    await saveAgentTask(task);
    event.currentTarget.reset();
  });
}

const taskBoard = document.getElementById("task-board");
if (taskBoard) {
  taskBoard.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-task-id]");
    if (!button) return;
    const task = agentTasks.find((item) => item.id === button.dataset.taskId);
    if (!task) return;
    await saveAgentTask({ ...task, status: button.dataset.taskStatus });
  });
}

const memoryForm = document.getElementById("memory-form");
if (memoryForm) {
  memoryForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const text = String(data.get("text") || "").trim();
    if (!text) return;
    await saveMemoryObservation({
      kind: "study_observation",
      subject: data.get("subject") || "通用学习",
      text,
      source: "ExamPilot Web",
      createdAt: new Date().toLocaleString("zh-CN")
    });
    event.currentTarget.reset();
  });
}

const voiceDictateButton = document.getElementById("voice-dictate");
if (voiceDictateButton) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceDictateButton.textContent = "浏览器不支持语音";
    voiceDictateButton.disabled = true;
  } else {
    voiceDictateButton.addEventListener("click", () => {
      const recognition = new SpeechRecognition();
      recognition.lang = "zh-CN";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      voiceDictateButton.textContent = "正在听...";
      voiceDictateButton.disabled = true;
      recognition.onresult = (event) => {
        const text = event.results?.[0]?.[0]?.transcript || "";
        const textarea = document.getElementById("memory-text");
        if (textarea && text) {
          textarea.value = `${textarea.value ? `${textarea.value}\n` : ""}${text}`;
        }
      };
      recognition.onerror = () => {
        voiceDictateButton.textContent = "语音失败";
      };
      recognition.onend = () => {
        setTimeout(() => {
          voiceDictateButton.textContent = "语音录入";
          voiceDictateButton.disabled = false;
        }, 500);
      };
      recognition.start();
    });
  }
}

render();
loadBackendRecords();
loadWeaknessReport();
loadMonitoringReport();
searchMaterials("831 软微 真题").catch(() => {});
loadAgentTasks();
loadMemoryObservations();
