// DeepTracer - Modernized Multi-Page Architecture
const themes = ["mist", "paper", "night"];
const loadingCopies = [
    "像素猫正在巡检结构、性能和内存，请稍等一下。",
    "正在梳理函数之间的关系，马上给你结果。",
    "热点和内存摘要还在整理中，很快就好。",
    "正在生成更容易理解的修改建议。"
];

const sampleCode = `BOOKS = [
    {"title": "Python 起步", "topic": "python", "pages": 180, "level": "beginner", "borrowed": 8},
    {"title": "数据结构轻读", "topic": "algorithm", "pages": 240, "level": "intermediate", "borrowed": 5},
    {"title": "可视化故事", "topic": "data", "pages": 210, "level": "beginner", "borrowed": 7},
    {"title": "函数式思维", "topic": "python", "pages": 320, "level": "advanced", "borrowed": 3},
    {"title": "图解排序", "topic": "algorithm", "pages": 190, "level": "beginner", "borrowed": 6},
    {"title": "数据分析练习", "topic": "data", "pages": 280, "level": "intermediate", "borrowed": 4}
]


def score_book(book):
    score = book["borrowed"] * 2
    if book["level"] == "beginner":
        score += 3
    if book["pages"] < 220:
        score += 2
    return score


def find_titles_for_topic(books, topic):
    titles = []
    for book in books:
        if book["topic"] == topic:
            titles.append(book["title"])
    return titles


def build_topic_summary(books):
    summary = {}
    for book in books:
        topic = book["topic"]
        if topic not in summary:
            summary[topic] = {
                "count": 0,
                "pages": 0,
                "score": 0,
                "titles": find_titles_for_topic(books, topic)
            }
        summary[topic]["count"] += 1
        summary[topic]["pages"] += book["pages"]
        summary[topic]["score"] += score_book(book)
    return summary


def choose_focus_topic(summary):
    best_topic = ""
    best_score = -1
    for topic, info in summary.items():
        if info["score"] > best_score:
            best_topic = topic
            best_score = info["score"]
    return best_topic, summary[best_topic]


def explain_focus(topic, info):
    avg_pages = info["pages"] // info["count"]
    return {
        "topic": topic,
        "count": info["count"],
        "avg_pages": avg_pages,
        "titles": info["titles"]
    }


def main():
    summary = build_topic_summary(BOOKS)
    focus_topic, focus_info = choose_focus_topic(summary)
    result = explain_focus(focus_topic, focus_info)
    print("summary:", summary)
    print("focus:", result)


if __name__ == "__main__":
    main()
`;

const demoData = {
    heroMetrics: [
        { label: "分析对象", value: "示例代码", note: "可以直接替换成你自己的代码" },
        { label: "代码行数", value: "64", note: "输入框里的内容会参与分析" },
        { label: "重点函数", value: "build_topic_summary", note: "按结构复杂度排序" },
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
                { label: "函数数量", value: "6", note: "共 6 个函数定义" },
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
                { label: "热点函数", value: "build_topic_summary", note: "耗时占比最高" },
                { label: "循环次数", value: "12", note: "总共执行 12 次循环" },
                { label: "优化空间", value: "中等", note: "有优化可能" }
            ],
            points: [
                "整体性能表现良好。",
                "build_topic_summary 是主要耗时点。",
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
            id: "merge-loops",
            title: "合并重复循环",
            explanation: "build_topic_summary 中存在重复遍历，可以合并以减少循环次数。",
            priority: "高",
            confidence: "中",
            risk: "低",
            file: "当前代码",
            note: "合并循环可以减少遍历次数，提升性能。",
            diff: [
                [1, " ", "def build_topic_summary(books):"],
                [2, " ", "    summary = {}"],
                [3, "-", "    titles_map = {}"],
                [4, " ", "    for book in books:"],
                [5, " ", "        topic = book[\"topic\"]"],
                [6, "+", "        if topic not in summary:"],
                [7, "+", "            summary[topic] = {\"count\": 0, \"pages\": 0, \"score\": 0, \"titles\": []}"],
                [8, " ", "        summary[topic][\"count\"] += 1"]
            ]
        },
        {
            id: "use-dict-get",
            title: "使用 dict.get() 简化代码",
            explanation: "可以使用 dict.get() 方法简化字典访问逻辑。",
            priority: "中",
            confidence: "高",
            risk: "低",
            file: "当前代码",
            note: "简化字典访问，提高代码可读性。",
            diff: [
                [1, " ", "def choose_focus_topic(summary):"],
                [2, "-", "    best_topic = \"\""],
                [3, "-", "    best_score = -1"],
                [4, "+", "    best_topic, best_info = max(summary.items(), key=lambda x: x[1][\"score\"], default=(\"\", None))"],
                [5, "+", "    return best_topic, best_info or {\"score\": -1}"]
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
    activeTab: "workflow",
    activeSuggestion: demoData.suggestions[0].id,
    activeViz: "ast",
    loading: false,
    loadingStep: 0,
    currentFileName: "",
    currentCode: "",
    originalCode: "", // 分析前的原始代码
    isEditing: false,
    hasUnsavedChanges: false,
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
        copyCode: document.getElementById("copyCode"),
        diffViewer: document.getElementById("diffViewer"),
        syncTutor: document.getElementById("syncTutor"),
        tutorPlaceholder: document.getElementById("tutorPlaceholder"),
        tutorVisualizerMount: document.getElementById("tutorVisualizerMount"),
        tutorStage: document.querySelector(".tutor-stage"),
        
        // 分析结果页面
        runtimeBanner: document.getElementById("runtimeBanner"),
        summaryCards: document.getElementById("summaryCards"),
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
            <span>${m.label}</span>
            <strong>${m.value}</strong>
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
    
    el.tabSummary.innerHTML = `<h3>${tab.title || ""}</h3><p>${tab.summary || ""}</p>`;
    
    el.tabBars.innerHTML = (tab.cards || []).map(c => `
        <div class="chart-item">
            <div class="chart-meta">
                <span>${c.label}</span>
                <span>${c.value}</span>
            </div>
            <div class="chart-track">
                <div class="chart-fill" style="width: ${Math.min(100, parseInt(c.value) || 0)}%"></div>
            </div>
        </div>
    `).join("");
    
    el.tabPoints.innerHTML = (tab.points || []).map(p => `
        <div class="notes-item">${p}</div>
    `).join("");
}

// 渲染建议列表
function renderSuggestions() {
    const suggestions = dataStore.suggestions || [];
    el.suggestionList.innerHTML = suggestions.map(s => `
        <button class="suggestion-item ${s.id === state.activeSuggestion ? "is-active" : ""}" data-suggestion="${s.id}">
            <div class="suggestion-title">${s.title}</div>
            <div class="suggestion-meta">建议强度：${s.priority || "-"} · 置信度：${s.confidence || "-"} · 风险：${s.risk || "-"}</div>
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
    const anchorHtml = anchors.length
        ? `
            <div class="suggestion-anchor-list">
                ${anchors.map(anchor => `
                    <article class="suggestion-anchor">
                        <div class="suggestion-anchor-head">
                            <span class="suggestion-anchor-kind">${escapeHtml(anchor.kind || "anchor")}</span>
                            <strong>${escapeHtml(anchor.label || "未命名位置")}</strong>
                            ${anchor.line ? `<span class="suggestion-anchor-line">第 ${anchor.line} 行</span>` : ""}
                        </div>
                        ${anchor.snippet ? `<pre class="suggestion-anchor-snippet"><code>${escapeHtml(anchor.snippet)}</code></pre>` : ""}
                    </article>
                `).join("")}
            </div>
        `
        : '<div class="suggestion-empty">当前没有可展示的代码锚点。</div>';

    el.suggestionDetail.innerHTML = `
        <h3>${suggestion.title}</h3>
        <p>${suggestion.explanation || ""}</p>
        <div class="suggestion-meta">建议强度：${suggestion.priority || "-"} · 置信度：${suggestion.confidence || "-"} · 风险：${suggestion.risk || "-"}</div>
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
        el.astVizContent.innerHTML = "";
        el.astVizContent.appendChild(iframe);
        
        iframe.contentWindow.document.open();
        iframe.contentWindow.document.write(sanitizeVisualizationHtml(viz.ast));
        iframe.contentWindow.document.close();
    } else {
        el.astVizContent.innerHTML = '<p style="padding: 20px; text-align: center; color: var(--muted);">AST 可视化生成失败或不可用</p>';
    }
    
    // 渲染性能可视化
    if (viz.performance && viz.performance.trim().length > 0) {
        const iframe = document.createElement("iframe");
        iframe.style.width = "100%";
        iframe.style.height = "700px";
        iframe.style.border = "none";
        el.perfVizContent.innerHTML = "";
        el.perfVizContent.appendChild(iframe);
        
        iframe.contentWindow.document.open();
        iframe.contentWindow.document.write(sanitizeVisualizationHtml(viz.performance));
        iframe.contentWindow.document.close();
    } else {
        el.perfVizContent.innerHTML = '<p style="padding: 20px; text-align: center; color: var(--muted);">性能分析可视化生成失败或不可用</p>';
    }
}

// 渲染所有内容
function renderAll() {
    renderRuntimeBanner();
    renderSummaryCards();
    renderAnalysisTab();
    renderSuggestions();
    renderVisualizations();
    renderChatTranscript();
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

// 载入示例代码
function loadSample() {
    el.sourceCode.value = sampleCode;
    state.currentFileName = "示例代码";
    state.currentCode = sampleCode;
    updateLineNumbers();
    el.fileName.textContent = state.currentFileName;
    resetChatState("示例已载入。分析后你可以继续追问，也可以直接用这段代码开始对话。");
    
    // 显示导航栏
    if (el.navbar) el.navbar.hidden = false;
    
    applyDefaultCodeLayout(true);
    switchToPage("code");
}

// 清空代码
function clearCode() {
    abortActiveChat("");
    el.sourceCode.value = "";
    state.currentFileName = "未命名";
    state.currentCode = "";
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
            el.sourceCode.value = content;
            state.currentFileName = file.name;
            state.currentCode = content;
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
    el.editStatus.textContent = "";
    updateLineNumbers();
}

// 保存编辑
function saveEdit() {
    const newCode = el.sourceCode.value;
    if (newCode === state.originalCode) {
        cancelEditMode();
        return;
    }
    
    state.currentCode = newCode;
    state.hasUnsavedChanges = true;
    
    // 显示 Diff
    showDiff(state.originalCode, newCode);
    
    state.isEditing = false;
    el.sourceCode.hidden = true;
    el.diffViewer.hidden = false;
    el.editCode.hidden = true;
    el.saveEdit.hidden = true;
    el.cancelEdit.hidden = false;
    el.editStatus.textContent = "已修改（未保存分析）";
}

// 显示 Diff 对比
function showDiff(oldCode, newCode) {
    const oldLines = oldCode.split("\n");
    const newLines = newCode.split("\n");
    
    // 简单的 Diff 算法
    const diff = computeSimpleDiff(oldLines, newLines);
    
    el.diffViewer.innerHTML = `
        <div class="diff-header">
            📝 代码对比（红色：删除，绿色：添加）
        </div>
        ${diff.map(line => `
            <div class="diff-line ${line.type}">
                <span class="line-num">${line.lineNum}</span>
                <span class="diff-marker">${line.marker}</span>
                <span class="diff-content">${escapeHtml(line.content)}</span>
            </div>
        `).join("")}
    `;
}

// 简单的 Diff 计算
function computeSimpleDiff(oldLines, newLines) {
    const result = [];
    const maxLen = Math.max(oldLines.length, newLines.length);
    
    for (let i = 0; i < maxLen; i++) {
        const oldLine = oldLines[i] || "";
        const newLine = newLines[i] || "";
        
        if (oldLine === newLine) {
            result.push({
                type: "unchanged",
                marker: " ",
                content: oldLine,
                lineNum: i + 1
            });
        } else {
            if (oldLine) {
                result.push({
                    type: "removed",
                    marker: "-",
                    content: oldLine,
                    lineNum: i + 1
                });
            }
            if (newLine) {
                result.push({
                    type: "added",
                    marker: "+",
                    content: newLine,
                    lineNum: i + 1
                });
            }
        }
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
    state.hasUnsavedChanges = false;
    
    // 显示编辑按钮
    el.editCode.hidden = false;
    el.editStatus.textContent = "";
}

// 加载 pytutor 可视化
async function loadTutorVisualization(code) {
    if (!code || !window.addVisualizerToPage) return;
    
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
            suggestions: payload.suggestions && payload.suggestions.length ? payload.suggestions : deepClone(demoData.suggestions),
            visualizations: payload.visualizations || { ast: "", performance: "" },
            runtimeBanner: payload.runtimeBanner || null,
            meta: payload.meta || {}
        };
        
        state.activeTab = "workflow";
        state.activeSuggestion = (dataStore.suggestions[0] && dataStore.suggestions[0].id) || demoData.suggestions[0].id;
        state.latestAnalysisTaskId = payload.meta?.taskId || null;
        
        hideLoading();
        renderAll();
        resetChatState("分析完成。现在可以继续追问这段代码为什么这样写、热点从哪里来、先改哪一步。");
        
        // 显示导航栏
        if (el.navbar) el.navbar.hidden = false;
        
        // 停留在代码页面
        switchToPage("code");
        
        // 完成分析处理
        finishAnalysis(code);
        
        // 自动加载执行流程可视化
        loadTutorVisualization(code);
        
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
    el.sourceCode.addEventListener("input", updateLineNumbers);
    el.sourceCode.addEventListener("scroll", syncLineNumberScroll);
    
    // 代码页面操作
    document.getElementById("runAnalysis").addEventListener("click", runAnalysis);
    el.clearCode.addEventListener("click", clearCode);
    el.reloadFile.addEventListener("click", () => {
        if (state.currentCode) {
            el.sourceCode.value = state.currentCode;
            updateLineNumbers();
        }
    });
    
    el.syncTutor.addEventListener("click", () => {
        const code = el.sourceCode.value.trim() || state.currentCode;
        loadTutorVisualization(code);
    });
    
    // 代码页面操作
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
    el.copyCode.addEventListener("click", copyCode);
    el.clearCode.addEventListener("click", clearCode);
    
    // 分析结果标签页
    el.resultTabs.addEventListener("click", (e) => {
        const btn = e.target.closest(".tab-btn");
        if (!btn) return;
        
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state.activeTab = btn.dataset.tab;
        renderAnalysisTab();
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
