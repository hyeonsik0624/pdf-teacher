const transcriptLibrary = window.transcriptLibrary;

const transcriptDefaults = {
  eyebrow: "TXT 전사 기반 정리본",
  overviewTitle: "강의 흐름과 전사문 찾기",
  lecturesTitle: "차시별 정리된 전사문",
  filterPlaceholder: "예: 주체사상, 평양, GIS",
};

const transcriptCourseTabsRoot = document.querySelector("#transcript-course-tabs");
const transcriptEyebrow = document.querySelector("#transcript-eyebrow");
const transcriptTitle = document.querySelector("#transcript-title");
const transcriptSummary = document.querySelector("#transcript-summary");
const conceptSiteLink = document.querySelector("#concept-site-link");
const transcriptStatsRoot = document.querySelector("#transcript-stats");
const transcriptReadingGuideRoot = document.querySelector("#transcript-reading-guide");
const transcriptOverviewRoot = document.querySelector("#transcript-overview");
const transcriptLectureNavRoot = document.querySelector("#transcript-lecture-nav");
const transcriptLectureListRoot = document.querySelector("#transcript-lecture-list");
const transcriptSourceNote = document.querySelector("#transcript-source-note");
const transcriptFilter = document.querySelector("#transcript-filter");

if (!transcriptLibrary?.courses?.length) {
  transcriptTitle.textContent = "전사문 데이터가 없습니다.";
  transcriptSummary.textContent = "transcript-data.js 생성이 필요합니다.";
  throw new Error("No transcript data available.");
}

const transcriptCourses = transcriptLibrary.courseOrder
  ? transcriptLibrary.courseOrder
      .map((courseId) => transcriptLibrary.courses.find((course) => course.id === courseId))
      .filter(Boolean)
  : transcriptLibrary.courses;

const transcriptParams = new URLSearchParams(window.location.search);
const selectedTranscriptCourseId = transcriptParams.get("course");
const selectedTranscriptCourse =
  transcriptCourses.find((course) => course.id === selectedTranscriptCourseId) ?? transcriptCourses[0];

function escapeHtml(value) {
  return `${value ?? ""}`
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatNumber(value) {
  if (!Number.isFinite(value)) {
    return `${value ?? ""}`;
  }
  return value.toLocaleString("ko-KR");
}

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

function buildPageHref(fileName, courseId) {
  const next = new URL(fileName, window.location.href);
  next.searchParams.set("course", courseId);
  next.hash = "";
  return `${next.pathname}?${next.searchParams.toString()}`;
}

function renderCourseTabs(courseList, activeId) {
  transcriptCourseTabsRoot.innerHTML = courseList
    .map((course) => {
      const label = course.meta?.courseLabel ?? course.meta?.title ?? course.id;
      const lectureCount = course.meta?.transcriptLectureCount ?? course.lectures.length;
      return `
        <a class="course-tab ${course.id === activeId ? "is-active" : ""}" href="${buildPageHref("transcript.html", course.id)}">
          <span>${label}</span>
          <small>${formatNumber(lectureCount)}개 전사</small>
        </a>
      `;
    })
    .join("");
}

function lectureMatches(lecture, query) {
  if (!query) {
    return true;
  }

  const combined = [
    lecture.title,
    lecture.theme,
    lecture.summary,
    ...(lecture.narrative ?? []),
    ...(lecture.basics ?? []).flatMap((item) => [item.title, item.body]),
    ...(lecture.topicTitles ?? []),
    ...(lecture.transcriptBlocks ?? []).map((item) => item.text),
  ]
    .join(" ")
    .toLowerCase();

  return combined.includes(query);
}

function renderOverviewCards(lectures) {
  if (!lectures.length) {
    transcriptOverviewRoot.innerHTML = `
      <div class="empty-state">
        일치하는 전사문이 없습니다. 다른 키워드로 다시 찾아보세요.
      </div>
    `;
    return;
  }

  transcriptOverviewRoot.innerHTML = lectures
    .map(
      (lecture) => `
        <article class="sub-card transcript-overview-card">
          <div class="lecture-meta">
            <span class="type-pill">${lecture.badge}</span>
            <span class="theme-pill">${lecture.theme}</span>
          </div>
          <h3>${lecture.title}</h3>
          <p>${lecture.summary}</p>
          <div class="topic-strip">
            ${(lecture.topicTitles ?? [])
              .slice(0, 5)
              .map((topic) => `<span class="topic-chip">${topic}</span>`)
              .join("")}
          </div>
          <a class="transcript-jump" href="#${lecture.id}">이 차시 전사 보기</a>
        </article>
      `
    )
    .join("");
}

function renderLectureNav(lectures) {
  transcriptLectureNavRoot.innerHTML = lectures
    .map(
      (lecture) => `
        <a class="lecture-link" href="#${lecture.id}">
          <span>${lecture.badge}</span>
          <span>${lecture.title}</span>
        </a>
      `
    )
    .join("");
}

function renderTranscriptBlocks(lecture, query) {
  const normalizedQuery = query.trim().toLowerCase();
  const matchedBlocks = normalizedQuery
    ? lecture.transcriptBlocks.filter((block) => block.text.toLowerCase().includes(normalizedQuery))
    : lecture.transcriptBlocks;
  const blocksToRender = matchedBlocks.length ? matchedBlocks : lecture.transcriptBlocks;

  return `
    <div class="transcript-blocks">
      ${blocksToRender
        .map(
          (block) => `
            <article class="transcript-block">
              <div class="transcript-block-header">
                <span class="label">정리 ${block.index}</span>
                <h4 class="transcript-block-title">${escapeHtml(block.title ?? `정리 ${block.index}`)}</h4>
              </div>
              <div class="transcript-block-copy">
                ${(block.paragraphs?.length ? block.paragraphs : [block.text])
                  .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
                  .join("")}
              </div>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderLectureList(lectures, query) {
  if (!lectures.length) {
    transcriptLectureListRoot.innerHTML = `
      <div class="empty-state">
        일치하는 전사문이 없습니다. 다른 키워드로 다시 찾아보세요.
      </div>
    `;
    return;
  }

  transcriptLectureListRoot.innerHTML = lectures
    .map(
      (lecture) => `
        <article class="lecture transcript-lecture" id="${lecture.id}">
          <header class="lecture-header">
            <div>
              <h3>${lecture.title}</h3>
              <p>${lecture.summary}</p>
            </div>
            <div class="lecture-meta">
              <span class="type-pill">${lecture.badge}</span>
              <span class="source-pill">${lecture.sourceDisplay} · ${lecture.sourceMetricLabel}</span>
              <span class="theme-pill">${lecture.theme}</span>
            </div>
          </header>
          <div class="lecture-copy">
            <section>
              <div class="section-head">
                <div>
                  <p class="mini-label">Primer</p>
                  <h3>먼저 알고 읽기</h3>
                </div>
              </div>
              <div class="concept-grid">
                ${(lecture.basics ?? [])
                  .map(
                    (item) => `
                      <article class="concept-card primer-card">
                        <h4>${item.title}</h4>
                        <p>${item.body}</p>
                      </article>
                    `
                  )
                  .join("")}
              </div>
            </section>
            <section class="transcript-outline">
              <div class="section-head">
                <div>
                  <p class="mini-label">Outline</p>
                  <h3>강의 흐름 미리보기</h3>
                </div>
              </div>
              <div class="transcript-outline-copy">
                ${(lecture.narrative ?? []).map((paragraph) => `<p>${paragraph}</p>`).join("")}
              </div>
            </section>
            <section>
              <div class="section-head split-space">
                <div>
                  <p class="mini-label">Transcript Blocks</p>
                  <h3>정리된 전사문</h3>
                </div>
                <span class="source-pill">${formatNumber(lecture.transcriptTextLength)}자</span>
              </div>
              ${renderTranscriptBlocks(lecture, query)}
            </section>
          </div>
        </article>
      `
    )
    .join("");
}

function renderTranscriptCourse(course, query = "") {
  transcriptEyebrow.textContent = transcriptDefaults.eyebrow;
  const transcriptPageTitle = course.meta.courseLabel
    ? `${course.meta.courseLabel} 정리된 전사문`
    : `${course.meta.title} 정리된 전사문`;
  transcriptTitle.textContent = transcriptPageTitle;
  transcriptSummary.innerHTML = course.meta.summary;
  conceptSiteLink.href = buildPageHref("index.html", course.id);
  transcriptFilter.placeholder = transcriptDefaults.filterPlaceholder;
  document.title = `${transcriptPageTitle} | 전사문 사이트`;

  const filteredLectures = course.lectures.filter((lecture) => lectureMatches(lecture, query.trim().toLowerCase()));

  transcriptStatsRoot.innerHTML = [
    { value: formatNumber(course.meta.transcriptLectureCount), label: "전사 강의" },
    { value: formatNumber(course.meta.transcriptBlockCount), label: "정리 블록" },
    { value: formatNumber(course.meta.transcriptCharacterCount), label: "총 글자 수" },
    { value: formatNumber(filteredLectures.length), label: "현재 표시" },
  ]
    .map(
      (item) => `
        <article class="stat-card">
          <strong>${item.value}</strong>
          <span>${item.label}</span>
        </article>
      `
    )
    .join("");

  transcriptReadingGuideRoot.innerHTML = [
    "먼저 각 차시의 `강의 흐름 미리보기`를 읽고 전체 맥락을 잡습니다.",
    "이해가 막히는 용어는 `먼저 알고 읽기` 카드에서 바로 확인합니다.",
    "키워드 검색으로 특정 개념이나 지역이 나오는 차시를 빠르게 찾을 수 있습니다.",
    "필요하면 `개념 교재로 보기`로 넘어가서 같은 차시의 개념 해설과 함께 읽으면 됩니다.",
  ]
    .map((item) => `<li>${item}</li>`)
    .join("");

  renderOverviewCards(filteredLectures);
  renderLectureNav(filteredLectures);
  renderLectureList(filteredLectures, query);

  const generatedAtLabel = formatDateLabel(course.meta.generatedAt);
  transcriptSourceNote.innerHTML = `총 ${formatNumber(course.meta.transcriptLectureCount)}개 강의 전사, 정리 블록 ${formatNumber(course.meta.transcriptBlockCount)}개로 재구성함${
    generatedAtLabel ? ` · 데이터 생성: <code>${generatedAtLabel}</code>` : ""
  }`;
}

transcriptFilter.addEventListener("input", (event) => {
  renderTranscriptCourse(selectedTranscriptCourse, event.target.value);
});

renderCourseTabs(transcriptCourses, selectedTranscriptCourse.id);
renderTranscriptCourse(selectedTranscriptCourse);
