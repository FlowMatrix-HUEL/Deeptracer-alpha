// DeepTracer - Modernized Multi-Page Architecture
const themes = ["mist", "paper", "night"];
const loadingCopies = [
    "像素猫正在巡检结构、性能和内存，请稍等一下。",
    "正在梳理函数之间的关系，马上给你结果。",
    "热点和内存摘要还在整理中，很快就好。",
    "正在生成更容易理解的修改建议。"
];

const sampleCode = `LEARNER_RECORDS = [
    {"name": "Ada", "topic": "syntax", "correct": 8, "total": 10},
    {"name": "Ada", "topic": "algorithm", "correct": 6, "total": 10},
    {"name": "Ada", "topic": "data", "correct": 9, "total": 10},
    {"name": "Lin", "topic": "syntax", "correct": 7, "total": 10},
    {"name": "Lin", "topic": "algorithm", "correct": 5, "total": 10},
    {"name": "Lin", "topic": "data", "correct": 8, "total": 10},
]

TOPIC_WEIGHTS = {"syntax": 1.0, "algorithm": 1.3, "data": 1.1}


def clamp_score(
    score: float,
    /,
    *,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    return min(maximum, max(minimum, score))


def attempt_score(
    correct: int,
    total: int,
    *,
    penalty: float = 0.0,
) -> float:
    if total <= 0:
        return 0.0
    raw_score = correct / total * 100 - penalty
    return clamp_score(round(raw_score, 1))


def recursive_match_count(
    scores: list[float],
    target: float,
    index: int = 0,
) -> int:
    if index >= len(scores):
        return 0
    matched = 1 if scores[index] >= target else 0
    return matched + recursive_match_count(scores, target, index + 1)


def topic_average(records: list[dict[str, object]], topic: str) -> float:
    scores = []
    for record in records:
        if record["topic"] != topic:
            continue
        scores.append(attempt_score(record["correct"], record["total"]))
    return round(sum(scores) / len(scores), 1) if scores else 0.0


def weighted_total(
    topic_scores: dict[str, float],
    *,
    default_weight: float = 1.0,
    **overrides: float,
) -> float:
    weighted_sum = 0.0
    weight_sum = 0.0
    for topic, score in topic_scores.items():
        weight = overrides.get(topic, TOPIC_WEIGHTS.get(topic, default_weight))
        weighted_sum += score * weight
        weight_sum += weight
    return round(weighted_sum / weight_sum, 1) if weight_sum else 0.0


def build_learning_summary(records: list[dict[str, object]]) -> dict[str, object]:
    topics = sorted({record["topic"] for record in records})
    topic_scores = {
        topic: topic_average(records, topic)
        for topic in topics
    }
    weighted_score = weighted_total(topic_scores)
    strong_topics = recursive_match_count(list(topic_scores.values()), 70)
    return {
        "topic_scores": topic_scores,
        "weighted_score": weighted_score,
        "strong_topics": strong_topics,
    }


def choose_next_action(summary: dict[str, object]) -> str:
    scores = summary["topic_scores"]
    weakest_topic = min(scores, key=scores.get)
    if summary["strong_topics"] >= 2:
        return f"继续巩固 {weakest_topic}"
    return f"优先复习 {weakest_topic}"


def main() -> None:
    summary = build_learning_summary(LEARNER_RECORDS)
    next_action = choose_next_action(summary)
    print("learner summary:", summary)
    print("next action:", next_action)


if __name__ == "__main__":
    main()
`;

const demoData = {
    heroMetrics: [
        { label: "分析对象", value: "示例代码", note: "可以直接替换成你自己的代码" },
        { label: "代码行数", value: "101", note: "输入框里的内容会参与分析" },
        { label: "重点函数", value: "build_learning_summary", note: "按结构复杂度排序" },
        { label: "分析环境", value: "Python 3.11", note: "执行可视化会自动切到兼容模式" }
    ],
    analysisMap: {
        workflow: {
            title: "概览",
            summary: "先看整体，再决定要不要继续往下看。",
            cards: [
                { label: "结构复杂度", value: "61", note: "分支和函数拆分处于中等复杂度" },
                { label: "热点集中度", value: "73", note: "耗时主要集中在少数关键函数" },
                { label: "内存压力", value: "24", note: "当前内存压力不高" },
                { label: "修改空间", value: "68", note: "有几处很适合先做的小重构" }
            ],
            points: [
                "代码结构清晰，函数职责单一。",
                "循环和条件分支处于合理范围。",
                "可以继续查看性能和内存细节。"
            ]
        },
        ast: {
            title: "结构",
            summary: "AST 语法树分析结果。",
            cards: [
                { label: "函数数量", value: "8", note: "包含递归与参数演示" },
                { label: "print 调用", value: "2", note: "2 次 print 调用" },
                { label: "循环数量", value: "4", note: "4 个循环结构" },
                { label: "条件分支", value: "4", note: "4 个 if 条件判断" }
            ],
            points: [
                "函数定义清晰，命名语义化。",
                "控制流结构简单易懂。",
                "没有复杂的嵌套结构。"
            ]
        },
        performance: {
            title: "性能",
            summary: "性能分析结果。",
            cards: [
                { label: "总耗时", value: "0.42 ms", note: "本地执行总耗时" },
                { label: "热点函数", value: "recursive_match_count", note: "递归调用形成明显热点" },
                { label: "循环次数", value: "12", note: "总共执行 12 次循环" },
                { label: "优化空间", value: "中等", note: "有优化可能" }
            ],
            points: [
                "整体性能表现良好。",
                "recursive_match_count 会形成可观察的递归调用链。",
                "可以考虑缓存中间结果。"
            ]
        },
        memory: {
            title: "内存",
            summary: "内存使用分析。",
            cards: [
                { label: "峰值内存", value: "1.2 MB", note: "执行过程峰值" },
                { label: "对象分配", value: "42", note: "共分配 42 个对象" },
                { label: "内存压力", value: "低", note: "内存使用合理" },
                { label: "优化建议", value: "无需优化", note: "当前内存使用良好" }
            ],
            points: [
                "内存使用效率高。",
                "没有明显的内存泄漏风险。",
                "对象复用合理。"
            ]
        }
    },
    suggestions: [
        {
            id: "replace-recursive-count",
            title: "将递归匹配改为迭代",
            explanation: "recursive_match_count 的递归调用清楚但会增加调用层级，数据量变大时可以改为迭代。",
            priority: "高",
            confidence: "中",
            risk: "低",
            file: "当前代码",
            note: "迭代写法更稳定，也更容易在调用追踪中观察。",
            diff: [
                [1, " ", "def recursive_match_count(scores, target, index=0):"],
                [2, "-", "    return matched + recursive_match_count(...)"],
                [3, "+", "    return sum(score >= target for score in scores)"]
            ]
        },
        {
            id: "cache-topic-average",
            title: "缓存 topic_average 的中间结果",
            explanation: "build_learning_summary 会按主题重复扫描记录，可以先建立 topic 分组再计算平均值。",
            priority: "中",
            confidence: "高",
            risk: "低",
            file: "当前代码",
            note: "一次分组后复用结果，减少重复遍历。",
            diff: [
                [1, "-", "    topic_scores = {topic: topic_average(records, topic) ...}"],
                [2, "+", "    grouped = group_records_by_topic(records)"],
                [3, "+", "    topic_scores = {topic: average_scores(items) ...}"]
            ]
        }
    ],
    visualizations: {
        ast: "",
        performance: ""
    },
    meta: {
        targetPath: "示例代码",
        stdout: "summary: {...}\nfocus: {...}",
        runtimeError: null
    }
};

// 应用状态
const state = {
    theme: "mist",
    currentPage: "home",
    activeWorkspace: "analysis",
    activeTab: "workflow",
    activeSuggestion: demoData.suggestions[0].id,
    activeViz: "ast",
    loading: false,
    loadingStep: 0,
    currentFileName: "",
    currentCode: "",
    isBuiltInSample: false,
    originalCode: "", // 分析前的原始代码
    analyzedCode: "",
    sourceHash: "",
    fileId: "editor",
    activeExecutionMode: "tutor",
    traceSelectedFunctions: new Set(),
    traceActiveView: "tree",
    traceResult: null,
    terminalOutputCode: "",
    isEditing: false,
    hasUnsavedChanges: false,
    diffMode: "unified",
    currentDiff: null,
    expandedDiffRanges: new Set(),
    editHistory: [],
    patchPlans: new Map(),
    patchErrors: new Map(),
    patchBusySuggestion: "",
    verificationResult: null,
    tutorLastStep: null,
    tutorMoments: [],
    activeTutorMomentId: null,
    tutorMomentsEnabled: true,
    tutorMomentEnrichTimer: 0,
    tutorMomentEnrichRequest: 0,
    latestAnalysisTaskId: null,
    chatMessages: [],
    activeChatRequestId: 0,
    activeChatController: null
};

// DOM 元素引用
let el = {};
let isResizing = false;
let chatCodeBlockRegistry = new Map();
let tutorConnectorRedrawQueued = false;
let tutorConnectorTracking = false;
let hasManualCodeLayout = false;
const CODE_PANE_MIN_WIDTH = 620;
const FLOW_PANE_MIN_WIDTH = 960;
const RESIZE_HANDLE_WIDTH = 28;

// 深度克隆工具函数
function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

// 数据存储器
let dataStore = deepClone(demoData);
let currentTutorVisualizer = null;
let partnerDock = null;

// 初始化 DOM 元素引用
function initElements() {
    el = {
        // 导航
        navbar: document.getElementById("navbar"),
        navTabs: document.querySelectorAll(".nav-tab"),
        themeToggle: document.getElementById("themeToggle"),
        
        // 页面
        pageHome: document.getElementById("pageHome"),
        pageCode: document.getElementById("pageCode"),
        pageAnalysis: document.getElementById("pageAnalysis"),
        codeLayoutViewport: document.querySelector(".code-layout-viewport"),
        
        // HOME 页面
        selectFileBtn: document.getElementById("selectFileBtn"),
        loadSampleBtn: document.getElementById("loadSampleBtn"),
        fileInput: document.getElementById("fileInput"),
        dropZone: document.getElementById("dropZone"),
        catAnimation: document.getElementById("catAnimation"),
        terminalEntryInput: document.getElementById("terminalEntryInput"),
        terminalEntryError: document.getElementById("terminalEntryError"),
        terminalSkip: document.getElementById("terminalSkip"),
        bootOverlay: document.getElementById("bootOverlay"),
        bootTerminal: document.getElementById("bootTerminal"),
        
        // 代码页面
        sourceCode: document.getElementById("sourceCode"),
        lineNumbers: document.getElementById("lineNumbers"),
        fileName: document.getElementById("fileName"),
        lineCount: document.getElementById("lineCount"),
        editStatus: document.getElementById("editStatus"),
        clearCode: document.getElementById("clearCode"),
        reloadFile: document.getElementById("reloadFile"),
        runAnalysis: document.getElementById("runAnalysis"),
        editCode: document.getElementById("editCode"),
        saveEdit: document.getElementById("saveEdit"),
        cancelEdit: document.getElementById("cancelEdit"),
        rollbackEdit: document.getElementById("rollbackEdit"),
        copyCode: document.getElementById("copyCode"),
        diffViewer: document.getElementById("diffViewer"),
        verificationPanel: document.getElementById("verificationPanel"),
        sourceFocusStatus: document.getElementById("sourceFocusStatus"),
        syncTutor: document.getElementById("syncTutor"),
        tutorPlaceholder: document.getElementById("tutorPlaceholder"),
        tutorVisualizerMount: document.getElementById("tutorVisualizerMount"),
        pythonMomentRail: document.getElementById("pythonMomentRail"),
        pythonMomentList: document.getElementById("pythonMomentList"),
        pythonMomentCount: document.getElementById("pythonMomentCount"),
        pythonMomentSource: document.getElementById("pythonMomentSource"),
        pythonMomentNext: document.getElementById("pythonMomentNext"),
        pythonMomentToggle: document.getElementById("pythonMomentToggle"),
        tutorStage: document.querySelector(".tutor-stage"),
        executionModeTabs: document.getElementById("executionModeTabs"),
        executionViews: document.querySelectorAll("[data-execution-view]"),
        tutorExecutionView: document.getElementById("tutorExecutionView"),
        tracerExecutionView: document.getElementById("tracerExecutionView"),
        terminalExecutionView: document.getElementById("terminalExecutionView"),
        runTerminalCode: document.getElementById("runTerminalCode"),
        terminalRunStatus: document.getElementById("terminalRunStatus"),
        terminalRunDuration: document.getElementById("terminalRunDuration"),
        terminalRunOutput: document.getElementById("terminalRunOutput"),
        traceFunctionList: document.getElementById("traceFunctionList"),
        traceTime: document.getElementById("traceTime"),
        traceColor: document.getElementById("traceColor"),
        traceExceptions: document.getElementById("traceExceptions"),
        traceLocals: document.getElementById("traceLocals"),
        runTracerTrace: document.getElementById("runTracerTrace"),
        traceViewTabs: document.getElementById("traceViewTabs"),
        traceTreeView: document.getElementById("traceTreeView"),
        traceTerminalView: document.getElementById("traceTerminalView"),
        traceTerminalOutput: document.getElementById("traceTerminalOutput"),
        traceStatus: document.getElementById("traceStatus"),
        expandTraceTree: document.getElementById("expandTraceTree"),
        collapseTraceTree: document.getElementById("collapseTraceTree"),
        
        // 分析结果页面
        runtimeBanner: document.getElementById("runtimeBanner"),
        summaryCards: document.getElementById("summaryCards"),
        workspaceTabs: document.getElementById("workspaceTabs"),
        workspacePanels: document.querySelectorAll("[data-workspace-panel]"),
        backToCode: document.getElementById("backToCode"),
        openTracer: document.getElementById("openTracer"),
        resultTabs: document.getElementById("resultTabs"),
        tabSummary: document.getElementById("tabSummary"),
        tabBars: document.getElementById("tabBars"),
        tabPoints: document.getElementById("tabPoints"),
        suggestionList: document.getElementById("suggestionList"),
        suggestionDetail: document.getElementById("suggestionDetail"),
        vizTabs: document.getElementById("vizTabs"),
        astVizContent: document.getElementById("astVizContent"),
        perfVizContent: document.getElementById("perfVizContent"),
        chatStatus: document.getElementById("chatStatus"),
        chatTranscript: document.getElementById("chatTranscript"),
        chatInput: document.getElementById("chatInput"),
        chatSend: document.getElementById("chatSend"),
        chatStop: document.getElementById("chatStop"),
        
        // 加载动画
        loadingOverlay: document.getElementById("loadingOverlay"),
        loadingText: document.getElementById("loadingText"),
        
        // 拖拽元素
        codePanel: document.getElementById("codePanel"),
        flowPanel: document.getElementById("flowPanel"),
        resizeHandle: document.getElementById("resizeHandle")
    };
}

// 页面切换
function switchToPage(pageName) {
    state.currentPage = pageName;

    // 更新页面显示
    document.querySelectorAll(".page").forEach(page => {
        page.classList.remove("is-active");
    });
    
    const targetPage = document.getElementById(`page${pageName.charAt(0).toUpperCase() + pageName.slice(1)}`);
    if (targetPage) {
        targetPage.classList.add("is-active");
    }
    
    // 更新导航栏状态
    document.querySelectorAll(".nav-tab").forEach(tab => {
        tab.classList.toggle("is-active", tab.dataset.page === pageName);
    });
    
    // 显示/隐藏导航栏
    if (el.navbar) {
        el.navbar.hidden = pageName === "home";
    }
    window.scrollTo({ top: 0, behavior: "auto" });
}

function currentSourceHash() {
    return state.sourceHash || "";
}

function encodeSourceRef(sourceRef) {
    return encodeURIComponent(JSON.stringify(sourceRef || {}));
}

function decodeSourceRef(token) {
    try {
        return JSON.parse(decodeURIComponent(token || ""));
    } catch (error) {
        return null;
    }
}

function lineStartOffset(code, line) {
    const lines = code.split("\n");
    let offset = 0;
    for (let index = 0; index < Math.max(0, line - 1); index += 1) {
        offset += (lines[index] || "").length + 1;
    }
    return offset;
}

function revealSource(sourceRef, {
    switchPage = true,
    focus = true,
    reason = ""
} = {}) {
    if (!sourceRef || !sourceRef.startLine) return false;
    const activeHash = currentSourceHash();
    if (sourceRef.sourceHash && sourceRef.sourceHash !== activeHash) {
        el.editStatus.textContent = "定位信息已过期，请重新分析当前代码。";
        return false;
    }

    if (switchPage) {
        switchToPage("code");
    }
    const code = el.sourceCode.value;
    const startLine = Math.max(1, Number(sourceRef.startLine) || 1);
    const endLine = Math.max(startLine, Number(sourceRef.endLine) || startLine);
    const startOffset = lineStartOffset(code, startLine);
    const endOffset = Math.min(
        code.length,
        lineStartOffset(code, endLine) + (code.split("\n")[endLine - 1] || "").length
    );
    el.sourceCode.setSelectionRange(startOffset, endOffset);
    const computed = window.getComputedStyle(el.sourceCode);
    const lineHeight = Number.parseFloat(computed.lineHeight) || 24;
    el.sourceCode.scrollTop = Math.max(
        0,
        (startLine - 1) * lineHeight - el.sourceCode.clientHeight / 2
    );
    el.lineNumbers.scrollTop = el.sourceCode.scrollTop;
    if (focus) {
        el.sourceCode.focus({ preventScroll: true });
    }
    const originLabel = reason || sourceRef.origin || "可视化";
    el.sourceFocusStatus.textContent = `已定位：第 ${startLine} 行 · ${originLabel}`;
    return true;
}

function revealSourceFromElement(element) {
    if (!element) return;
    const sourceRef = decodeSourceRef(element.dataset.sourceRef);
    revealSource(sourceRef, {
        reason: element.dataset.sourceOrigin || sourceRef?.origin || "代码定位"
    });
}

window.addEventListener("message", (event) => {
    const astFrame = document.querySelector("#astVizContent iframe");
    if (!astFrame || event.source !== astFrame.contentWindow) return;
    if (event.data?.type !== "deeptracer:reveal-source") return;
    revealSource(event.data.sourceRef, {
        reason: "AST 节点"
    });
});

function setWorkspaceView(workspaceName) {
    const target = document.querySelector(`[data-workspace-panel="${workspaceName}"]`);
    if (!target) return;

    state.activeWorkspace = workspaceName;
    el.workspaceTabs.querySelectorAll(".workspace-tab").forEach(tab => {
        const isActive = tab.dataset.workspace === workspaceName;
        tab.classList.toggle("is-active", isActive);
        tab.setAttribute("aria-selected", String(isActive));
    });
    el.workspacePanels.forEach(panel => {
        panel.hidden = panel.dataset.workspacePanel !== workspaceName;
    });

    if (state.currentPage === "analysis") {
        const tabsTop = el.workspaceTabs.getBoundingClientRect().top + window.scrollY;
        window.scrollTo({ top: Math.max(0, tabsTop - 76), behavior: "auto" });
    }

    if (workspaceName === "chat") {
        window.requestAnimationFrame(() => {
            if (el.chatTranscript) {
                el.chatTranscript.scrollTop = el.chatTranscript.scrollHeight;
            }
        });
    }
}

function setExecutionMode(mode) {
    const target = document.querySelector(`[data-execution-view="${mode}"]`);
    if (!target) return;

    state.activeExecutionMode = mode;
    el.executionModeTabs.querySelectorAll(".execution-mode-tab").forEach(tab => {
        const isActive = tab.dataset.executionMode === mode;
        tab.classList.toggle("is-active", isActive);
        tab.setAttribute("aria-selected", String(isActive));
    });
    el.executionViews.forEach(view => {
        view.hidden = view.dataset.executionView !== mode;
    });
    el.syncTutor.hidden = mode !== "tutor";
}

function ensurePartnerDock() {
    if (partnerDock || !window.createPartnerDock) {
        return;
    }
    const mount = document.getElementById("partnerDockMount");
    if (!mount) {
        return;
    }
    partnerDock = window.createPartnerDock(mount, {
        workbench: "python",
        getContext: buildPartnerContext,
        onHighlight: revealPartnerTarget,
        onJump: revealPartnerTarget,
        onInsert: insertPartnerCode
    });
}

function buildPartnerContext() {
    const analysis = dataStore.analysisMap || {};
    const functions = Array.isArray(analysis.ast?.functions)
        ? analysis.ast.functions
              .map(item => item.qualified_name || item.name)
              .filter(Boolean)
              .slice(0, 20)
        : [];
    return {
        code: el.sourceCode?.value || "",
        displayName: currentDisplayName(),
        selection: state.tutorLastStep?.line
            ? { line: state.tutorLastStep.line }
            : {},
        analysis: {
            focusFunction: analysis.ast?.focusFunction || "",
            functions,
            performance:
                analysis.performance?.hottestFunction ||
                analysis.performance?.summary ||
                "",
            memory: analysis.memory?.summary || ""
        },
        trace: state.tutorLastStep
            ? {
                  lastStep: state.tutorLastStep.step,
                  line: state.tutorLastStep.line,
                  event: state.tutorLastStep.event || ""
              }
            : {}
    };
}

function revealPartnerTarget(target) {
    if (!target || typeof target !== "object") return;
    if (target.stepIndex !== null && target.stepIndex !== undefined) {
        jumpToTutorStep(Number(target.stepIndex));
        return;
    }
    if (target.line !== null && target.line !== undefined) {
        revealSource(
            {
                fileId: state.fileId || "editor",
                sourceHash: currentSourceHash(),
                startLine: Number(target.line),
                endLine: Number(target.line),
                origin: "partner"
            },
            {
                switchPage: false,
                focus: true,
                reason: "思辨伙伴"
            }
        );
    }
}

function insertPartnerCode(proposal) {
    const code = String(proposal?.code || "");
    if (!code.trim()) return false;
    if (el.sourceCode.readOnly) {
        enableEditMode();
    }
    const lines = el.sourceCode.value.split("\n");
    const requested = Number(proposal?.target?.line);
    const insertAt = Number.isFinite(requested) && requested > 0
        ? Math.min(lines.length, requested - 1)
        : lines.length;
    lines.splice(insertAt, 0, ...code.split("\n"));
    el.sourceCode.value = lines.join("\n");
    updateLineNumbers();
    el.editStatus.textContent = "已插入示范片段；保存后重新分析验证。";
    return true;
}

function delay(ms) {
    return new Promise(resolve => window.setTimeout(resolve, ms));
}

function initTerminalEntry() {
    const input = el.terminalEntryInput;
    if (!input) return;
    input.addEventListener("keydown", event => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        const raw = input.value.trim();
        const command = raw.toLowerCase();
        if (!command) return;
        el.terminalEntryError.hidden = true;
        el.terminalEntryError.textContent = "";
        if (command === "deeptracer") {
            void runBootSequence();
            return;
        }
        if (command === "turtle") {
            window.open("/turtle/", "_blank", "noopener");
            return;
        }
        if (command === "netbrick") {
            window.open("/netbrick/", "_blank", "noopener");
            return;
        }
        if (command === "python") {
            switchToPage("code");
            return;
        }
        if (command === "help") {
            el.terminalEntryError.hidden = false;
            el.terminalEntryError.textContent =
                "commands: deeptracer / turtle / netbrick / python / help";
            return;
        }
        el.terminalEntryError.hidden = false;
        el.terminalEntryError.textContent = `command not found: ${raw} — try deeptracer`;
    });
    el.terminalSkip?.addEventListener("click", () => switchToPage("code"));
}

async function runBootSequence() {
    if (!el.bootOverlay || !el.bootTerminal) {
        switchToPage("code");
        return;
    }
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    el.bootOverlay.hidden = false;
    el.bootTerminal.textContent = "";
    const logo = window.DEEPTRACER_LOGO || "";
    if (logo) {
        const logoEl = document.createElement("pre");
        logoEl.className = "boot-logo";
        logoEl.textContent = logo;
        el.bootTerminal.appendChild(logoEl);
    }
    el.bootTerminal.insertAdjacentText("beforeend", "$ deeptracer\n");
    const lines = [
        "booting workbench...",
        "  turtle      ✓",
        "  python      ✓",
        "  netbrick    ✓",
        "  partner     ✓",
        "> 准备好了。先说你想弄清楚什么？"
    ];
    for (const line of lines) {
        if (!reduced) await delay(140);
        el.bootTerminal.insertAdjacentText("beforeend", `${line}\n`);
    }
    if (!reduced) await delay(360);
    el.bootOverlay.hidden = true;
    if (!el.sourceCode.value.trim()) {
        loadSample();
    } else {
        switchToPage("code");
    }
    ensurePartnerDock();
    partnerDock?.open?.();
}

function getTraceableFunctions() {
    const currentCode = el.sourceCode?.value.trim();
    if (!state.analyzedCode || state.analyzedCode !== currentCode) {
        return [];
    }
    return dataStore.analysisMap?.ast?.functions || [];
}

function resetTraceWorkspace(autoSelect = false) {
    state.traceResult = null;
    state.traceSelectedFunctions = new Set();
    const functions = getTraceableFunctions();
    if (autoSelect && functions.length) {
        const focusName = dataStore.analysisMap?.ast?.focusFunction;
        const preferred = functions.find(fn =>
            fn.qualified_name === focusName ||
            fn.name === focusName ||
            String(fn.qualified_name || "").endsWith(`.${focusName}`)
        ) || functions[0];
        state.traceSelectedFunctions.add(preferred.qualified_name || preferred.name);
    }
    renderTraceFunctionOptions();
    renderTraceResult();
}

function renderTraceFunctionOptions() {
    if (!el.traceFunctionList) return;
    const functions = getTraceableFunctions();
    const availableKeys = new Set(
        functions.map(fn => fn.qualified_name || fn.name)
    );
    state.traceSelectedFunctions = new Set(
        [...state.traceSelectedFunctions].filter(key => availableKeys.has(key))
    );

    if (!functions.length) {
        el.traceFunctionList.innerHTML = `
            <p class="trace-empty">先分析代码，才能选择需要追踪的函数。</p>
        `;
        if (!state.traceResult) {
            el.traceStatus.textContent = "等待代码分析结果。";
        }
        return;
    }

    el.traceFunctionList.innerHTML = functions.map(fn => {
        const key = fn.qualified_name || fn.name;
        return `
            <label class="trace-function-option">
                <input type="checkbox" data-trace-function="${escapeHtml(key)}" ${state.traceSelectedFunctions.has(key) ? "checked" : ""}>
                <span>
                    <strong>${escapeHtml(key)}</strong>
                    <code>${escapeHtml(fn.signature || fn.name)}</code>
                </span>
            </label>
        `;
    }).join("");

    if (!state.traceResult) {
        el.traceStatus.textContent = state.traceSelectedFunctions.size
            ? `已选择 ${state.traceSelectedFunctions.size} 个函数。`
            : "请选择至少一个函数，然后开始追踪。";
    }
}

function renderTraceResult() {
    if (!el.traceTreeView) return;
    const result = state.traceResult;
    if (!result) {
        el.traceTreeView.innerHTML = `
            <div class="trace-empty">
                <strong>调用树会显示在这里</strong>
                <p>选择函数后运行，可查看参数、返回值和嵌套调用关系。</p>
            </div>
        `;
        el.traceTerminalOutput.textContent = "";
        return;
    }

    const roots = result.traceTree || [];
    if (roots.length) {
        el.traceTreeView.innerHTML = `
            <div class="trace-tree">
                ${roots.map(renderTraceNode).join("")}
            </div>
        `;
    } else {
        el.traceTreeView.innerHTML = `
            <div class="trace-empty">
                <strong>没有捕获到目标函数调用</strong>
                <p>${escapeHtml(result.runtimeError || "请确认选中的函数会在当前代码中被调用。")}</p>
            </div>
        `;
    }
    const callCount = Number(result.callCount || 0);
    const duration = Number(result.durationMs || 0).toFixed(1);
    el.traceStatus.textContent = result.runtimeError
        ? `捕获 ${callCount} 次调用 · ${duration} ms · ${result.runtimeError}`
        : `捕获 ${callCount} 次调用 · 执行 ${duration} ms`;
    el.traceTerminalOutput.innerHTML = ansiToHtml(result.terminalOutput || "没有终端输出。");
}

function renderTraceNode(node) {
    const children = node.children || [];
    const cost = node.costSeconds == null
        ? ""
        : `<span class="trace-cost">${(node.costSeconds * 1000).toFixed(3)} ms</span>`;
    const returned = node.error
        ? `<div class="trace-node-return">抛出：${escapeHtml(node.error)}</div>`
        : node.returned != null
            ? `<div class="trace-node-return">返回：${escapeHtml(node.returned)}</div>`
            : `<div class="trace-node-return">未返回</div>`;
    const sourceButton = node.sourceRef
        ? `<button class="text-button source-jump" type="button"
                data-source-ref="${encodeSourceRef(node.sourceRef)}"
                data-source-origin="Tracer">定位源码</button>`
        : "";
    return `
        <details class="trace-node" open id="${escapeHtml(node.id || "")}">
            <summary class="trace-node-head">
                <span class="disclosure-chevron" aria-hidden="true"></span>
                <strong>→ ${escapeHtml(node.name)}</strong>
                ${cost}
                ${sourceButton}
            </summary>
            <div class="trace-node-body">
                <div class="trace-node-arguments">${escapeHtml(node.argumentText || node.arguments || "()")}</div>
                ${returned}
            </div>
            ${children.length ? `<div class="trace-children">${children.map(renderTraceNode).join("")}</div>` : ""}
        </details>
    `;
}

function setTraceView(viewName) {
    state.traceActiveView = viewName;
    el.traceViewTabs.querySelectorAll(".trace-view-tab").forEach(tab => {
        const isActive = tab.dataset.traceView === viewName;
        tab.classList.toggle("is-active", isActive);
        tab.setAttribute("aria-selected", String(isActive));
    });
    el.traceTreeView.hidden = viewName !== "tree";
    el.traceTerminalView.hidden = viewName !== "terminal";
}

function ansiToHtml(text) {
    const source = String(text || "");
    const colorMap = {
        "31": "ansi-red",
        "32": "ansi-green",
        "33": "ansi-yellow",
        "34": "ansi-blue",
        "35": "ansi-magenta",
        "36": "ansi-cyan",
    };
    const pattern = /\x1b\[([0-9;]*)m/g;
    let html = "";
    let cursor = 0;
    let activeClass = "";
    let match;
    while ((match = pattern.exec(source)) !== null) {
        const segment = source.slice(cursor, match.index);
        if (segment) {
            html += activeClass
                ? `<span class="${activeClass}">${escapeHtml(segment)}</span>`
                : escapeHtml(segment);
        }
        const codes = match[1].split(";").filter(Boolean);
        const resetIndex = codes.lastIndexOf("0");
        if (resetIndex >= 0) {
            codes.splice(0, resetIndex + 1);
        }
        const colorCode = [...codes].reverse().find(code => colorMap[code]);
        activeClass = colorCode ? colorMap[colorCode] : activeClass;
        if (codes.length === 0) {
            activeClass = "";
        }
        cursor = pattern.lastIndex;
    }
    const rest = source.slice(cursor);
    if (rest) {
        html += activeClass
            ? `<span class="${activeClass}">${escapeHtml(rest)}</span>`
            : escapeHtml(rest);
    }
    return html;
}

async function runTracerTrace() {
    const code = el.sourceCode.value.trim();
    if (!code) {
        setChatStatus("请先输入代码。");
        return;
    }
    if (state.analyzedCode !== code) {
        el.traceStatus.textContent = "代码已修改或尚未分析，请先重新分析代码。";
        return;
    }
    const functions = [...state.traceSelectedFunctions];
    if (!functions.length) {
        el.traceStatus.textContent = "请至少选择一个需要追踪的函数。";
        return;
    }

    const originalLabel = el.runTracerTrace.textContent;
    el.runTracerTrace.disabled = true;
    el.runTracerTrace.textContent = "正在追踪...";
    el.traceStatus.textContent = "Tracer 正在运行当前代码并收集调用关系...";
    try {
        const response = await fetch("/api/tracer/trace", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code,
                functions,
                options: {
                    timeTrace: el.traceTime.checked,
                    useColor: el.traceColor.checked,
                    exceptionTrace: el.traceExceptions.checked,
                    showLocals: el.traceLocals.checked,
                }
            })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || `HTTP ${response.status}`);
        }
        state.traceResult = payload;
        setTraceView("tree");
        renderTraceResult();
    } catch (error) {
        el.traceStatus.textContent = `调用追踪失败：${error.message}`;
    } finally {
        el.runTracerTrace.disabled = false;
        el.runTracerTrace.textContent = originalLabel;
    }
}

async function runTerminalCode() {
    const code = el.sourceCode.value.trim();
    if (!code) {
        el.terminalRunStatus.textContent = "请先输入代码。";
        return;
    }

    const originalLabel = el.runTerminalCode.textContent;
    el.runTerminalCode.disabled = true;
    el.runTerminalCode.textContent = "运行中...";
    el.terminalRunStatus.textContent = "正在独立子进程中运行当前代码...";
    el.terminalRunDuration.textContent = "";
    el.terminalRunOutput.textContent = "";
    try {
        const response = await fetch("/api/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || `HTTP ${response.status}`);
        }

        state.terminalOutputCode = code;
        const sections = [];
        if (payload.stdout) {
            sections.push(payload.stdout);
        }
        if (payload.stderr) {
            sections.push(`[stderr]\n${payload.stderr}`);
        }
        if (payload.runtimeError) {
            sections.push(`[error]\n${payload.runtimeError}`);
        }
        if (payload.traceback) {
            sections.push(`[traceback]\n${payload.traceback.trim()}`);
        }
        el.terminalRunOutput.textContent = sections.length
            ? sections.join("\n")
            : "(程序运行完成，没有输出)";
        el.terminalRunStatus.textContent = payload.runtimeError
            ? "运行结束，但程序抛出异常。"
            : "运行完成。";
        el.terminalRunDuration.textContent = `耗时 ${Number(payload.durationMs || 0).toFixed(1)} ms · exit ${payload.exitCode ?? 0}`;
    } catch (error) {
        state.terminalOutputCode = "";
        el.terminalRunStatus.textContent = `运行失败：${error.message}`;
        el.terminalRunOutput.textContent = error.message;
    } finally {
        el.runTerminalCode.disabled = false;
        el.runTerminalCode.textContent = originalLabel;
    }
}

function resetTerminalOutput() {
    state.terminalOutputCode = "";
    el.terminalRunStatus.textContent = "等待运行。";
    el.terminalRunDuration.textContent = "";
    el.terminalRunOutput.textContent = "点击“运行代码”查看程序输出。";
}

// 更新行号
function updateLineNumbers() {
    const code = el.sourceCode.value;
    const lines = code.split("\n").length;
    el.lineNumbers.textContent = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
    el.lineCount.textContent = `${lines} 行`;
}

// 同步行号滚动
function syncLineNumberScroll() {
    el.lineNumbers.scrollTop = el.sourceCode.scrollTop;
}

// 渲染指标卡片
function renderSummaryCards() {
    const metrics = dataStore.heroMetrics || [];
    el.summaryCards.innerHTML = metrics.map(m => `
        <div class="summary-card">
            <span>${escapeHtml(m.label)}</span>
            <strong>${escapeHtml(m.value)}</strong>
        </div>
    `).join("");
}

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function renderInlineMarkdown(text) {
    const codeSpans = [];
    let html = escapeHtml(text).replace(/`([^`]+)`/g, (_, code) => {
        const token = `__CODE_SPAN_${codeSpans.length}__`;
        codeSpans.push(`<code>${code}</code>`);
        return token;
    });

    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer noopener">$1</a>');
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, "$1<em>$2</em>");

    codeSpans.forEach((snippet, index) => {
        html = html.replace(`__CODE_SPAN_${index}__`, snippet);
    });
    return html;
}

function normalizeCodeLanguage(label) {
    const value = String(label || "").trim().toLowerCase();
    if (!value) return "text";
    if (["js", "javascript"].includes(value)) return "javascript";
    if (["ts", "typescript"].includes(value)) return "typescript";
    if (["py", "python"].includes(value)) return "python";
    if (["sh", "bash", "shell"].includes(value)) return "bash";
    return value;
}

function buildCodeBlockHtml(code, languageLabel) {
    const token = `code-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const language = normalizeCodeLanguage(languageLabel);
    chatCodeBlockRegistry.set(token, code);
    return `
        <div class="chat-codeblock">
            <div class="chat-codeblock-head">
                <span class="chat-codeblock-lang">${escapeHtml(language)}</span>
                <button class="chat-codeblock-copy" type="button" data-code-token="${token}">复制代码</button>
            </div>
            <pre><code>${escapeHtml(code)}</code></pre>
        </div>
    `;
}

function isMarkdownTableSeparator(line) {
    return /^\|?[\s:-]+\|[\s|:-]*$/.test(line.trim());
}

function parseMarkdownTable(lines, startIndex) {
    const headerLine = lines[startIndex]?.trim();
    const separatorLine = lines[startIndex + 1]?.trim();
    if (!headerLine || !separatorLine) return null;
    if (!headerLine.includes("|") || !isMarkdownTableSeparator(separatorLine)) return null;

    const extractCells = (line) =>
        line
            .trim()
            .replace(/^\|/, "")
            .replace(/\|$/, "")
            .split("|")
            .map(cell => cell.trim());

    const headers = extractCells(headerLine);
    if (!headers.length) return null;

    const rows = [];
    let cursor = startIndex + 2;
    while (cursor < lines.length) {
        const candidate = lines[cursor].trim();
        if (!candidate || !candidate.includes("|")) break;
        rows.push(extractCells(candidate));
        cursor += 1;
    }

    return {
        html: `
            <div class="chat-table-wrap">
                <table class="chat-table">
                    <thead>
                        <tr>${headers.map(cell => `<th>${renderInlineMarkdown(cell)}</th>`).join("")}</tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `<tr>${row.map(cell => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`).join("")}
                    </tbody>
                </table>
            </div>
        `,
        nextIndex: cursor - 1
    };
}

function renderMarkdown(text) {
    const normalized = String(text || "").replace(/\r\n/g, "\n").trim();
    if (!normalized) {
        return "";
    }

    const lines = normalized.split("\n");
    const blocks = [];
    let paragraph = [];
    let listType = null;
    let listItems = [];
    let inCodeFence = false;
    let codeFenceLines = [];
    let codeFenceLanguage = "";

    function flushParagraph() {
        if (!paragraph.length) return;
        blocks.push(`<p>${renderInlineMarkdown(paragraph.join(" "))}</p>`);
        paragraph = [];
    }

    function flushList() {
        if (!listItems.length || !listType) return;
        const itemsHtml = listItems.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join("");
        blocks.push(`<${listType}>${itemsHtml}</${listType}>`);
        listItems = [];
        listType = null;
    }

    function flushCodeFence() {
        if (!inCodeFence) return;
        blocks.push(buildCodeBlockHtml(codeFenceLines.join("\n"), codeFenceLanguage));
        codeFenceLines = [];
        codeFenceLanguage = "";
        inCodeFence = false;
    }

    for (let index = 0; index < lines.length; index += 1) {
        const rawLine = lines[index];
        const line = rawLine.trimEnd();

        const fenceMatch = line.trim().match(/^```([\w-]*)\s*$/);
        if (fenceMatch) {
            flushParagraph();
            flushList();
            if (inCodeFence) {
                flushCodeFence();
            } else {
                inCodeFence = true;
                codeFenceLines = [];
                codeFenceLanguage = fenceMatch[1] || "";
            }
            continue;
        }

        if (inCodeFence) {
            codeFenceLines.push(rawLine);
            continue;
        }

        const trimmed = line.trim();
        if (!trimmed) {
            flushParagraph();
            flushList();
            continue;
        }

        if (/^([-*_]\s*){3,}$/.test(trimmed)) {
            flushParagraph();
            flushList();
            blocks.push("<hr>");
            continue;
        }

        const tableBlock = parseMarkdownTable(lines, index);
        if (tableBlock) {
            flushParagraph();
            flushList();
            blocks.push(tableBlock.html);
            index = tableBlock.nextIndex;
            continue;
        }

        const headingMatch = trimmed.match(/^(#{1,4})\s+(.*)$/);
        if (headingMatch) {
            flushParagraph();
            flushList();
            const level = headingMatch[1].length;
            blocks.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`);
            continue;
        }

        const quoteMatch = trimmed.match(/^>\s?(.*)$/);
        if (quoteMatch) {
            flushParagraph();
            flushList();
            blocks.push(`<blockquote>${renderInlineMarkdown(quoteMatch[1])}</blockquote>`);
            continue;
        }

        const orderedMatch = trimmed.match(/^\d+\.\s+(.*)$/);
        if (orderedMatch) {
            flushParagraph();
            if (listType && listType !== "ol") flushList();
            listType = "ol";
            listItems.push(orderedMatch[1]);
            continue;
        }

        const unorderedMatch = trimmed.match(/^[-*+]\s+(.*)$/);
        if (unorderedMatch) {
            flushParagraph();
            if (listType && listType !== "ul") flushList();
            listType = "ul";
            listItems.push(unorderedMatch[1]);
            continue;
        }

        flushList();
        paragraph.push(trimmed);
    }

    flushParagraph();
    flushList();
    flushCodeFence();
    return blocks.join("");
}

function currentDisplayName() {
    return state.currentFileName || "编辑器中的 Python 代码";
}

function setChatStatus(text) {
    if (el.chatStatus) {
        el.chatStatus.textContent = text;
    }
}

function setChatBusy(isBusy) {
    if (el.chatSend) {
        el.chatSend.disabled = isBusy;
    }
    if (el.chatStop) {
        el.chatStop.hidden = !isBusy;
    }
}

function renderRuntimeBanner() {
    if (!el.runtimeBanner) return;
    const banner = dataStore.runtimeBanner;
    if (!banner) {
        el.runtimeBanner.hidden = true;
        el.runtimeBanner.innerHTML = "";
        return;
    }
    el.runtimeBanner.hidden = false;
    el.runtimeBanner.innerHTML = `
        <h3>${escapeHtml(banner.title)}</h3>
        <p>${escapeHtml(banner.body)}</p>
    `;
}

function renderChatTranscript() {
    if (!el.chatTranscript) return;
    if (!state.chatMessages.length) {
        el.chatTranscript.innerHTML = '<div class="chat-empty">这里会保留你基于当前代码的追问记录。</div>';
        return;
    }
    chatCodeBlockRegistry = new Map();
    el.chatTranscript.innerHTML = state.chatMessages.map(message => `
        <article class="chat-message ${message.role} ${message.pending ? "pending" : ""}">
            <div class="chat-role">${message.role === "user" ? "你" : "DeepTracer"}</div>
            <div class="chat-body">${renderMarkdown(message.content)}</div>
        </article>
    `).join("");
    el.chatTranscript.scrollTop = el.chatTranscript.scrollHeight;
}

function appendChatMessage(role, content, options = {}) {
    const message = {
        id: options.id || `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        role,
        content: content || "",
        pending: Boolean(options.pending)
    };
    state.chatMessages.push(message);
    renderChatTranscript();
    return message.id;
}

function updateChatMessage(messageId, updater) {
    const index = state.chatMessages.findIndex(message => message.id === messageId);
    if (index === -1) return;
    const current = state.chatMessages[index];
    state.chatMessages[index] = { ...current, ...updater(current) };
    renderChatTranscript();
}

function resetChatState(statusText) {
    if (state.activeChatController) {
        state.activeChatController.abort();
        state.activeChatController = null;
    }
    state.chatMessages = [];
    state.activeChatRequestId = 0;
    state.latestAnalysisTaskId = dataStore.meta?.taskId || null;
    setChatBusy(false);
    setChatStatus(
        statusText ||
        "分析完成后，可以继续追问这段代码为什么这样写、哪里更值得先看、下一步应该怎么改。"
    );
    renderChatTranscript();
}

function buildAnalysisSnapshot() {
    return {
        heroMetrics: dataStore.heroMetrics || [],
        analysisMap: dataStore.analysisMap || {},
        suggestions: dataStore.suggestions || [],
        meta: dataStore.meta || {}
    };
}

function buildChatRequestMessages(question) {
    const priorMessages = state.chatMessages
        .filter(message => message.content && !message.pending)
        .slice(-8)
        .map(message => ({ role: message.role, content: message.content }));
    priorMessages.push({ role: "user", content: question });
    return priorMessages;
}

function abortActiveChat(reason = "已停止当前回答。") {
    if (state.activeChatController) {
        state.activeChatController.abort();
        state.activeChatController = null;
    }
    setChatBusy(false);
    if (reason) {
        setChatStatus(reason);
    }
}

async function copyChatCode(token, trigger) {
    const code = chatCodeBlockRegistry.get(token);
    if (!code) {
        setChatStatus("未找到可复制的代码块。");
        return;
    }
    try {
        await navigator.clipboard.writeText(code);
        setChatStatus("代码块已复制到剪贴板。");
        if (trigger) {
            const original = trigger.textContent;
            trigger.textContent = "已复制";
            trigger.dataset.copied = "true";
            window.setTimeout(() => {
                trigger.textContent = original;
                delete trigger.dataset.copied;
            }, 1200);
        }
    } catch (error) {
        console.error("复制聊天代码块失败:", error);
        setChatStatus("复制代码块失败。");
    }
}

function handleChatEvent(rawEvent, requestId, assistantMessageId) {
    if (requestId !== state.activeChatRequestId) return;
    const lines = rawEvent.split(/\r?\n/);
    let eventName = "message";
    const dataLines = [];
    lines.forEach(line => {
        if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trimStart());
        }
    });
    if (!dataLines.length) return;

    let payload;
    try {
        payload = JSON.parse(dataLines.join("\n"));
    } catch (error) {
        console.error("解析对话事件失败:", error, rawEvent);
        return;
    }

    if (eventName === "meta") {
        state.latestAnalysisTaskId = payload.taskId || state.latestAnalysisTaskId;
        setChatStatus(`正在基于 ${payload.displayName || currentDisplayName()} 组织回答...`);
        return;
    }

    if (eventName === "chunk") {
        updateChatMessage(assistantMessageId, current => ({
            content: `${current.content}${payload.delta || ""}`
        }));
        return;
    }

    if (eventName === "done") {
        updateChatMessage(assistantMessageId, () => ({ pending: false }));
        state.activeChatController = null;
        setChatBusy(false);
        setChatStatus("回答完成。你可以继续追问细节，或切回上面的分析结果继续查看。");
        return;
    }

    if (eventName === "error") {
        updateChatMessage(assistantMessageId, current => ({
            content: current.content || payload.message || "对话生成失败。",
            pending: false
        }));
        state.activeChatController = null;
        setChatBusy(false);
        setChatStatus(payload.message || "对话生成失败。");
    }
}

async function consumeChatStream(response, requestId, assistantMessageId) {
    const reader = response.body?.getReader();
    if (!reader) {
        throw new Error("当前浏览器无法读取流式响应。");
    }

    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
            const rawEvent = buffer.slice(0, boundary).trim();
            buffer = buffer.slice(boundary + 2);
            if (rawEvent) {
                handleChatEvent(rawEvent, requestId, assistantMessageId);
            }
            boundary = buffer.indexOf("\n\n");
        }
    }

    const trailing = buffer.trim();
    if (trailing) {
        handleChatEvent(trailing, requestId, assistantMessageId);
    }
}

async function sendChatMessage() {
    const question = el.chatInput?.value.trim();
    const code = el.sourceCode.value.trim();
    if (!question) {
        setChatStatus("先输入一个具体问题，再开始追问。");
        return;
    }
    if (!code) {
        setChatStatus("请先输入代码，再发起追问。");
        return;
    }
    if (state.analyzedCode !== code) {
        setChatStatus("代码已修改或尚未完成分析，请先重新点击“分析代码”。");
        return;
    }

    abortActiveChat("");
    const requestId = state.activeChatRequestId + 1;
    state.activeChatRequestId = requestId;
    const controller = new AbortController();
    state.activeChatController = controller;
    setChatBusy(true);

    const requestMessages = buildChatRequestMessages(question);
    appendChatMessage("user", question);
    const assistantMessageId = appendChatMessage("assistant", "", { pending: true });
    el.chatInput.value = "";
    setChatStatus("正在基于当前代码和分析结果组织回答...");

    try {
        const response = await fetch("/api/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            signal: controller.signal,
            body: JSON.stringify({
                code,
                displayName: currentDisplayName(),
                taskId: state.latestAnalysisTaskId,
                analysis: buildAnalysisSnapshot(),
                messages: requestMessages
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `HTTP ${response.status}`);
        }

        await consumeChatStream(response, requestId, assistantMessageId);
    } catch (error) {
        if (error.name === "AbortError") {
            updateChatMessage(assistantMessageId, current => ({
                content: current.content || "这次回答已停止。",
                pending: false
            }));
            setChatStatus("已停止当前回答。");
        } else {
            console.error("发送对话失败:", error);
            updateChatMessage(assistantMessageId, current => ({
                content: current.content || `对话生成失败：${error.message}`,
                pending: false
            }));
            setChatStatus(`对话生成失败：${error.message}`);
        }
        if (requestId === state.activeChatRequestId) {
            state.activeChatController = null;
            setChatBusy(false);
        }
    }
}

// 渲染分析标签页内容
function renderAnalysisTab() {
    const tab = dataStore.analysisMap[state.activeTab] || {};
    const cards = tab.cards || [];
    const bars = tab.bars || [];
    const functions = tab.functions || [];
    const hotspots = tab.hotspots || [];

    el.tabSummary.innerHTML = `
        <h3>${escapeHtml(tab.title || "")}</h3>
        <p>${escapeHtml(tab.summary || "")}</p>
    `;

    const cardsHtml = cards.length
        ? `
            <div class="tab-metric-grid">
                ${cards.map(card => `
                    <div class="tab-metric">
                        <span>${escapeHtml(card.label)}</span>
                        <strong>${escapeHtml(card.value)}</strong>
                    </div>
                `).join("")}
            </div>
        `
        : "";

    const barsHtml = bars.length
        ? bars.map(bar => {
            const width = Math.max(0, Math.min(100, Number(bar.value) || 0));
            return `
                <div class="chart-item">
                    <div class="chart-meta">
                        <span>${escapeHtml(bar.label)}</span>
                        <span>${escapeHtml(bar.value)}</span>
                    </div>
                    <div class="chart-track">
                        <div class="chart-fill" style="width: ${width}%"></div>
                    </div>
                </div>
            `;
        }).join("")
        : "";

    const hotspotsHtml = hotspots.length
        ? `
            <div class="hotspot-list">
                <div class="hotspot-list-head">
                    <h4>可定位热点</h4>
                    <span>点击后跳到源代码中的对应位置</span>
                </div>
                ${hotspots.map(hotspot => `
                    <button class="hotspot-item" type="button"
                        data-source-ref="${encodeSourceRef(hotspot.sourceRef)}"
                        data-source-origin="${escapeHtml(hotspot.sourceRef?.origin || "performance")}">
                        <span>
                            <strong>${escapeHtml(hotspot.label || "热点")}</strong>
                            <small>第 ${escapeHtml(hotspot.line || "?")} 行</small>
                        </span>
                        <span class="hotspot-metric">
                            ${hotspot.totalMs != null
                                ? `${Number(hotspot.totalMs).toFixed(2)} ms`
                                : `${Number(hotspot.sizeKb || 0).toFixed(1)} KB`}
                        </span>
                    </button>
                `).join("")}
            </div>
        `
        : "";

    const functionsHtml = functions.length
        ? `
            <div class="function-signature-list">
                <div class="function-signature-title">
                    <h4>函数签名与参数</h4>
                    <div class="inline-actions">
                        <button class="text-button" type="button" data-function-details="expand">展开全部</button>
                        <button class="text-button" type="button" data-function-details="collapse">收起全部</button>
                    </div>
                </div>
                ${functions.map(fn => {
                    const parameters = (fn.parameters || []).map(parameter => {
                        const details = [
                            parameter.kind,
                            parameter.annotation ? `类型：${parameter.annotation}` : "",
                            parameter.default !== null && parameter.default !== undefined
                                ? `默认值：${parameter.default}`
                                : ""
                        ].filter(Boolean).map(escapeHtml).join(" · ");
                        return `
                            <span class="signature-parameter">
                                <strong>${escapeHtml(parameter.name)}</strong>
                                <small>${details}</small>
                            </span>
                        `;
                    }).join("");
                    return `
                        <details class="function-signature-card">
                            <summary class="function-signature-head">
                                <span class="function-signature-main">
                                    <strong>${escapeHtml(fn.name)}</strong>
                                    <code>${escapeHtml(fn.signature)}</code>
                                </span>
                                <span class="function-signature-meta">
                                    第 ${escapeHtml(fn.lineno)} 行
                                    ${fn.sourceRef
                                        ? `<button class="text-button source-jump" type="button"
                                                data-source-ref="${encodeSourceRef(fn.sourceRef)}"
                                                data-source-origin="函数签名">定位</button>`
                                        : ""}
                                    <span class="disclosure-chevron" aria-hidden="true"></span>
                                </span>
                            </summary>
                            <div class="signature-parameters">
                                ${parameters || '<span class="signature-parameter"><small>该函数没有显式参数</small></span>'}
                            </div>
                        </details>
                    `;
                }).join("")}
            </div>
        `
        : "";

    el.tabBars.innerHTML = cardsHtml + barsHtml + hotspotsHtml + functionsHtml;

    el.tabPoints.innerHTML = (tab.points || []).map(p => `
        <div class="notes-item">${escapeHtml(p)}</div>
    `).join("");
}

// 渲染建议列表
function renderSuggestions() {
    const suggestions = dataStore.suggestions || [];
    el.suggestionList.innerHTML = suggestions.map(s => `
        <button class="suggestion-item ${s.id === state.activeSuggestion ? "is-active" : ""}" data-suggestion="${escapeHtml(s.id)}">
            <div class="suggestion-title">${escapeHtml(s.title)}</div>
            <div class="suggestion-meta">建议强度：${escapeHtml(s.priority || "-")} · 置信度：${escapeHtml(s.confidence || "-")} · 风险：${escapeHtml(s.risk || "-")}</div>
        </button>
    `).join("");
    
    renderSuggestionDetail();
}

// 渲染建议详情
function renderSuggestionDetail() {
    const suggestion = (dataStore.suggestions || []).find(s => s.id === state.activeSuggestion);
    if (!suggestion) {
        el.suggestionDetail.innerHTML = "<p>还没有可展示的建议。</p>";
        return;
    }
    const detail = suggestion.detail || {};
    const anchors = detail.codeAnchors || suggestion.anchors || [];
    const patchResult = state.patchPlans.get(suggestion.id);
    const patchError = state.patchErrors.get(suggestion.id);
    const patchBusy = state.patchBusySuggestion === suggestion.id;
    const anchorHtml = anchors.length
        ? `
            <div class="suggestion-anchor-list">
                ${anchors.map(anchor => `
                    <article class="suggestion-anchor">
                        <div class="suggestion-anchor-head">
                            <span class="suggestion-anchor-kind">${escapeHtml(anchor.kind || "anchor")}</span>
                            <strong>${escapeHtml(anchor.label || "未命名位置")}</strong>
                            ${anchor.line ? `<span class="suggestion-anchor-line">第 ${anchor.line} 行</span>` : ""}
                            ${anchor.sourceRef
                                ? `<button class="text-button source-jump" type="button"
                                        data-source-ref="${encodeSourceRef(anchor.sourceRef)}"
                                        data-source-origin="建议锚点">定位源码</button>`
                                : ""}
                        </div>
                        ${anchor.snippet ? `<pre class="suggestion-anchor-snippet"><code>${escapeHtml(anchor.snippet)}</code></pre>` : ""}
                    </article>
                `).join("")}
            </div>
        `
        : '<div class="suggestion-empty">当前没有可展示的代码锚点。</div>';

    let patchHtml = "";
    if (patchResult?.available) {
        const plan = patchResult.plan || {};
        const modeLabel = patchResult.generationMode === "model-assisted"
            ? "模型辅助"
            : "本地规则";
        patchHtml = `
            <section class="patch-panel">
                <div class="patch-panel-head">
                    <div>
                        <h4>可应用 Patch</h4>
                        <p>${escapeHtml(plan.summary || plan.title || "已生成经过结构校验的修改方案。")}</p>
                    </div>
                    <span class="patch-risk">${modeLabel} · 风险：${escapeHtml(plan.risk || "-")}</span>
                </div>
                <pre class="patch-preview"><code>${escapeHtml(patchResult.previewDiff || "")}</code></pre>
                <div class="inline-actions">
                    <button class="action-button small primary" type="button"
                        data-suggestion-action="apply-patch"
                        data-suggestion-id="${escapeHtml(suggestion.id)}">应用并验证</button>
                    <button class="text-button" type="button"
                        data-suggestion-action="clear-patch"
                        data-suggestion-id="${escapeHtml(suggestion.id)}">取消方案</button>
                </div>
            </section>
        `;
    } else if (patchResult && !patchResult.available) {
        patchHtml = `
            <section class="patch-panel">
                <h4>无法安全自动生成 Patch</h4>
                <p class="patch-note">${escapeHtml(patchResult.reason || "该建议需要人工判断。")}</p>
            </section>
        `;
    } else {
        patchHtml = `
            <section class="patch-panel">
                <div class="patch-panel-head">
                    <div>
                        <h4>从建议生成修改</h4>
                        <p>先生成结构化 Patch，预览后再决定是否应用。</p>
                    </div>
                    <button class="action-button small primary" type="button"
                        data-suggestion-action="generate-patch"
                        data-suggestion-id="${escapeHtml(suggestion.id)}"
                        ${patchBusy ? "disabled" : ""}>
                        ${patchBusy ? "正在生成..." : "生成 Patch"}
                    </button>
                </div>
                ${patchError ? `<p class="patch-error">${escapeHtml(patchError)}</p>` : ""}
            </section>
        `;
    }

    el.suggestionDetail.innerHTML = `
        <h3>${escapeHtml(suggestion.title)}</h3>
        <p>${escapeHtml(suggestion.explanation || "")}</p>
        <div class="suggestion-meta">建议强度：${escapeHtml(suggestion.priority || "-")} · 置信度：${escapeHtml(suggestion.confidence || "-")} · 风险：${escapeHtml(suggestion.risk || "-")}</div>
        <div class="suggestion-detail-grid">
            <section class="suggestion-detail-card">
                <h4>为什么选中这条</h4>
                <p>${escapeHtml(detail.whySelected || suggestion.note || "当前没有额外说明。")}</p>
            </section>
            <section class="suggestion-detail-card">
                <h4>如果不改会怎样</h4>
                <p>${escapeHtml(detail.riskIfUnchanged || "当前没有额外风险说明。")}</p>
            </section>
            <section class="suggestion-detail-card">
                <h4>最小可执行修改方向</h4>
                <p>${escapeHtml(detail.nextChange || "当前没有额外的下一步建议。")}</p>
            </section>
        </div>
        <section class="suggestion-detail-card">
            <h4>它对应代码里的哪个位置</h4>
            ${anchorHtml}
        </section>
        ${patchHtml}
    `;
}

async function generateSuggestionPatch(suggestionId) {
    const suggestion = (dataStore.suggestions || []).find(item => item.id === suggestionId);
    if (!suggestion) return;
    if (
        state.analyzedCode &&
        el.sourceCode.value.trim() !== state.analyzedCode
    ) {
        state.patchErrors.set(suggestionId, "代码已经修改，请先重新分析再生成 Patch。");
        renderSuggestionDetail();
        return;
    }

    state.patchBusySuggestion = suggestionId;
    state.patchErrors.delete(suggestionId);
    renderSuggestionDetail();
    try {
        const response = await fetch("/api/edit/plan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: el.sourceCode.value,
                displayName: currentDisplayName(),
                suggestion,
                allowModel: true
            })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || `HTTP ${response.status}`);
        }
        state.patchPlans.set(suggestionId, payload);
    } catch (error) {
        state.patchErrors.set(suggestionId, `Patch 生成失败：${error.message}`);
    } finally {
        state.patchBusySuggestion = "";
        renderSuggestionDetail();
    }
}

function pushEditSnapshot(label, code = el.sourceCode.value) {
    state.editHistory.push({
        code,
        dataStore: deepClone(dataStore),
        sourceHash: state.sourceHash || dataStore.meta?.sourceHash || "",
        latestAnalysisTaskId: state.latestAnalysisTaskId,
        traceResult: state.traceResult ? deepClone(state.traceResult) : null,
        traceSelectedFunctions: [...state.traceSelectedFunctions],
        terminalOutputCode: state.terminalOutputCode,
        label,
        createdAt: new Date().toISOString()
    });
    if (state.editHistory.length > 10) {
        state.editHistory.shift();
    }
    updateRollbackButton();
}

function updateRollbackButton() {
    if (!el.rollbackEdit) return;
    el.rollbackEdit.hidden = state.editHistory.length === 0;
}

async function applySuggestionPatch(suggestionId) {
    const patchResult = state.patchPlans.get(suggestionId);
    if (!patchResult?.available || !patchResult.plan) return;
    const beforeCode = el.sourceCode.value;
    el.editStatus.textContent = "正在校验并应用 Patch...";
    try {
        const response = await fetch("/api/edit/apply", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: beforeCode,
                plan: patchResult.plan
            })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || `HTTP ${response.status}`);
        }

        pushEditSnapshot(`应用 Patch：${patchResult.plan.title || suggestionId}`);
        applyPatchedCode(payload.code, {
            beforeCode,
            afterHash: payload.afterHash,
            label: patchResult.plan.title || suggestionId
        });
        await verifyAppliedEdit(beforeCode, payload.code);
    } catch (error) {
        el.editStatus.textContent = `Patch 应用失败：${error.message}`;
        state.patchPlans.delete(suggestionId);
        state.patchErrors.set(suggestionId, `Patch 应用失败：${error.message}`);
        renderSuggestionDetail();
    }
}

function applyPatchedCode(nextCode, { beforeCode, afterHash, label = "自动修改" }) {
    el.sourceCode.value = nextCode;
    state.currentCode = nextCode;
    state.originalCode = beforeCode;
    state.analyzedCode = "";
    state.sourceHash = "";
    state.latestAnalysisTaskId = null;
    state.hasUnsavedChanges = true;
    state.isEditing = false;
    el.sourceCode.readOnly = true;
    el.sourceCode.hidden = true;
    el.diffViewer.hidden = false;
    el.editCode.hidden = true;
    el.saveEdit.hidden = true;
    el.cancelEdit.hidden = true;
    el.editStatus.textContent = state.isBuiltInSample
        ? `${label} · 示例副本已修改，重载示例可恢复原文`
        : `${label} · 已修改，等待重新分析`;
    updateLineNumbers();
    resetTraceWorkspace(false);
    resetTerminalOutput();
    resetChatState("代码已通过 Patch 修改，请重新分析后再继续追问。");
    showDiff(beforeCode, nextCode, { afterHash });
    switchToPage("code");
}

async function verifyAppliedEdit(beforeCode, afterCode) {
    if (!el.verificationPanel) return;
    el.verificationPanel.hidden = false;
    el.verificationPanel.innerHTML = `
        <div class="verification-loading">正在分别运行修改前后的代码并比较行为...</div>
    `;
    try {
        const response = await fetch("/api/edit/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ beforeCode, afterCode })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || `HTTP ${response.status}`);
        }
        state.verificationResult = payload;
        renderVerification(payload);
    } catch (error) {
        state.verificationResult = null;
        el.verificationPanel.innerHTML = `
            <div class="patch-error">自动验证失败：${escapeHtml(error.message)}</div>
        `;
    }
}

function renderVerification(result) {
    if (!el.verificationPanel) return;
    const behaviorLabels = {
        unchanged: "行为未变化",
        changed: "输出发生变化",
        improved: "运行时错误已修复",
        regressed: "修改后出现运行错误"
    };
    const behavior = result.behavior || "changed";
    const before = result.before || {};
    const after = result.after || {};
    el.verificationPanel.hidden = false;
    el.verificationPanel.innerHTML = `
        <div class="verification-head">
            <div>
                <span class="analysis-eyebrow">Verification</span>
                <h3>修改前后验证</h3>
            </div>
            <strong class="verification-status is-${escapeHtml(behavior)}">
                ${escapeHtml(behaviorLabels[behavior] || behavior)}
            </strong>
        </div>
        <div class="verification-grid">
            ${renderVerificationRun("修改前", before)}
            ${renderVerificationRun("修改后", after)}
        </div>
        <div class="verification-meta">
            <span>语法：${result.syntax?.passed ? "通过" : "失败"}</span>
            <span>运行：${result.runtime?.passed ? "通过" : "失败"}</span>
            <span>耗时变化：${Number(result.performance?.durationDeltaMs || 0).toFixed(2)} ms</span>
        </div>
        <p class="patch-note">${escapeHtml(result.tests?.note || "")}</p>
    `;
}

function renderVerificationRun(label, result) {
    const output = [
        result.stdout || "",
        result.stderr ? `[stderr]\n${result.stderr}` : "",
        result.runtimeError ? `[error]\n${result.runtimeError}` : ""
    ].filter(Boolean).join("\n") || "(无输出)";
    return `
        <section class="verification-run">
            <div class="verification-run-head">
                <strong>${escapeHtml(label)}</strong>
                <span>exit ${escapeHtml(String(result.exitCode ?? "-"))} · ${Number(result.durationMs || 0).toFixed(2)} ms</span>
            </div>
            <pre>${escapeHtml(output)}</pre>
        </section>
    `;
}

function sanitizeVisualizationHtml(html) {
    if (!html) return "";
    return String(html)
        // Generated AST HTML may reference local helper scripts that are not served by the app.
        .replace(/<script[^>]+src=["']lib\/bindings\/utils\.js["'][^>]*><\/script>/gi, "")
        .replace(/<script[^>]+src=["']\.{1,2}\/[^"']+["'][^>]*><\/script>/gi, "");
}

// 渲染可视化
function renderVisualizations() {
    const viz = dataStore.visualizations || { ast: "", performance: "" };
    
    console.log("可视化数据详情:", {
        hasViz: !!dataStore.visualizations,
        astLength: viz.ast ? viz.ast.length : 0,
        perfLength: viz.performance ? viz.performance.length : 0
    });
    
    // 渲染 AST 可视化
    if (viz.ast && viz.ast.trim().length > 0) {
        const iframe = document.createElement("iframe");
        iframe.style.width = "100%";
        iframe.style.height = "600px";
        iframe.style.border = "none";
        iframe.setAttribute("sandbox", "allow-scripts");
        el.astVizContent.innerHTML = "";
        el.astVizContent.appendChild(iframe);
        iframe.srcdoc = sanitizeVisualizationHtml(viz.ast);
    } else {
        el.astVizContent.innerHTML = '<p style="padding: 20px; text-align: center; color: var(--muted);">AST 可视化生成失败或不可用</p>';
    }
    
    // 渲染性能可视化
    if (viz.performance && viz.performance.trim().length > 0) {
        const iframe = document.createElement("iframe");
        iframe.style.width = "100%";
        iframe.style.height = "700px";
        iframe.style.border = "none";
        // PyInstrument persists its view state in localStorage/sessionStorage.
        iframe.setAttribute("sandbox", "allow-scripts allow-same-origin");
        el.perfVizContent.innerHTML = renderVisualizationHotspots(
            dataStore.analysisMap?.performance?.hotspots || []
        );
        el.perfVizContent.appendChild(iframe);
        iframe.srcdoc = sanitizeVisualizationHtml(viz.performance);
    } else {
        el.perfVizContent.innerHTML = `
            ${renderVisualizationHotspots(dataStore.analysisMap?.performance?.hotspots || [])}
            <p style="padding: 20px; text-align: center; color: var(--muted);">性能分析可视化生成失败或不可用</p>
        `;
    }
}

function renderVisualizationHotspots(hotspots) {
    if (!hotspots.length) {
        return `
            <div class="viz-hotspot-empty">
                当前没有可定位的性能样本；火焰图仍会保留用于查看可用的采样数据。
            </div>
        `;
    }
    return `
        <div class="viz-hotspot-bar">
            <span>热点定位</span>
            ${hotspots.map(hotspot => `
                <button type="button" class="viz-hotspot-jump"
                    data-source-ref="${encodeSourceRef(hotspot.sourceRef)}"
                    data-source-origin="性能火焰图">
                    ${escapeHtml(hotspot.label)} · 第 ${escapeHtml(hotspot.line)} 行
                </button>
            `).join("")}
        </div>
    `;
}

// 渲染所有内容
function renderAll() {
    renderRuntimeBanner();
    renderSummaryCards();
    renderAnalysisTab();
    renderSuggestions();
    renderVisualizations();
    renderChatTranscript();
    renderTraceFunctionOptions();
    renderTraceResult();
}

function getDefaultCodeLayout() {
    const viewportWidth = document.querySelector('.code-layout-viewport')?.clientWidth || window.innerWidth;
    const preferredCodeWidth = window.innerWidth >= 1600 ? 640 : window.innerWidth >= 1280 ? 620 : CODE_PANE_MIN_WIDTH;
    const flowWidth = Math.max(
        FLOW_PANE_MIN_WIDTH,
        Math.round(viewportWidth - preferredCodeWidth - RESIZE_HANDLE_WIDTH)
    );
    return `${preferredCodeWidth}px ${RESIZE_HANDLE_WIDTH}px ${flowWidth}px`;
}

function applyCodeLayout(templateColumns, { manual = false } = {}) {
    const container = document.querySelector(".code-layout");
    if (!container) return;
    container.style.gridTemplateColumns = templateColumns;
    if (manual) {
        hasManualCodeLayout = true;
    }
}

function applyDefaultCodeLayout(force = false) {
    if (!force && hasManualCodeLayout) return;
    applyCodeLayout(getDefaultCodeLayout());
}

// 设置主题
function setTheme(theme) {
    state.theme = theme;
    document.body.setAttribute("data-theme", theme);
}

// 切换主题
function toggleTheme() {
    const index = themes.indexOf(state.theme);
    setTheme(themes[(index + 1) % themes.length]);
}

function resetTutorSurface() {
    currentTutorVisualizer = null;
    tutorConnectorRedrawQueued = false;
    tutorConnectorTracking = false;
    if (el.tutorVisualizerMount) {
        delete el.tutorVisualizerMount.dataset.connectorBindingsReady;
        el.tutorVisualizerMount.hidden = true;
        el.tutorVisualizerMount.innerHTML = "";
    }
    if (el.tutorPlaceholder) {
        el.tutorPlaceholder.hidden = false;
        el.tutorPlaceholder.style.display = "";
    }
    clearTutorMoments();
}

function queueTutorConnectorRedraw() {
    if (!currentTutorVisualizer || typeof currentTutorVisualizer.redrawConnectors !== "function") {
        return;
    }
    if (tutorConnectorRedrawQueued) {
        return;
    }
    tutorConnectorRedrawQueued = true;
    window.requestAnimationFrame(() => {
        tutorConnectorRedrawQueued = false;
        if (!currentTutorVisualizer || typeof currentTutorVisualizer.redrawConnectors !== "function") {
            return;
        }
        currentTutorVisualizer.redrawConnectors();
    });
}

function redrawTutorConnectorsImmediate() {
    if (!currentTutorVisualizer || typeof currentTutorVisualizer.redrawConnectors !== "function") {
        return;
    }
    tutorConnectorRedrawQueued = false;
    currentTutorVisualizer.redrawConnectors();
}

function startTutorConnectorTracking() {
    if (tutorConnectorTracking) {
        return;
    }
    tutorConnectorTracking = true;
    redrawTutorConnectorsImmediate();

    const tick = () => {
        if (!tutorConnectorTracking) {
            return;
        }
        redrawTutorConnectorsImmediate();
        window.requestAnimationFrame(tick);
    };

    window.requestAnimationFrame(tick);
}

function stopTutorConnectorTracking() {
    tutorConnectorTracking = false;
    redrawTutorConnectorsImmediate();
}

function styleTutorVisualizer() {
    const root = el.tutorVisualizerMount;
    if (!root) {
        return;
    }

    root.querySelectorAll("#editCodeLinkDiv, #codeFooterDocs").forEach((node) => {
        node.remove();
    });

    if (root.dataset.connectorBindingsReady === "true") {
        return;
    }
    root.dataset.connectorBindingsReady = "true";

    root.querySelectorAll("#pyCodeOutputDiv, #dataViz, #codAndNav").forEach((node) => {
        node.addEventListener("scroll", redrawTutorConnectorsImmediate, { passive: true });
        node.addEventListener("pointerdown", startTutorConnectorTracking, { passive: true });
        node.addEventListener("pointermove", redrawTutorConnectorsImmediate, { passive: true });
        node.addEventListener("pointerup", stopTutorConnectorTracking, { passive: true });
        node.addEventListener("pointercancel", stopTutorConnectorTracking, { passive: true });
        node.addEventListener("wheel", redrawTutorConnectorsImmediate, { passive: true });
    });

    window.addEventListener("pointerup", stopTutorConnectorTracking, { passive: true });
    window.addEventListener("pointercancel", stopTutorConnectorTracking, { passive: true });
}

function getTutorVisualizerOptions() {
    const stageWidth = el.tutorStage?.clientWidth || el.flowPanel?.clientWidth || 960;
    const stageHeight = el.tutorStage?.clientHeight || el.flowPanel?.clientHeight || 650;
    return {
        embeddedMode: false,
        verticalStack: false,
        startingInstruction: 0,
        codeDivWidth: Math.max(560, Math.round(stageWidth * 0.42)),
        codeDivHeight: Math.max(560, Math.round(stageHeight * 0.88)),
    };
}

function reflowTutorVisualizer() {
    if (!currentTutorVisualizer) return;
    queueTutorConnectorRedraw();
    window.requestAnimationFrame(() => {
        queueTutorConnectorRedraw();
    });
}

function bindTutorStepSync() {
    const visualizer = currentTutorVisualizer;
    if (!visualizer || visualizer.__deepTracerStepBound) return;
    visualizer.__deepTracerStepBound = true;
    const originalRenderStep = visualizer.renderStep;
    if (typeof originalRenderStep !== "function") return;
    visualizer.renderStep = function patchedRenderStep(step, ...args) {
        const result = originalRenderStep.call(this, step, ...args);
        publishTutorStep(step);
        return result;
    };
    if (Number.isFinite(visualizer.curInstr)) {
        publishTutorStep(visualizer.curInstr);
    }
}

function publishTutorStep(step) {
    const visualizer = currentTutorVisualizer;
    const trace = visualizer?.curTrace || [];
    const entry = trace[step];
    if (!entry?.line) return;
    state.tutorLastStep = {
        step,
        line: entry.line,
        event: entry.event || ""
    };
    const activeMoment = state.tutorMoments.find(
        moment =>
            moment.step_index !== null &&
            moment.step_index !== undefined &&
            Number(moment.step_index) === step
    );
    state.activeTutorMomentId = activeMoment ? activeMoment.id : null;
    updateTutorMomentActiveState();
    const sourceRef = {
        fileId: state.fileId || "editor",
        sourceHash: currentSourceHash(),
        startLine: entry.line,
        endLine: entry.line,
        symbol: entry.func_name || entry.event || null,
        origin: "tutor",
        stepIndex: step
    };
    const located = revealSource(sourceRef, {
        switchPage: false,
        focus: false,
        reason: `Python Tutor 第 ${step} 步`
    });
    if (located) {
        syncTraceToTutorLine(entry.line);
    }
}

function clearTutorMoments() {
    state.tutorMoments = [];
    state.activeTutorMomentId = null;
    window.clearTimeout(state.tutorMomentEnrichTimer);
    state.tutorMomentEnrichRequest += 1;
    if (el.pythonMomentSource) {
        el.pythonMomentSource.textContent = "本地规则";
    }
    renderTutorMomentRail();
}

function renderTutorMomentRail() {
    if (!el.pythonMomentRail) return;
    if (!state.tutorMomentsEnabled) {
        el.pythonMomentRail.hidden = false;
        el.pythonMomentCount.textContent = "已关闭";
        el.pythonMomentList.replaceChildren();
        return;
    }
    const moments = state.tutorMoments.filter(moment => moment && moment.id);
    el.pythonMomentRail.hidden = moments.length === 0;
    el.pythonMomentCount.textContent = moments.length ? `${moments.length} 个` : "";
    if (!moments.length) {
        el.pythonMomentList.replaceChildren();
        return;
    }
    const fragment = document.createDocumentFragment();
    moments.forEach(moment => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = `moment-card moment-card--${moment.severity || "info"}`;
        card.dataset.momentId = moment.id;
        card.title = moment.why || moment.label || "";
        if (moment.id === state.activeTutorMomentId) {
            card.classList.add("is-active");
        }
        const label = document.createElement("span");
        label.className = "moment-card__label";
        label.textContent = moment.label || "关键瞬间";
        const why = document.createElement("span");
        why.className = "moment-card__why";
        why.textContent = moment.why || "";
        const meta = document.createElement("span");
        meta.className = "moment-card__meta";
        const hasLine =
            moment.line !== null &&
            moment.line !== undefined &&
            Number.isFinite(Number(moment.line));
        const hasStep =
            moment.step_index !== null &&
            moment.step_index !== undefined &&
            Number.isFinite(Number(moment.step_index));
        meta.textContent = [
            hasLine ? `第 ${Number(moment.line)} 行` : "",
            hasStep ? `第 ${Number(moment.step_index) + 1} 步` : ""
        ].filter(Boolean).join(" · ");
        card.append(label, why, meta);
        card.addEventListener("click", () => {
            if (hasStep) {
                jumpToTutorStep(Number(moment.step_index));
            }
            state.activeTutorMomentId = moment.id;
            updateTutorMomentActiveState();
        });
        fragment.appendChild(card);
    });
    el.pythonMomentList.replaceChildren(fragment);
}

function updateTutorMomentActiveState() {
    if (!el.pythonMomentList) return;
    el.pythonMomentList.querySelectorAll(".moment-card").forEach(card => {
        card.classList.toggle(
            "is-active",
            card.dataset.momentId === state.activeTutorMomentId
        );
    });
}

function jumpToTutorStep(index) {
    const visualizer = currentTutorVisualizer;
    if (!visualizer) return;
    const trace = visualizer.curTrace || [];
    if (!trace.length) return;
    const safeIndex = Math.max(0, Math.min(trace.length - 1, Number(index)));
    if (!Number.isFinite(safeIndex)) return;
    if (typeof visualizer.renderStep === "function") {
        visualizer.renderStep(safeIndex);
    } else if (Number.isFinite(visualizer.curInstr)) {
        visualizer.curInstr = safeIndex;
    }
}

function nextTutorMoment() {
    const moments = state.tutorMoments.filter(moment => moment && moment.id);
    if (!moments.length) return;
    const currentIndex = moments.findIndex(
        moment => moment.id === state.activeTutorMomentId
    );
    const next = moments[(currentIndex + 1) % moments.length];
    if (next.step_index !== null && next.step_index !== undefined) {
        const stepIndex = Number(next.step_index);
        if (Number.isFinite(stepIndex)) {
            jumpToTutorStep(stepIndex);
        }
    }
    state.activeTutorMomentId = next.id;
    updateTutorMomentActiveState();
}

function scheduleTutorMomentEnrichment() {
    window.clearTimeout(state.tutorMomentEnrichTimer);
    if (!state.tutorMomentsEnabled || !state.tutorMoments.length) return;
    const requestId = state.tutorMomentEnrichRequest;
    state.tutorMomentEnrichTimer = window.setTimeout(() => {
        void enrichTutorMoments(requestId);
    }, 800);
}

async function enrichTutorMoments(requestId) {
    if (requestId !== state.tutorMomentEnrichRequest || !state.tutorMoments.length) {
        return;
    }
    try {
        const response = await fetch("/api/breakpoints/enrich", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                world: "python",
                code: state.analyzedCode || el.sourceCode.value,
                moments: state.tutorMoments
            })
        });
        if (!response.ok) return;
        const payload = await response.json();
        if (requestId !== state.tutorMomentEnrichRequest) return;
        const enriched = Array.isArray(payload.moments) ? payload.moments : [];
        if (!enriched.some(moment => moment && moment.enriched)) return;
        const byId = new Map(
            enriched
                .filter(moment => moment && moment.id)
                .map(moment => [moment.id, moment])
        );
        state.tutorMoments = state.tutorMoments.map(moment => {
            const update = byId.get(moment.id);
            if (!update) return moment;
            return {
                ...moment,
                label: update.label || moment.label,
                why: update.why || moment.why,
                question: update.question ?? moment.question,
                importance: Number.isFinite(Number(update.importance))
                    ? Number(update.importance)
                    : moment.importance,
                enriched: Boolean(update.enriched)
            };
        });
        if (el.pythonMomentSource) {
            el.pythonMomentSource.textContent = "本地规则 + AI 文案";
        }
        renderTutorMomentRail();
    } catch (error) {
        // Keep rule-based copy when the optional enrichment fails.
    }
}

function findDeepestTraceNodeForLine(nodes, line) {
    let best = null;
    const visit = (node) => {
        const sourceRef = node.definitionRef || node.sourceRef;
        if (
            sourceRef?.startLine &&
            line >= Number(sourceRef.startLine) &&
            line <= Number(sourceRef.endLine || sourceRef.startLine)
        ) {
            if (
                !best ||
                Number(sourceRef.endLine || sourceRef.startLine) -
                    Number(sourceRef.startLine) <
                    Number(
                        (best.definitionRef || best.sourceRef).endLine ||
                        (best.definitionRef || best.sourceRef).startLine
                    ) -
                    Number((best.definitionRef || best.sourceRef).startLine)
            ) {
                best = node;
            }
        }
        (node.children || []).forEach(visit);
    };
    (nodes || []).forEach(visit);
    return best;
}

function syncTraceToTutorLine(line) {
    if (!el.traceTreeView || !state.traceResult?.traceTree) return;
    el.traceTreeView.querySelectorAll(".trace-node.is-source-active").forEach(node => {
        node.classList.remove("is-source-active");
    });
    const match = findDeepestTraceNodeForLine(state.traceResult.traceTree, line);
    if (!match?.id) return;
    const details = document.getElementById(match.id);
    if (!details) return;
    let parent = details.parentElement?.closest("details.trace-node");
    while (parent) {
        parent.open = true;
        parent = parent.parentElement?.closest("details.trace-node");
    }
    details.open = true;
    details.classList.add("is-source-active");
    const paneBounds = el.traceTreeView.getBoundingClientRect();
    const nodeBounds = details.getBoundingClientRect();
    if (nodeBounds.top < paneBounds.top || nodeBounds.bottom > paneBounds.bottom) {
        el.traceTreeView.scrollTop += nodeBounds.top - paneBounds.top - 20;
    }
}

// 拖拽调节大小
function initResizeHandler() {
    const handle = el.resizeHandle;
    const codePanel = el.codePanel;
    const flowPanel = el.flowPanel;
    
    if (!handle || !codePanel || !flowPanel) return;
    
    handle.addEventListener("mousedown", (e) => {
        isResizing = true;
        handle.classList.add("resizing");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
    });
    
    document.addEventListener("mousemove", (e) => {
        if (!isResizing) return;
        
        const viewport = document.querySelector(".code-layout-viewport");
        const codeLayout = document.querySelector(".code-layout");
        if (!viewport || !codeLayout) return;

        const viewportRect = viewport.getBoundingClientRect();
        const pointerOffset = e.clientX - viewportRect.left + viewport.scrollLeft;
        const totalVisibleWidth = viewport.clientWidth;
        const maxCodeWidth = Math.max(
            CODE_PANE_MIN_WIDTH,
            totalVisibleWidth - RESIZE_HANDLE_WIDTH - FLOW_PANE_MIN_WIDTH
        );
        const codeWidth = Math.max(
            CODE_PANE_MIN_WIDTH,
            Math.min(pointerOffset, maxCodeWidth)
        );
        const flowWidth = Math.max(
            FLOW_PANE_MIN_WIDTH,
            totalVisibleWidth - RESIZE_HANDLE_WIDTH - codeWidth
        );

        applyCodeLayout(
            `${Math.round(codeWidth)}px ${RESIZE_HANDLE_WIDTH}px ${Math.round(flowWidth)}px`,
            { manual: true }
        );
        queueTutorConnectorRedraw();
    });
    
    document.addEventListener("mouseup", () => {
        if (isResizing) {
            isResizing = false;
            handle.classList.remove("resizing");
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
            reflowTutorVisualizer();
        }
    });
}

function resetEditWorkspace() {
    state.sourceHash = "";
    state.fileId = "editor";
    state.currentDiff = null;
    state.expandedDiffRanges = new Set();
    state.editHistory = [];
    state.patchPlans = new Map();
    state.patchErrors = new Map();
    state.patchBusySuggestion = "";
    state.verificationResult = null;
    state.isEditing = false;
    state.hasUnsavedChanges = false;
    el.sourceCode.hidden = false;
    el.diffViewer.hidden = true;
    el.verificationPanel.hidden = true;
    el.verificationPanel.innerHTML = "";
    el.sourceFocusStatus.textContent = "";
    el.saveEdit.hidden = true;
    el.cancelEdit.hidden = true;
    updateRollbackButton();
}

// 载入示例代码
function loadSample() {
    resetEditWorkspace();
    el.sourceCode.value = sampleCode;
    state.currentFileName = "内置示例 · 临时副本";
    state.currentCode = sampleCode;
    state.originalCode = sampleCode;
    state.isBuiltInSample = true;
    state.analyzedCode = "";
    resetTraceWorkspace(false);
    resetTerminalOutput();
    updateLineNumbers();
    el.fileName.textContent = state.currentFileName;
    el.editStatus.textContent = "内置示例 · 修改仅在本次打开期间保留";
    resetChatState("示例副本已载入。可以编辑和测试；重新载入示例或刷新页面会恢复原始代码。");
    
    // 显示导航栏
    if (el.navbar) el.navbar.hidden = false;
    
    applyDefaultCodeLayout(true);
    switchToPage("code");
}

// 清空代码
function clearCode() {
    abortActiveChat("");
    resetEditWorkspace();
    el.sourceCode.value = "";
    state.currentFileName = "未命名";
    state.currentCode = "";
    state.originalCode = "";
    state.isBuiltInSample = false;
    state.analyzedCode = "";
    resetTraceWorkspace(false);
    resetTerminalOutput();
    updateLineNumbers();
    el.fileName.textContent = state.currentFileName;
    resetTutorSurface();
    resetChatState("输入区已清空。重新输入代码后，可以继续提问。");
}

// 处理文件选择
async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith(".py")) {
        alert("请选择 Python 文件（.py 后缀）");
        return;
    }
    
    try {
        const reader = new FileReader();
        reader.onload = function(e) {
            const content = e.target.result;
            resetEditWorkspace();
            el.sourceCode.value = content;
            state.currentFileName = file.name;
            state.currentCode = content;
            state.originalCode = content;
            state.isBuiltInSample = false;
            state.analyzedCode = "";
            resetTraceWorkspace(false);
            resetTerminalOutput();
            updateLineNumbers();
            el.fileName.textContent = state.currentFileName;
            
            // 显示导航栏
            if (el.navbar) el.navbar.hidden = false;
            
            applyDefaultCodeLayout(true);
            switchToPage("code");
        };
        reader.onerror = function() {
            alert("文件读取失败，请重试");
        };
        reader.readAsText(file, "utf-8");
    } catch (error) {
        console.error(error);
        alert(`文件读取失败：${error.message}`);
    }
    
    event.target.value = "";
}

// 显示加载动画
function showLoading(step = 0) {
    state.loading = true;
    state.loadingStep = step;
    el.loadingOverlay.hidden = false;
    el.loadingText.textContent = loadingCopies[step % loadingCopies.length];
    document.body.classList.add("is-loading");
}

// 隐藏加载动画
function hideLoading() {
    state.loading = false;
    el.loadingOverlay.hidden = true;
    document.body.classList.remove("is-loading");
}

// 启用编辑模式
function enableEditMode() {
    state.isEditing = true;
    el.sourceCode.readOnly = false;
    el.sourceCode.hidden = false;
    el.diffViewer.hidden = true;
    el.editCode.hidden = true;
    el.saveEdit.hidden = false;
    el.cancelEdit.hidden = false;
    el.editStatus.textContent = "编辑中...";
    el.sourceCode.focus();
}

// 取消编辑
function cancelEditMode() {
    state.isEditing = false;
    state.hasUnsavedChanges = false;
    el.sourceCode.value = state.originalCode;
    el.sourceCode.readOnly = true;
    el.sourceCode.hidden = false;
    el.diffViewer.hidden = true;
    el.editCode.hidden = false;
    el.saveEdit.hidden = true;
    el.cancelEdit.hidden = true;
    el.editStatus.textContent = state.isBuiltInSample
        ? "内置示例 · 修改仅在本次打开期间保留"
        : "";
    state.sourceHash = dataStore.meta?.sourceHash || "";
    updateLineNumbers();
}

// 保存编辑
function saveEdit() {
    const newCode = el.sourceCode.value;
    if (newCode === state.originalCode) {
        cancelEditMode();
        return;
    }

    pushEditSnapshot("手动编辑", state.originalCode);
    state.currentCode = newCode;
    state.hasUnsavedChanges = true;
    resetTraceWorkspace(false);
    
    // 显示 Diff
    showDiff(state.originalCode, newCode);
    
    state.isEditing = false;
    el.sourceCode.hidden = true;
    el.diffViewer.hidden = false;
    el.editCode.hidden = true;
    el.saveEdit.hidden = true;
    el.cancelEdit.hidden = false;
    el.editStatus.textContent = state.isBuiltInSample
        ? "内置示例副本已修改 · 重载示例可恢复原文"
        : "已修改（未保存分析）";
}

function rollbackLastEdit() {
    const snapshot = state.editHistory.pop();
    if (!snapshot) return;
    dataStore = deepClone(snapshot.dataStore || dataStore);
    state.sourceHash = snapshot.sourceHash || dataStore.meta?.sourceHash || "";
    state.latestAnalysisTaskId = snapshot.latestAnalysisTaskId || null;
    state.traceResult = snapshot.traceResult ? deepClone(snapshot.traceResult) : null;
    state.traceSelectedFunctions = new Set(snapshot.traceSelectedFunctions || []);
    state.terminalOutputCode = snapshot.terminalOutputCode || "";
    state.currentCode = snapshot.code;
    state.originalCode = snapshot.code;
    state.analyzedCode = snapshot.code;
    state.hasUnsavedChanges = false;
    state.verificationResult = null;
    el.sourceCode.value = snapshot.code;
    el.sourceCode.readOnly = true;
    el.sourceCode.hidden = false;
    el.diffViewer.hidden = true;
    el.verificationPanel.hidden = true;
    el.verificationPanel.innerHTML = "";
    el.sourceFocusStatus.textContent = "";
    el.editCode.hidden = false;
    el.saveEdit.hidden = true;
    el.cancelEdit.hidden = true;
    el.editStatus.textContent = `已回滚：${snapshot.label || "最近修改"}`;
    updateLineNumbers();
    updateRollbackButton();
    renderAll();
    switchToPage("code");
}

// 显示 Diff 对比
function showDiff(oldCode, newCode, { afterHash = "" } = {}) {
    if (el.verificationPanel) {
        el.verificationPanel.hidden = true;
        el.verificationPanel.innerHTML = "";
    }
    const oldLines = oldCode.split("\n");
    const newLines = newCode.split("\n");
    const diff = computeSimpleDiff(oldLines, newLines);
    state.currentDiff = { oldCode, newCode, afterHash, diff };
    state.expandedDiffRanges = new Set();
    renderDiffView();
}

function renderDiffView() {
    if (!state.currentDiff) return;
    const { diff } = state.currentDiff;
    const added = diff.filter(line => line.type === "added").length;
    const removed = diff.filter(line => line.type === "removed").length;
    const viewLabel = state.diffMode === "split" ? "并排 Diff" : "统一 Diff";
    const controls = `
        <div class="diff-actions">
            <button class="text-button" type="button" data-diff-action="toggle-mode">
                切换为${state.diffMode === "split" ? "统一" : "并排"}
            </button>
            ${state.editHistory.length
                ? '<button class="text-button danger-text" type="button" data-diff-action="rollback">回滚最近修改</button>'
                : ""}
        </div>
    `;
    const displayRows = buildDiffHunks(
        diff,
        3,
        state.expandedDiffRanges
    );

    const unifiedHtml = displayRows.map(line => line.type === "collapsed" ? `
        <button class="diff-collapsed" type="button"
            data-diff-action="expand"
            data-diff-range="${line.start}:${line.end}">
            <span>···</span>
            <span>展开 ${line.skipped} 行未修改内容</span>
        </button>
    ` : `
        <div class="diff-line ${line.type}">
            <span class="diff-old-num">${line.oldLine ?? ""}</span>
            <span class="diff-new-num">${line.newLine ?? ""}</span>
            <span class="diff-marker">${line.marker}</span>
            <code class="diff-content">${escapeHtml(line.content)}</code>
        </div>
    `).join("");

    const splitHtml = state.diffMode === "split"
        ? buildSplitDiffRows(displayRows).map(line => {
            if (line.type === "collapsed") {
                return `
                    <button class="diff-collapsed split-collapsed" type="button"
                        data-diff-action="expand"
                        data-diff-range="${line.start}:${line.end}">
                        展开 ${line.skipped} 行未修改内容
                    </button>
                `;
            }
            return renderSplitDiffPair(line.left, line.right);
        }).join("")
        : "";

    el.diffViewer.innerHTML = `
        <div class="diff-header">
            <div>
                <strong>${viewLabel}</strong>
                <span class="diff-stats">
                    <span class="diff-added-count">+${added}</span>
                    <span class="diff-removed-count">-${removed}</span>
                </span>
            </div>
            ${controls}
        </div>
        ${state.diffMode === "split" ? `
            <div class="diff-split-head">
                <span>修改前</span>
                <span>修改后</span>
            </div>
            <div class="diff-split">${splitHtml}</div>
        ` : `
            <div class="diff-column-head">
                <span>旧版本</span>
                <span>新版本</span>
                <span></span>
                <span>代码</span>
            </div>
            ${unifiedHtml}
        `}
    `;
}

function buildDiffHunks(diff, context = 3, expandedRanges = new Set()) {
    const changed = [];
    diff.forEach((line, index) => {
        if (line.type !== "unchanged") changed.push(index);
    });
    if (!changed.length) return diff;

    const ranges = [];
    for (const index of changed) {
        const start = Math.max(0, index - context);
        const end = Math.min(diff.length, index + context + 1);
        const previous = ranges[ranges.length - 1];
        if (previous && start <= previous.end) {
            previous.end = Math.max(previous.end, end);
        } else {
            ranges.push({ start, end });
        }
    }

    const rows = [];
    let cursor = 0;
    for (const range of ranges) {
        if (range.start > cursor) {
            const collapsed = {
                type: "collapsed",
                start: cursor,
                end: range.start,
                skipped: range.start - cursor
            };
            if (expandedRanges.has(`${collapsed.start}:${collapsed.end}`)) {
                rows.push(...diff.slice(collapsed.start, collapsed.end));
            } else {
                rows.push(collapsed);
            }
        }
        rows.push(...diff.slice(range.start, range.end));
        cursor = range.end;
    }
    if (cursor < diff.length) {
        const collapsed = {
            type: "collapsed",
            start: cursor,
            end: diff.length,
            skipped: diff.length - cursor
        };
        if (expandedRanges.has(`${collapsed.start}:${collapsed.end}`)) {
            rows.push(...diff.slice(collapsed.start, collapsed.end));
        } else {
            rows.push(collapsed);
        }
    }
    return rows;
}

function buildSplitDiffRows(displayRows) {
    const rows = [];
    let index = 0;
    while (index < displayRows.length) {
        const line = displayRows[index];
        if (line.type === "collapsed") {
            rows.push(line);
            index += 1;
            continue;
        }
        if (line.type === "unchanged") {
            rows.push({ type: "unchanged", left: line, right: line });
            index += 1;
            continue;
        }
        const removed = [];
        const added = [];
        while (index < displayRows.length && displayRows[index].type === "removed") {
            removed.push(displayRows[index]);
            index += 1;
        }
        while (index < displayRows.length && displayRows[index].type === "added") {
            added.push(displayRows[index]);
            index += 1;
        }
        const pairCount = Math.max(removed.length, added.length);
        for (let pairIndex = 0; pairIndex < pairCount; pairIndex += 1) {
            rows.push({
                type: "changed",
                left: removed[pairIndex] || null,
                right: added[pairIndex] || null
            });
        }
    }
    return rows;
}

function renderSplitDiffPair(left, right) {
    const leftCell = left
        ? `
            <div class="diff-split-cell removed">
                <span class="diff-old-num">${left.oldLine}</span>
                <code>${escapeHtml(left.content)}</code>
            </div>
        `
        : '<div class="diff-split-cell empty"></div>';
    const rightCell = right
        ? `
            <div class="diff-split-cell added">
                <span class="diff-new-num">${right.newLine}</span>
                <code>${escapeHtml(right.content)}</code>
            </div>
        `
        : '<div class="diff-split-cell empty"></div>';
    if (left?.type === "unchanged" && right?.type === "unchanged") {
        return `
            <div class="diff-split-row unchanged">
                <div class="diff-split-cell">
                    <span class="diff-old-num">${left.oldLine}</span>
                    <code>${escapeHtml(left.content)}</code>
                </div>
                <div class="diff-split-cell">
                    <span class="diff-new-num">${right.newLine}</span>
                    <code>${escapeHtml(right.content)}</code>
                </div>
            </div>
        `;
    }
    return `
        <div class="diff-split-row changed">
            ${leftCell}
            ${rightCell}
        </div>
    `;
}

// 基于最长公共子序列的行级 Diff；大文件使用前后缀压缩回退。
function computeSimpleDiff(oldLines, newLines) {
    if (oldLines.length * newLines.length > 4_000_000) {
        return computeCompressedDiff(oldLines, newLines);
    }

    const rows = oldLines.length;
    const cols = newLines.length;
    const lcs = Array.from({ length: rows + 1 }, () => new Uint32Array(cols + 1));
    for (let i = rows - 1; i >= 0; i--) {
        for (let j = cols - 1; j >= 0; j--) {
            lcs[i][j] = oldLines[i] === newLines[j]
                ? lcs[i + 1][j + 1] + 1
                : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
        }
    }

    const result = [];
    let oldIndex = 0;
    let newIndex = 0;
    while (oldIndex < rows && newIndex < cols) {
        if (oldLines[oldIndex] === newLines[newIndex]) {
            result.push({
                type: "unchanged",
                marker: " ",
                content: oldLines[oldIndex],
                lineNum: oldIndex + 1,
                oldLine: oldIndex + 1,
                newLine: newIndex + 1
            });
            oldIndex += 1;
            newIndex += 1;
        } else if (lcs[oldIndex + 1][newIndex] >= lcs[oldIndex][newIndex + 1]) {
            result.push({
                type: "removed",
                marker: "-",
                content: oldLines[oldIndex],
                lineNum: oldIndex + 1,
                oldLine: oldIndex + 1,
                newLine: null
            });
            oldIndex += 1;
        } else {
            result.push({
                type: "added",
                marker: "+",
                content: newLines[newIndex],
                lineNum: newIndex + 1,
                oldLine: null,
                newLine: newIndex + 1
            });
            newIndex += 1;
        }
    }

    while (oldIndex < rows) {
        result.push({
            type: "removed",
            marker: "-",
            content: oldLines[oldIndex],
            lineNum: oldIndex + 1,
            oldLine: oldIndex + 1,
            newLine: null
        });
        oldIndex += 1;
    }
    while (newIndex < cols) {
        result.push({
            type: "added",
            marker: "+",
            content: newLines[newIndex],
            lineNum: newIndex + 1,
            oldLine: null,
            newLine: newIndex + 1
        });
        newIndex += 1;
    }
    return result;
}

function computeCompressedDiff(oldLines, newLines) {
    let prefix = 0;
    while (
        prefix < oldLines.length &&
        prefix < newLines.length &&
        oldLines[prefix] === newLines[prefix]
    ) {
        prefix += 1;
    }
    let oldEnd = oldLines.length - 1;
    let newEnd = newLines.length - 1;
    while (
        oldEnd >= prefix &&
        newEnd >= prefix &&
        oldLines[oldEnd] === newLines[newEnd]
    ) {
        oldEnd -= 1;
        newEnd -= 1;
    }

    const result = [];
    for (let i = 0; i < prefix; i++) {
        result.push({
            type: "unchanged",
            marker: " ",
            content: oldLines[i],
            lineNum: i + 1,
            oldLine: i + 1,
            newLine: i + 1
        });
    }
    for (let i = prefix; i <= oldEnd; i++) {
        result.push({
            type: "removed",
            marker: "-",
            content: oldLines[i],
            lineNum: i + 1,
            oldLine: i + 1,
            newLine: null
        });
    }
    for (let i = prefix; i <= newEnd; i++) {
        result.push({
            type: "added",
            marker: "+",
            content: newLines[i],
            lineNum: i + 1,
            oldLine: null,
            newLine: i + 1
        });
    }
    const suffixLength = oldLines.length - oldEnd - 1;
    for (let offset = 0; offset < suffixLength; offset++) {
        const oldLineIndex = oldEnd + 1 + offset;
        const newLineIndex = newEnd + 1 + offset;
        result.push({
            type: "unchanged",
            marker: " ",
            content: oldLines[oldLineIndex],
            lineNum: oldLineIndex + 1,
            oldLine: oldLineIndex + 1,
            newLine: newLineIndex + 1
        });
    }
    return result;
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// 复制代码
async function copyCode() {
    const code = el.sourceCode.value || state.currentCode;
    try {
        await navigator.clipboard.writeText(code);
        el.editStatus.textContent = "✅ 已复制到剪贴板";
        setTimeout(() => {
            el.editStatus.textContent = state.hasUnsavedChanges ? "已修改（未保存分析）" : "";
        }, 2000);
    } catch (error) {
        console.error("复制失败:", error);
        el.editStatus.textContent = "❌ 复制失败";
    }
}

// 完成分析后的处理
function finishAnalysis(code) {
    state.originalCode = code;
    state.analyzedCode = code;
    state.currentCode = code;
    state.hasUnsavedChanges = false;
    state.isEditing = false;
    state.patchPlans.clear();
    state.patchErrors.clear();
    state.currentDiff = null;
    state.expandedDiffRanges = new Set();
    el.sourceCode.value = code;
    el.sourceCode.readOnly = true;
    el.sourceCode.hidden = false;
    el.diffViewer.hidden = true;
    el.verificationPanel.hidden = true;
    el.verificationPanel.innerHTML = "";
    el.editCode.hidden = false;
    el.saveEdit.hidden = true;
    el.cancelEdit.hidden = true;
    el.editStatus.textContent = state.isBuiltInSample
        ? "内置示例 · 修改仅在本次打开期间保留"
        : "";
    updateLineNumbers();
    updateRollbackButton();
}

// 加载 pytutor 可视化
async function loadTutorVisualization(code) {
    if (!code || !window.addVisualizerToPage) return;

    state.tutorMomentEnrichRequest += 1;
    window.clearTimeout(state.tutorMomentEnrichTimer);
    state.tutorMoments = [];
    state.activeTutorMomentId = null;
    renderTutorMomentRail();

    try {
        const response = await fetch("/api/tutor/trace", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: code })
        });
        
        if (!response.ok) return;
        
        const payload = await response.json();
        if (payload.error) return;
        
        // 隐藏 placeholder，显示可视化
        el.tutorPlaceholder.hidden = true;
        el.tutorVisualizerMount.hidden = false;
        el.tutorVisualizerMount.innerHTML = "";

        const tutorOptions = getTutorVisualizerOptions();
        currentTutorVisualizer = window.addVisualizerToPage(
            payload,
            "tutorVisualizerMount",
            tutorOptions
        );
        styleTutorVisualizer();
        bindTutorStepSync();
        state.tutorMoments = Array.isArray(payload.moments) ? payload.moments : [];
        if (el.pythonMomentSource) {
            el.pythonMomentSource.textContent = "本地规则";
        }
        const startStep = Number(currentTutorVisualizer?.curInstr);
        if (Number.isFinite(startStep)) {
            const activeMoment = state.tutorMoments.find(
                moment =>
                    moment.step_index !== null &&
                    moment.step_index !== undefined &&
                    Number(moment.step_index) === startStep
            );
            state.activeTutorMomentId = activeMoment ? activeMoment.id : null;
        }
        renderTutorMomentRail();
        scheduleTutorMomentEnrichment();
        queueTutorConnectorRedraw();
        window.setTimeout(reflowTutorVisualizer, 120);
        
        // 隐藏 placeholder 确保不会悬浮显示
        setTimeout(() => {
            if (el.tutorPlaceholder) {
                el.tutorPlaceholder.style.display = "none";
            }
        }, 100);
        
    } catch (error) {
        console.error("加载执行可视化失败:", error);
    }
}

// 运行分析
async function runAnalysis() {
    const code = el.sourceCode.value.trim();
    if (!code) {
        alert("请先输入或选择代码");
        return;
    }
    
    showLoading(0);
    
    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: code,
                path: state.currentFileName,
                displayName: currentDisplayName()
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const payload = await response.json();
        
        if (payload.error) {
            throw new Error(payload.error);
        }
        
        // 应用分析结果
        dataStore = {
            heroMetrics: payload.heroMetrics || deepClone(demoData.heroMetrics),
            analysisMap: payload.analysisMap || deepClone(demoData.analysisMap),
            suggestions: payload.suggestions || [],
            visualizations: payload.visualizations || { ast: "", performance: "" },
            runtimeBanner: payload.runtimeBanner || null,
            meta: payload.meta || {}
        };
        
        state.activeTab = "workflow";
        state.activeSuggestion = (dataStore.suggestions[0] && dataStore.suggestions[0].id) || null;
        state.latestAnalysisTaskId = payload.meta?.taskId || null;
        state.sourceHash = payload.meta?.sourceHash || "";
        state.fileId = payload.meta?.fileId || "editor";
        
        finishAnalysis(code);
        resetTraceWorkspace(true);
        hideLoading();
        renderAll();
        resetChatState("分析完成。现在可以继续追问这段代码为什么这样写、热点从哪里来、先改哪一步。");
        
        // 显示导航栏
        if (el.navbar) el.navbar.hidden = false;
        
        // 分析完成后进入工作台，默认先展示结果详情。
        switchToPage("analysis");
        setWorkspaceView("analysis");
        
        // 执行流程会再次运行用户代码，改为由用户显式点击“生成执行流程”。
        resetTutorSurface();
        
    } catch (error) {
        console.error(error);
        hideLoading();
        alert(`分析失败：${error.message}`);
    }
}

// 绑定事件
function bindEvents() {
    // 主题切换
    el.themeToggle.addEventListener("click", toggleTheme);
    
    // 导航切换
    el.navTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            switchToPage(tab.dataset.page);
        });
    });
    
    // 拖拽调节大小
    initResizeHandler();
    initTerminalEntry();
    ensurePartnerDock();

    // 文件选择
    el.selectFileBtn.addEventListener("click", () => {
        el.fileInput.click();
    });
    
    el.fileInput.addEventListener("change", handleFileSelect);
    
    el.loadSampleBtn.addEventListener("click", loadSample);
    
    // 拖放支持
    el.dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        el.dropZone.classList.add("drag-over");
    });
    
    el.dropZone.addEventListener("dragleave", () => {
        el.dropZone.classList.remove("drag-over");
    });
    
    el.dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        el.dropZone.classList.remove("drag-over");
        const file = e.dataTransfer.files[0];
        if (file && file.name.endsWith(".py")) {
            handleFileSelect({ target: { files: [file], value: "" } });
        }
    });
    
    // 代码编辑器
    el.sourceCode.addEventListener("input", () => {
        updateLineNumbers();
        state.sourceHash = "";
        if (state.analyzedCode && el.sourceCode.value.trim() !== state.analyzedCode) {
            state.latestAnalysisTaskId = null;
            setChatStatus("代码已修改，请重新分析后再继续追问。");
            if (state.traceResult || state.traceSelectedFunctions.size) {
                resetTraceWorkspace(false);
            }
        }
        if (state.terminalOutputCode && el.sourceCode.value.trim() !== state.terminalOutputCode) {
            el.terminalRunStatus.textContent = "代码已修改，请重新运行终端。";
        }
    });
    el.sourceCode.addEventListener("scroll", syncLineNumberScroll);
    
    // 代码页面操作
    el.reloadFile.addEventListener("click", () => {
        if (state.isBuiltInSample) {
            loadSample();
            return;
        }
        if (state.currentCode) {
            el.sourceCode.value = state.currentCode;
            updateLineNumbers();
        }
    });
    
    el.syncTutor.addEventListener("click", () => {
        const code = el.sourceCode.value.trim() || state.currentCode;
        loadTutorVisualization(code);
    });

    el.pythonMomentNext?.addEventListener("click", nextTutorMoment);
    el.pythonMomentToggle?.addEventListener("click", () => {
        state.tutorMomentsEnabled = !state.tutorMomentsEnabled;
        el.pythonMomentToggle.setAttribute(
            "aria-pressed",
            String(state.tutorMomentsEnabled)
        );
        el.pythonMomentToggle.textContent = state.tutorMomentsEnabled
            ? "智能断点"
            : "智能断点（关）";
        renderTutorMomentRail();
        if (state.tutorMomentsEnabled) scheduleTutorMomentEnrichment();
    });

    el.executionModeTabs.addEventListener("click", (event) => {
        const button = event.target.closest(".execution-mode-tab");
        if (!button) return;
        setExecutionMode(button.dataset.executionMode);
    });

    el.traceFunctionList.addEventListener("change", (event) => {
        const input = event.target.closest("[data-trace-function]");
        if (!input) return;
        const functionName = input.dataset.traceFunction;
        if (input.checked) {
            state.traceSelectedFunctions.add(functionName);
        } else {
            state.traceSelectedFunctions.delete(functionName);
        }
        state.traceResult = null;
        renderTraceResult();
        el.traceStatus.textContent = state.traceSelectedFunctions.size
            ? `已选择 ${state.traceSelectedFunctions.size} 个函数。`
            : "请选择至少一个函数，然后开始追踪。";
    });

    el.traceExceptions.addEventListener("change", () => {
        el.traceLocals.disabled = !el.traceExceptions.checked;
        if (!el.traceExceptions.checked) {
            el.traceLocals.checked = false;
        }
    });

    el.traceViewTabs.addEventListener("click", (event) => {
        const button = event.target.closest(".trace-view-tab");
        if (!button) return;
        setTraceView(button.dataset.traceView);
    });

    el.expandTraceTree.addEventListener("click", () => {
        el.traceTreeView.querySelectorAll("details.trace-node").forEach(node => {
            node.open = true;
        });
    });

    el.collapseTraceTree.addEventListener("click", () => {
        el.traceTreeView.querySelectorAll("details.trace-node").forEach(node => {
            node.open = false;
        });
    });
    el.traceTreeView.addEventListener("click", (event) => {
        const sourceButton = event.target.closest("[data-source-ref]");
        if (!sourceButton) return;
        event.preventDefault();
        event.stopPropagation();
        revealSourceFromElement(sourceButton);
    });

    el.runTracerTrace.addEventListener("click", runTracerTrace);
    el.runTerminalCode.addEventListener("click", runTerminalCode);

    el.backToCode.addEventListener("click", () => switchToPage("code"));
    el.openTracer.addEventListener("click", () => {
        switchToPage("code");
        setExecutionMode("tracer");
    });
    
    el.clearCode.addEventListener("click", clearCode);
    el.runAnalysis.addEventListener("click", runAnalysis);
    el.chatSend.addEventListener("click", sendChatMessage);
    el.chatStop.addEventListener("click", () => abortActiveChat("已停止当前回答。"));
    el.chatInput.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
            event.preventDefault();
            sendChatMessage();
        }
    });
    el.chatTranscript.addEventListener("click", (event) => {
        const button = event.target.closest("[data-code-token]");
        if (!button) return;
        copyChatCode(button.dataset.codeToken, button);
    });
    el.editCode.addEventListener("click", enableEditMode);
    el.saveEdit.addEventListener("click", saveEdit);
    el.cancelEdit.addEventListener("click", cancelEditMode);
    el.rollbackEdit.addEventListener("click", rollbackLastEdit);
    el.copyCode.addEventListener("click", copyCode);

    // 工作台一级视图
    el.workspaceTabs.addEventListener("click", (event) => {
        const button = event.target.closest(".workspace-tab");
        if (!button) return;
        setWorkspaceView(button.dataset.workspace);
    });

    // 分析结果标签页
    el.resultTabs.addEventListener("click", (e) => {
        const btn = e.target.closest(".tab-btn");
        if (!btn) return;
        
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state.activeTab = btn.dataset.tab;
        renderAnalysisTab();
    });

    el.tabBars.addEventListener("click", (e) => {
        const sourceJump = e.target.closest("[data-source-ref]");
        if (sourceJump) {
            e.preventDefault();
            e.stopPropagation();
            revealSourceFromElement(sourceJump);
            return;
        }
        const button = e.target.closest("[data-function-details]");
        if (!button) return;
        const shouldOpen = button.dataset.functionDetails === "expand";
        el.tabBars.querySelectorAll("details.function-signature-card").forEach(card => {
            card.open = shouldOpen;
        });
    });
    
    // 建议列表
    el.suggestionList.addEventListener("click", (e) => {
        const btn = e.target.closest(".suggestion-item");
        if (!btn) return;
        
        document.querySelectorAll(".suggestion-item").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state.activeSuggestion = btn.dataset.suggestion;
        renderSuggestions();
    });

    el.suggestionDetail.addEventListener("click", (event) => {
        const sourceJump = event.target.closest("[data-source-ref]");
        if (sourceJump) {
            event.preventDefault();
            revealSourceFromElement(sourceJump);
            return;
        }
        const action = event.target.closest("[data-suggestion-action]");
        if (!action) return;
        event.preventDefault();
        const suggestionId = action.dataset.suggestionId;
        if (action.dataset.suggestionAction === "generate-patch") {
            generateSuggestionPatch(suggestionId);
        } else if (action.dataset.suggestionAction === "apply-patch") {
            applySuggestionPatch(suggestionId);
        } else if (action.dataset.suggestionAction === "clear-patch") {
            state.patchPlans.delete(suggestionId);
            state.patchErrors.delete(suggestionId);
            renderSuggestionDetail();
        }
    });

    el.diffViewer.addEventListener("click", (event) => {
        const action = event.target.closest("[data-diff-action]");
        if (!action) return;
        if (action.dataset.diffAction === "toggle-mode") {
            state.diffMode = state.diffMode === "unified" ? "split" : "unified";
            renderDiffView();
        } else if (action.dataset.diffAction === "expand") {
            state.expandedDiffRanges.add(action.dataset.diffRange);
            renderDiffView();
        } else if (action.dataset.diffAction === "rollback") {
            rollbackLastEdit();
        }
    });
    
    // 可视化标签页
    el.vizTabs.addEventListener("click", (e) => {
        const btn = e.target.closest(".viz-tab");
        if (!btn) return;
        
        document.querySelectorAll(".viz-tab").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state.activeViz = btn.dataset.viz;
        
        el.astVizContent.hidden = btn.dataset.viz !== "ast";
        el.perfVizContent.hidden = btn.dataset.viz !== "performance";
    });
    el.perfVizContent.addEventListener("click", (event) => {
        const sourceJump = event.target.closest("[data-source-ref]");
        if (!sourceJump) return;
        revealSourceFromElement(sourceJump);
    });
}

// 初始化应用
function initApp() {
    initElements();
    
    // 检查关键元素是否存在
    if (!el.sourceCode || !el.navbar) {
        console.error("关键 DOM 元素未找到，请检查 HTML 结构");
        return;
    }
    
    setTheme(state.theme);
    setWorkspaceView(state.activeWorkspace);
    setExecutionMode(state.activeExecutionMode);
    setTraceView(state.traceActiveView);
    updateLineNumbers();
    bindEvents();
    applyDefaultCodeLayout(true);
    window.addEventListener("resize", () => {
        applyDefaultCodeLayout();
        queueTutorConnectorRedraw();
    });
    
    // 初始显示 HOME 页面
    switchToPage("home");
}

// DOM 加载完成后初始化
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}
