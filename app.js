const library =
  window.studyLibrary ??
  (window.courseData ? { generatedAt: null, courseOrder: ["default"], courses: [{ id: "default", ...window.courseData }] } : null);

const DEFAULT_LABELS = {
  courseEyebrow: "PDF 기반 시험 강의 노트",
  quickGuideLabel: "Quick Guide",
  quickGuideTitle: "핵심 생존 가이드",
  atlasLabel: "Exam Atlas",
  atlasTitle: "시험 아틀라스",
  atlasFilterPlaceholder: "예: 핵심어, 이론, 명령어",
  drillLabel: "Drills",
  drillTitle: "실전 대비 문제 루틴",
  lectureDetailMiniLabel: "Key Cards",
  lectureDetailTitle: "시험용 핵심 카드",
  lectureSyntaxLabel: "답안 틀",
  lectureExampleLabel: "예시",
  lectureDetailEmpty: "아직 이 강의의 시험용 핵심 카드가 작성되지 않았습니다.",
  statsLectureCards: "핵심 카드",
  statsAtlasItems: "아틀라스 항목",
};

const lectureTypeLabels = {
  core: "Core",
  practice: "Practice",
  pending: "Pending",
};

const lectureStatusLabels = {
  draft: "Draft",
  "missing-source": "Source Missing",
};

const heroEyebrow = document.querySelector("#hero-eyebrow");
const courseTabsRoot = document.querySelector("#course-tabs");
const heroTitle = document.querySelector("#hero-title");
const heroSummary = document.querySelector("#hero-summary");
const statsRoot = document.querySelector("#stats");
const memoryRoot = document.querySelector("#memory-lines");
const examMapRoot = document.querySelector("#exam-map");
const cramPlanRoot = document.querySelector("#cram-plan");
const vimGroupsRoot = document.querySelector("#vim-groups");
const lectureNavRoot = document.querySelector("#lecture-nav");
const lectureListRoot = document.querySelector("#lecture-list");
const atlasGroupsRoot = document.querySelector("#atlas-groups");
const studyDrillsRoot = document.querySelector("#study-drills");
const sourceNote = document.querySelector("#source-note");
const commandFilter = document.querySelector("#command-filter");
const quickGuideLabel = document.querySelector("#quick-guide-label");
const quickGuideTitle = document.querySelector("#quick-guide-title");
const atlasLabel = document.querySelector("#atlas-label");
const atlasTitle = document.querySelector("#atlas-title");
const drillLabel = document.querySelector("#drill-label");
const drillTitle = document.querySelector("#drill-title");

if (!library?.courses?.length) {
  heroTitle.textContent = "과목 데이터가 없습니다.";
  heroSummary.textContent = "study-data.js 생성이 필요합니다.";
  throw new Error("No course data available.");
}

const courses = library.courseOrder
  ? library.courseOrder.map((courseId) => library.courses.find((course) => course.id === courseId)).filter(Boolean)
  : library.courses;

const params = new URLSearchParams(window.location.search);
const selectedCourseId = params.get("course");
const selectedCourse = courses.find((course) => course.id === selectedCourseId) ?? courses[0];

function formatDateLabel(isoString) {
  if (!isoString) {
    return null;
  }

  return new Date(isoString).toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getCourseLabels(meta) {
  return { ...DEFAULT_LABELS, ...meta };
}

function buildCourseHref(courseId) {
  const next = new URL(window.location.href);
  next.searchParams.set("course", courseId);
  next.hash = "";
  return `${next.pathname}?${next.searchParams.toString()}`;
}

function renderCourseTabs(courseList, activeId) {
  courseTabsRoot.innerHTML = courseList
    .map((course) => {
      const count = course.meta?.sources?.length ?? 0;
      const label = course.meta?.courseLabel ?? course.meta?.title ?? course.id;
      return `
        <a class="course-tab ${course.id === activeId ? "is-active" : ""}" href="${buildCourseHref(course.id)}">
          <span>${label}</span>
          <small>${count} PDFs</small>
        </a>
      `;
    })
    .join("");
}

function renderEmptySection(message) {
  return `<div class="empty-state">${message}</div>`;
}

function renderConceptSection(lecture) {
  if (!lecture.concepts?.length) {
    return `
      <section>
        <div class="section-head">
          <div>
            <p class="mini-label">Concepts</p>
            <h3>이 강의에서 꼭 붙잡아야 할 개념</h3>
          </div>
        </div>
        ${renderEmptySection("아직 이 강의의 핵심 개념 카드가 작성되지 않았습니다.")}
      </section>
    `;
  }

  return `
    <section>
      <div class="section-head">
        <div>
          <p class="mini-label">Concepts</p>
          <h3>이 강의에서 꼭 붙잡아야 할 개념</h3>
        </div>
      </div>
      <div class="concept-grid">
        ${lecture.concepts
          .map(
            (concept) => `
              <article class="concept-card">
                <h4>${concept.title}</h4>
                <p>${concept.body}</p>
              </article>
            `
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderDetailSection(lecture, labels) {
  if (!lecture.commands?.length) {
    return `
      <section>
        <div class="section-head">
          <div>
            <p class="mini-label">${labels.lectureDetailMiniLabel}</p>
            <h3>${labels.lectureDetailTitle}</h3>
          </div>
        </div>
        ${renderEmptySection(labels.lectureDetailEmpty)}
      </section>
    `;
  }

  return `
    <section>
      <div class="section-head">
        <div>
          <p class="mini-label">${labels.lectureDetailMiniLabel}</p>
          <h3>${labels.lectureDetailTitle}</h3>
        </div>
      </div>
      <div class="command-grid">
        ${lecture.commands
          .map(
            (command) => `
              <article class="command-card">
                <span class="label">${command.name}</span>
                <h4>핵심 의미</h4>
                <p>${command.idea}</p>
                <h4>${labels.lectureSyntaxLabel}</h4>
                <pre><code>${command.syntax}</code></pre>
                <h4>${labels.lectureExampleLabel}</h4>
                <pre><code>${command.example}</code></pre>
                <h4>시험 함정</h4>
                <p>${command.pitfall}</p>
              </article>
            `
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderQuizItems(lecture) {
  if (!lecture.quiz?.length) {
    return `<div class="empty-state">아직 자가 점검 질문이 준비되지 않았습니다.</div>`;
  }

  return `
    <div class="quiz">
      ${lecture.quiz
        .map(
          (item) => `
            <details>
              <summary>${item.q}</summary>
              <p>${item.a}</p>
            </details>
          `
        )
        .join("")}
    </div>
  `;
}

function renderAtlas(groups, filterText = "") {
  const query = filterText.trim().toLowerCase();
  const filteredGroups = groups
    .map((group) => {
      const items = group.items.filter((item) => {
        if (!query) {
          return true;
        }

        return [group.title, item.name, item.use, item.compare, item.example]
          .join(" ")
          .toLowerCase()
          .includes(query);
      });

      return { ...group, items };
    })
    .filter((group) => group.items.length > 0);

  if (filteredGroups.length === 0) {
    atlasGroupsRoot.innerHTML = `
      <div class="empty-state">
        일치하는 아틀라스 항목이 없습니다. 다른 키워드로 다시 검색해 보세요.
      </div>
    `;
    return;
  }

  atlasGroupsRoot.innerHTML = filteredGroups
    .map(
      (group) => `
        <article class="atlas-card">
          <div>
            <h4>${group.title}</h4>
            <p class="atlas-meta">${group.items.length}개 항목</p>
          </div>
          <ul>
            ${group.items
              .map(
                (item) => `
                  <li>
                    <strong>${item.name}</strong><br />
                    ${item.use}<br />
                    비교: ${item.compare}<br />
                    예시: <code>${item.example}</code>
                  </li>
                `
              )
              .join("")}
          </ul>
        </article>
      `
    )
    .join("");
}

function renderCourse(course) {
  const labels = getCourseLabels(course.meta);
  const totalPages = course.meta.sources.reduce((sum, source) => sum + source.pages, 0);
  const totalLectureCards = course.lectures.reduce((sum, lecture) => sum + lecture.commands.length, 0);
  const totalAtlasItems = course.commandAtlas.reduce((sum, group) => sum + group.items.length, 0);
  const draftLectureCount = course.lectures.filter((lecture) => lecture.status === "draft").length;
  const generatedAtLabel = formatDateLabel(course.meta.generatedAt);

  document.title = `${course.meta.title} | PDF 시험 강의 노트`;
  heroEyebrow.textContent = labels.courseEyebrow;
  heroTitle.textContent = course.meta.title;
  heroSummary.innerHTML = course.meta.summary;
  quickGuideLabel.textContent = labels.quickGuideLabel;
  quickGuideTitle.textContent = labels.quickGuideTitle;
  atlasLabel.textContent = labels.atlasLabel;
  atlasTitle.textContent = labels.atlasTitle;
  drillLabel.textContent = labels.drillLabel;
  drillTitle.textContent = labels.drillTitle;
  commandFilter.placeholder = labels.atlasFilterPlaceholder;

  const stats = [
    { value: `${course.meta.sources.length}`, label: "PDF 묶음" },
    { value: `${totalPages}`, label: "총 페이지" },
    { value: `${course.lectures.length}`, label: "학습 섹션" },
    { value: `${totalLectureCards}`, label: labels.statsLectureCards },
    { value: `${totalAtlasItems}`, label: labels.statsAtlasItems },
  ];

  if (draftLectureCount > 0) {
    stats.splice(3, 0, { value: `${draftLectureCount}`, label: "해설 대기" });
  }

  statsRoot.innerHTML = stats
    .map(
      (stat) => `
        <article class="stat-card">
          <strong>${stat.value}</strong>
          <span>${stat.label}</span>
        </article>
      `
    )
    .join("");

  memoryRoot.innerHTML = course.fastRecall.map((item) => `<li>${item}</li>`).join("");

  examMapRoot.innerHTML = course.examMap
    .map(
      (item) => `
        <article class="sub-card">
          <h3>${item.title}</h3>
          <p>${item.body}</p>
        </article>
      `
    )
    .join("");

  cramPlanRoot.innerHTML = course.cramPlan
    .map(
      (item) => `
        <article class="timeline-card">
          <span class="time-pill">${item.time}</span>
          <h3>${item.title}</h3>
          <p>${item.body}</p>
        </article>
      `
    )
    .join("");

  vimGroupsRoot.innerHTML = course.vimCheat
    .map(
      (group) => `
        <article class="vim-card">
          <h3>${group.title}</h3>
          <ul>
            ${group.bullets.map((bullet) => `<li>${bullet}</li>`).join("")}
          </ul>
        </article>
      `
    )
    .join("");

  lectureNavRoot.innerHTML = course.lectures
    .map(
      (lecture) => `
        <a class="lecture-link ${lecture.status === "draft" ? "is-draft" : ""}" href="#${lecture.id}">
          <span>${lecture.badge}</span>
          <span>${lecture.title}</span>
        </a>
      `
    )
    .join("");

  lectureListRoot.innerHTML = course.lectures
    .map((lecture) => {
      const typeLabel = lectureTypeLabels[lecture.type] ?? "Lecture";
      const statusLabel = lectureStatusLabels[lecture.status];

      return `
        <article class="lecture ${lecture.status === "draft" ? "is-draft" : ""}" id="${lecture.id}">
          <header class="lecture-header">
            <div>
              <h3>${lecture.title}</h3>
              <p>${lecture.summary}</p>
            </div>
            <div class="lecture-meta">
              <span class="type-pill">${typeLabel}</span>
              ${statusLabel ? `<span class="status-pill">${statusLabel}</span>` : ""}
              <span class="source-pill">${lecture.source} · ${lecture.pages}p</span>
              <span class="theme-pill">${lecture.theme}</span>
            </div>
          </header>
          <div class="lecture-layout">
            <div class="lecture-copy">
              ${lecture.narrative.map((paragraph) => `<p>${paragraph}</p>`).join("")}
              ${renderConceptSection(lecture)}
              ${renderDetailSection(lecture, labels)}
            </div>
            <aside class="aside-stack">
              <section class="pitfall-box">
                <h4>헷갈리기 쉬운 포인트</h4>
                <ul class="pitfall-list">
                  ${lecture.pitfalls.map((item) => `<li>${item}</li>`).join("")}
                </ul>
              </section>
              <section class="checklist-box">
                <h4>복습 체크리스트</h4>
                <ul class="checklist">
                  ${lecture.checklist.map((item) => `<li>${item}</li>`).join("")}
                </ul>
              </section>
              <section class="quiz-box">
                <h4>자가 점검 질문</h4>
                ${renderQuizItems(lecture)}
              </section>
            </aside>
          </div>
        </article>
      `;
    })
    .join("");

  studyDrillsRoot.innerHTML = course.studyDrills
    .map(
      (drill) => `
        <article class="drill-card">
          <h3>${drill.title}</h3>
          <p>${drill.body}</p>
          <ul>
            ${drill.bullets.map((bullet) => `<li>${bullet}</li>`).join("")}
          </ul>
        </article>
      `
    )
    .join("");

  sourceNote.innerHTML = `총 ${course.meta.sources.length}개 PDF, ${totalPages}페이지를 바탕으로 재구성함.${generatedAtLabel ? ` · 데이터 생성: <code>${generatedAtLabel}</code>` : ""}`;

  renderAtlas(course.commandAtlas, commandFilter.value);
}

commandFilter.addEventListener("input", (event) => {
  renderAtlas(selectedCourse.commandAtlas, event.target.value);
});

renderCourseTabs(courses, selectedCourse.id);
renderCourse(selectedCourse);
