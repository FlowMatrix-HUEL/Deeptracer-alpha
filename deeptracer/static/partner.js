(function () {
    "use strict";

    const LOGO = [
        " ____                  _____",
        "|  _ \\  ___  ___ _ __ |_   _| __ __ _  ___ ___ _ __",
        "| | | |/ _ \\/ _ \\ '_ \\  | | '__/ _` |/ __/ _ \\ '__|",
        "| |_| |  __/  __/ |_) | | | | | (_| | (_|  __/ |",
        "|____/ \\___|\\___| .__/  |_|_|  \\__,_|\\___\\___|_|",
        "                |_|"
    ].join("\n");

    const MODE_LABELS = {
        ask: "提问",
        "co-investigate": "共查",
        challenge: "反驳",
        reflect: "复述"
    };

    const ACTION_LABELS = {
        evidence: "证据",
        highlight: "看这里",
        jump: "跳过去",
        run: "运行验证",
        propose_code: "示范片段",
        save_case: "保存档案"
    };

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = text;
        return node;
    }

    function createPartnerConsole(mount, options = {}) {
        if (!mount) {
            throw new Error("partner console mount is required");
        }

        const state = {
            workbench: options.workbench || "python",
            mode: "co-investigate",
            messages: [],
            streaming: false,
            controller: null,
            timeoutTimer: 0,
            hintLevel: "H1",
            sawProposeCode: false,
            lastUser: "",
            lastAssistant: "",
            memoryRoot: "",
            cases: [],
            logEl: null,
            inputEl: null,
            sendEl: null,
            statusEl: null,
            footEl: null
        };

        mount.innerHTML = "";
        const root = el("div", "partner-console" + (options.compact ? " partner-console--compact" : ""));
        root.innerHTML = `
            <div class="partner-head">
                <span class="partner-mark" aria-hidden="true"><i></i><i></i></span>
                <span class="partner-title">思辨伙伴</span>
                <span class="partner-status" data-role="status">本地 · 等待输入</span>
                <button type="button" data-role="memory">记忆</button>
                <button type="button" data-role="save">保存</button>
                <button type="button" data-role="clear">清空</button>
            </div>
            <div class="partner-modes" role="group" aria-label="思辨模式">
                <button type="button" data-mode="ask">提问</button>
                <button type="button" data-mode="co-investigate" class="is-active">共查</button>
                <button type="button" data-mode="challenge">反驳</button>
                <button type="button" data-mode="reflect">复述</button>
            </div>
            <div class="partner-log" data-role="log" aria-live="polite"></div>
            <form class="partner-composer">
                <span class="partner-prompt">›</span>
                <input class="partner-input" data-role="input" autocomplete="off"
                       placeholder="说说你卡在哪…" aria-label="思辨伙伴输入">
                <button class="partner-send" data-role="send" type="submit">发送</button>
            </form>
            <div class="partner-foot"><span data-role="foot">H1 · 共查 · 本地记忆</span></div>
        `;
        mount.appendChild(root);

        state.logEl = root.querySelector('[data-role="log"]');
        state.inputEl = root.querySelector('[data-role="input"]');
        state.sendEl = root.querySelector('[data-role="send"]');
        state.statusEl = root.querySelector('[data-role="status"]');
        state.footEl = root.querySelector('[data-role="foot"]');

        const memoryButton = root.querySelector('[data-role="memory"]');
        const saveButton = root.querySelector('[data-role="save"]');
        const clearButton = root.querySelector('[data-role="clear"]');
        const modeButtons = Array.from(root.querySelectorAll("[data-mode]"));
        const form = root.querySelector(".partner-composer");
        if (typeof options.onClose === "function") {
            const closeButton = el("button", null, "关闭");
            closeButton.type = "button";
            closeButton.addEventListener("click", options.onClose);
            root.querySelector(".partner-head").appendChild(closeButton);
        }

        function scrollToEnd() {
            state.logEl.scrollTop = state.logEl.scrollHeight;
        }

        function appendLine(kind, text) {
            const line = el("div", `partner-line partner-line--${kind}`, text);
            state.logEl.appendChild(line);
            scrollToEnd();
            return line;
        }

        function appendMeta(text) {
            return appendLine("meta", text);
        }

        function appendError(text) {
            return appendLine("error", text);
        }

        function updateFoot() {
            const memoryText = state.memoryRoot ? "本地记忆" : "本地规则";
            state.footEl.textContent =
                `${state.hintLevel} · ${MODE_LABELS[state.mode] || state.mode} · ${memoryText}`;
        }

        function setMode(mode) {
            if (!MODE_LABELS[mode]) return;
            state.mode = mode;
            modeButtons.forEach(button => {
                button.classList.toggle("is-active", button.dataset.mode === mode);
            });
            updateFoot();
        }

        function callTarget(target) {
            if (!target || typeof target !== "object") return;
            const stepIndex = target.stepIndex;
            if (stepIndex != null && typeof options.onJump === "function") {
                options.onJump(target);
                return;
            }
            if (typeof options.onHighlight === "function") {
                options.onHighlight(target);
            } else if (typeof options.onJump === "function") {
                options.onJump(target);
            }
        }

        function runResultText(result) {
            if (result == null) return "";
            if (typeof result === "string") return result;
            if (typeof result !== "object") return String(result);
            const parts = [];
            if (result.stdout) parts.push(`stdout:\n${result.stdout}`);
            if (result.stderr) parts.push(`stderr:\n${result.stderr}`);
            if (result.error) {
                const message = typeof result.error === "string"
                    ? result.error
                    : result.error.message || result.error.title || JSON.stringify(result.error);
                parts.push(`error:\n${message}`);
            }
            if (result.exception) parts.push(`exception:\n${result.exception}`);
            if (result.steps != null) parts.push(`steps: ${result.steps}`);
            if (result.durationMs != null) parts.push(`duration: ${result.durationMs} ms`);
            return parts.join("\n") || "完成。";
        }

        async function defaultRun(action) {
            const code = action?.target?.code || "";
            if (!code.trim()) {
                appendMeta("这个动作没有可运行的代码。");
                return;
            }
            try {
                if (state.workbench === "turtle") {
                    const response = await fetch("/api/turtle/compile", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ source: code })
                    });
                    const payload = await response.json();
                    if (!response.ok) {
                        throw new Error(payload.detail || `HTTP ${response.status}`);
                    }
                    const text = payload.error
                        ? `运行错误：${payload.error.title || payload.error.message || "未知错误"}`
                        : `运行通过：${payload.steps?.length || 0} 个执行步骤。`;
                    appendMeta(text);
                    return;
                }
                if (state.workbench === "netbrick") {
                    appendMeta("NetBrick 的变体请在“结构追踪”里推演；我不会替你直接改图。");
                    return;
                }
                const response = await fetch("/api/run", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code })
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.detail || `HTTP ${response.status}`);
                }
                appendMeta(runResultText(payload));
            } catch (error) {
                appendError(`运行失败：${error.message}`);
            }
        }

        async function runAction(action) {
            try {
                if (typeof options.onRun === "function") {
                    const result = await options.onRun(action);
                    const text = runResultText(result);
                    if (text) appendMeta(text);
                    return;
                }
                await defaultRun(action);
            } catch (error) {
                appendError(`运行失败：${error.message}`);
            }
        }

        async function insertProposal(action) {
            try {
                if (typeof options.onInsert === "function") {
                    const accepted = await options.onInsert(action);
                    if (accepted !== false) {
                        appendMeta(`已插入示范代码${action.target?.line ? `（第 ${action.target.line} 行）` : ""}。`);
                    }
                    return;
                }
                if (navigator.clipboard) {
                    await navigator.clipboard.writeText(action.code || "");
                    appendMeta("已复制示范代码，请粘贴到编辑器。");
                }
            } catch (error) {
                appendError(`插入失败：${error.message}`);
            }
        }

        async function saveCase(casePayload) {
            try {
                const response = await fetch("/api/partner/memory", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(casePayload)
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.detail || `HTTP ${response.status}`);
                }
                appendMeta(`已保存档案：${payload.title || casePayload.title}`);
            } catch (error) {
                appendError(`保存失败：${error.message}`);
            }
        }

        function saveLastCase() {
            if (!state.lastUser && !state.lastAssistant) {
                appendMeta("还没有可以保存的对话。");
                return;
            }
            saveCase({
                title: state.lastUser.slice(0, 80) || "一次困惑调查",
                workbench: state.workbench,
                question: state.lastUser,
                conclusion: state.lastAssistant.slice(0, 2000),
                status: "open"
            });
        }

        async function loadMemory() {
            try {
                const response = await fetch("/api/partner/memory");
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.detail || `HTTP ${response.status}`);
                }
                state.memoryRoot = payload.root || "";
                state.cases = payload.cases || [];
                updateFoot();
                const box = el("div", "partner-memory");
                box.appendChild(el("div", null, `记忆目录：${payload.root || "未知"}`));
                if (!state.cases.length) {
                    box.appendChild(el("div", null, "还没有档案。第一次调查结束后可以点“保存”。"));
                } else {
                    state.cases.slice(0, 10).forEach(item => {
                        const button = el(
                            "button",
                            null,
                            `[${item.workbench}] ${item.title} · ${item.status}`
                        );
                        button.type = "button";
                        button.addEventListener("click", () => {
                            appendMeta(item.conclusion || "这个档案还没有结论。");
                        });
                        box.appendChild(button);
                    });
                }
                state.logEl.appendChild(box);
                scrollToEnd();
            } catch (error) {
                appendError(`读取记忆失败：${error.message}`);
            }
        }

        function appendEvidence(action, container) {
            (action.refs || []).forEach(ref => {
                const row = el("div", "partner-action__ref");
                const parts = [ref.type || "evidence", ref.label || ""];
                if (ref.line != null) parts.push(`第 ${ref.line} 行`);
                if (ref.stepIndex != null) parts.push(`第 ${Number(ref.stepIndex) + 1} 步`);
                if (ref.nodeId) parts.push(String(ref.nodeId));
                row.appendChild(el("span", null, parts.filter(Boolean).join(" · ")));
                if (ref.line != null || ref.stepIndex != null || ref.nodeId) {
                    const button = el("button", null, "跳过去");
                    button.type = "button";
                    button.addEventListener("click", () => callTarget({
                        line: ref.line,
                        stepIndex: ref.stepIndex,
                        nodeId: ref.nodeId
                    }));
                    row.appendChild(button);
                }
                container.appendChild(row);
            });
        }

        function appendAction(action) {
            if (!action || !action.kind) return;
            if (action.kind === "propose_code") {
                state.sawProposeCode = true;
            }
            const block = el("div", `partner-action partner-action--${action.kind}`);
            const head = el(
                "div",
                "partner-action__head",
                action.label || ACTION_LABELS[action.kind] || action.kind
            );
            block.appendChild(head);
            const actionBody = el("div", "partner-action__body");
            const buttons = el("div", "partner-action__buttons");

            if (action.kind === "evidence") {
                appendEvidence(action, actionBody);
                block.appendChild(actionBody);
                state.logEl.appendChild(block);
                scrollToEnd();
                return;
            }

            if (action.kind === "highlight" || action.kind === "jump") {
                actionBody.textContent = action.label || "看这里";
                const button = el("button", null, action.kind === "jump" ? "跳过去" : "看这里");
                button.type = "button";
                button.addEventListener("click", () => callTarget(action.target));
                buttons.appendChild(button);
            } else if (action.kind === "run") {
                actionBody.textContent = "我可以跑这个变体，但由你决定什么时候跑。";
                const button = el("button", null, "运行验证");
                button.type = "button";
                button.addEventListener("click", () => void runAction(action));
                buttons.appendChild(button);
            } else if (action.kind === "propose_code") {
                if (action.why) {
                    actionBody.textContent = action.why;
                }
                const code = el("pre", "partner-code");
                code.textContent = action.code || "";
                block.appendChild(actionBody);
                block.appendChild(code);
                const note = el(
                    "div",
                    "partner-note",
                    action.hintLevel === "H4"
                        ? "这是答案；先试着解释为什么。"
                        : "这是提示，不是完整答案；留空的地方由你补。"
                );
                block.appendChild(note);
                const insertButton = el(
                    "button",
                    null,
                    action.target?.line
                        ? `插入到第 ${action.target.line} 行`
                        : "插入示范"
                );
                insertButton.type = "button";
                insertButton.addEventListener("click", () => void insertProposal(action));
                buttons.appendChild(insertButton);
                const copyButton = el("button", null, "复制");
                copyButton.type = "button";
                copyButton.addEventListener("click", async () => {
                    try {
                        await navigator.clipboard.writeText(action.code || "");
                        appendMeta("已复制示范代码。");
                    } catch (error) {
                        appendError(`复制失败：${error.message}`);
                    }
                });
                buttons.appendChild(copyButton);
                const verifyButton = el("button", null, "验证");
                verifyButton.type = "button";
                verifyButton.addEventListener("click", () => {
                    void runAction({
                        kind: "run",
                        target: { type: "variant", code: action.code },
                        label: "验证示范"
                    });
                });
                buttons.appendChild(verifyButton);
                const rejectButton = el("button", "partner-danger", "拒绝");
                rejectButton.type = "button";
                rejectButton.addEventListener("click", () => {
                    block.remove();
                    appendMeta("已拒绝这个示范。");
                });
                buttons.appendChild(rejectButton);
                block.appendChild(buttons);
                state.logEl.appendChild(block);
                scrollToEnd();
                return;
            } else if (action.kind === "save_case") {
                actionBody.textContent = action.case?.title || "把这次调查保存成档案？";
                const button = el("button", null, "保存到记忆");
                button.type = "button";
                button.addEventListener("click", () => void saveCase({
                    ...action.case,
                    workbench: action.case?.workbench || state.workbench
                }));
                buttons.appendChild(button);
            }

            block.appendChild(actionBody);
            block.appendChild(buttons);
            state.logEl.appendChild(block);
            scrollToEnd();
        }

        function offerCodeFromText(text) {
            const blocks = [];
            const fence = /```(?:python|py|javascript|js)?\s*\n([\s\S]*?)```/g;
            let match = fence.exec(text || "");
            while (match && blocks.length < 2) {
                const code = match[1].trim();
                if (code) blocks.push(code);
                match = fence.exec(text || "");
            }
            blocks.forEach(code => {
                appendAction({
                    kind: "propose_code",
                    target: {
                        workbench: state.workbench,
                        mode: "insert",
                        line: null
                    },
                    code,
                    why: "对话里给出的示范代码；确认后再插入。",
                    hintLevel: state.hintLevel
                });
            });
        }

        function finishStream() {
            state.streaming = false;
            state.controller = null;
            window.clearTimeout(state.timeoutTimer);
            state.timeoutTimer = 0;
            state.sendEl.textContent = "发送";
            state.sendEl.disabled = false;
            state.inputEl.disabled = false;
            if (state.lastAssistant.trim()) {
                state.messages.push({ role: "assistant", content: state.lastAssistant.trim() });
                state.messages = state.messages.slice(-10);
            }
            updateFoot();
        }

        function parseRawEvent(raw) {
            let eventName = "message";
            let data = "";
            raw.split("\n").forEach(line => {
                if (line.startsWith("event:")) {
                    eventName = line.slice(6).trim();
                } else if (line.startsWith("data:")) {
                    data += line.slice(5).trim();
                }
            });
            if (!data) return null;
            try {
                return { eventName, data: JSON.parse(data) };
            } catch (error) {
                return null;
            }
        }

        async function consumeStream(response, assistantEl) {
            const reader = response.body && response.body.getReader();
            if (!reader) {
                throw new Error("当前浏览器无法读取流式响应。");
            }
            const decoder = new TextDecoder();
            let buffer = "";
            const handleRaw = raw => {
                const parsed = parseRawEvent(raw);
                if (!parsed) return;
                const { eventName, data } = parsed;
                if (eventName === "meta") {
                    const runtime = data.runtime || {};
                    state.memoryRoot = data.memoryRoot || state.memoryRoot;
                    state.cases = data.cases || state.cases;
                    const modelReady = runtime.modelReady !== undefined
                        ? Boolean(runtime.modelReady)
                        : Boolean(runtime.llmConfigured);
                    if (modelReady) {
                        state.statusEl.textContent = `模型 ${runtime.model || ""}`;
                    } else if (runtime.llmConfigured) {
                        state.statusEl.textContent = "模型不可用 · 本地保底";
                    } else {
                        state.statusEl.textContent = "本地保底 · 未配置模型";
                    }
                    updateFoot();
                } else if (eventName === "token") {
                    const delta = data.delta || "";
                    if (delta) {
                        assistantEl.textContent += delta;
                        state.lastAssistant += delta;
                        scrollToEnd();
                    }
                } else if (eventName === "action") {
                    appendAction(data);
                } else if (eventName === "hint") {
                    state.hintLevel = data.level || state.hintLevel;
                    updateFoot();
                } else if (eventName === "error") {
                    appendError(data.message || "生成失败。");
                } else if (eventName === "done") {
                    if (data.note) appendMeta(data.note);
                    if (!state.sawProposeCode) {
                        offerCodeFromText(state.lastAssistant);
                    }
                }
            };

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                let boundary = buffer.indexOf("\n\n");
                while (boundary !== -1) {
                    const raw = buffer.slice(0, boundary).trim();
                    buffer = buffer.slice(boundary + 2);
                    if (raw) handleRaw(raw);
                    boundary = buffer.indexOf("\n\n");
                }
            }
            const trailing = buffer.trim();
            if (trailing) handleRaw(trailing);
        }

        async function send() {
            if (state.streaming) {
                if (state.controller) state.controller.abort();
                return;
            }
            const question = state.inputEl.value.trim();
            if (!question) return;
            state.inputEl.value = "";
            state.lastUser = question;
            state.lastAssistant = "";
            state.sawProposeCode = false;
            appendLine("user", question);
            state.messages.push({ role: "user", content: question });
            state.messages = state.messages.slice(-10);

            const assistantEl = appendLine("assistant", "");
            state.streaming = true;
            state.sendEl.textContent = "停止";
            state.controller = new AbortController();
            window.clearTimeout(state.timeoutTimer);
            state.timeoutTimer = window.setTimeout(() => {
                if (!state.streaming) return;
                appendError("模型响应超时，已停止。");
                state.controller?.abort();
            }, 55000);

            let context = {};
            try {
                context = typeof options.getContext === "function"
                    ? options.getContext() || {}
                    : {};
            } catch (error) {
                context = {};
            }

            try {
                const response = await fetch("/api/partner/stream", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    signal: state.controller.signal,
                    body: JSON.stringify({
                        workbench: state.workbench,
                        mode: state.mode,
                        messages: state.messages,
                        context
                    })
                });
                if (!response.ok) {
                    const detail = await response.text();
                    throw new Error(detail || `HTTP ${response.status}`);
                }
                await consumeStream(response, assistantEl);
            } catch (error) {
                if (error.name === "AbortError") {
                    appendMeta("已停止。");
                } else {
                    appendError(`连接失败：${error.message}`);
                }
            } finally {
                finishStream();
                if (typeof options.onDone === "function") {
                    options.onDone();
                }
            }
        }

        form.addEventListener("submit", event => {
            event.preventDefault();
            if (state.streaming) {
                if (state.controller) state.controller.abort();
                return;
            }
            void send();
        });
        modeButtons.forEach(button => {
            button.addEventListener("click", () => setMode(button.dataset.mode));
        });
        memoryButton.addEventListener("click", () => void loadMemory());
        saveButton.addEventListener("click", saveLastCase);
        clearButton.addEventListener("click", () => {
            state.messages = [];
            state.lastUser = "";
            state.lastAssistant = "";
            state.logEl.innerHTML = "";
            welcome();
        });

        function appendLogo() {
            const logo = el("pre", "partner-logo");
            logo.textContent = LOGO;
            state.logEl.appendChild(logo);
        }

        function welcome() {
            appendLogo();
            appendMeta("我在这儿。先说说你卡在哪；也可以选上面的模式。");
            updateFoot();
        }

        welcome();

        return {
            element: root,
            send,
            focus: () => state.inputEl.focus(),
            clear: () => {
                state.messages = [];
                state.logEl.innerHTML = "";
                welcome();
            },
            setMode,
            getMode: () => state.mode,
            injectAction: appendAction
        };
    }

    function createPartnerDock(mount, options = {}) {
        if (!mount) {
            throw new Error("partner dock mount is required");
        }
        mount.innerHTML = "";
        const root = el("div", "partner-dock");
        root.innerHTML = `
            <div class="partner-dock__bar">
                <span class="partner-dock__path">~/deeptracer</span>
                <span class="partner-dock__prompt">$</span>
                <input class="partner-dock__input" type="text" autocomplete="off"
                       spellcheck="false" placeholder="输入 deeptracer 打开思辨伙伴"
                       aria-label="输入 deeptracer 打开思辨伙伴">
                <span class="partner-dock__hint">输入 deeptracer ↵</span>
            </div>
            <div class="partner-dock__drawer" hidden>
                <div class="partner-dock__resizer" title="拖拽调整终端高度">
                    <span></span>
                </div>
                <div class="partner-dock__console"></div>
            </div>
        `;
        mount.appendChild(root);

        const bar = root.querySelector(".partner-dock__bar");
        const input = root.querySelector(".partner-dock__input");
        const hint = root.querySelector(".partner-dock__hint");
        const drawer = root.querySelector(".partner-dock__drawer");
        const consoleMount = drawer.querySelector(".partner-dock__console");
        const resizer = drawer.querySelector(".partner-dock__resizer");
        let consoleInstance = null;

        const defaultHeight = Math.min(window.innerHeight * 0.52, 520);
        let drawerHeight = defaultHeight;
        try {
            const stored = Number(
                window.localStorage.getItem("deeptracer.partner.height")
            );
            if (Number.isFinite(stored) && stored >= 180) {
                drawerHeight = stored;
            }
        } catch (error) {
            // localStorage may be unavailable in private or embedded contexts.
        }
        drawer.style.height = `${Math.round(drawerHeight)}px`;

        resizer.addEventListener("pointerdown", event => {
            event.preventDefault();
            const startY = event.clientY;
            const startHeight = drawer.getBoundingClientRect().height;
            const onMove = moveEvent => {
                const maxHeight = window.innerHeight * 0.85;
                drawerHeight = Math.max(
                    180,
                    Math.min(maxHeight, startHeight + (startY - moveEvent.clientY))
                );
                drawer.style.height = `${Math.round(drawerHeight)}px`;
            };
            const onUp = () => {
                window.removeEventListener("pointermove", onMove);
                window.removeEventListener("pointerup", onUp);
                try {
                    window.localStorage.setItem(
                        "deeptracer.partner.height",
                        String(Math.round(drawerHeight))
                    );
                } catch (error) {
                    // Ignore storage failures.
                }
            };
            window.addEventListener("pointermove", onMove);
            window.addEventListener("pointerup", onUp);
        });
        resizer.addEventListener("dblclick", () => {
            drawerHeight = defaultHeight;
            drawer.style.height = `${Math.round(drawerHeight)}px`;
            try {
                window.localStorage.setItem(
                    "deeptracer.partner.height",
                    String(Math.round(drawerHeight))
                );
            } catch (error) {
                // Ignore storage failures.
            }
        });

        function open() {
            root.classList.add("is-open");
            bar.hidden = true;
            drawer.hidden = false;
            if (!consoleInstance) {
                consoleInstance = createPartnerConsole(consoleMount, {
                    ...options,
                    onClose: close
                });
            }
            consoleInstance.focus();
        }

        function close() {
            root.classList.remove("is-open");
            bar.hidden = false;
            drawer.hidden = true;
            input.focus();
        }

        input.addEventListener("keydown", event => {
            if (event.key !== "Enter") return;
            event.preventDefault();
            const raw = input.value.trim();
            const command = raw.toLowerCase();
            if (!command) return;
            if (command === "deeptracer") {
                input.value = "";
                hint.textContent = "输入 deeptracer ↵";
                open();
                return;
            }
            if (command === "exit" || command === "/exit") {
                close();
                return;
            }
            if (command === "help") {
                hint.textContent = "deeptracer / exit / help";
                return;
            }
            hint.textContent = `command not found: ${raw}`;
        });

        document.addEventListener("keydown", event => {
            if (event.key === "Escape" && root.classList.contains("is-open")) {
                close();
            }
        });

        return {
            element: root,
            open,
            close,
            focus: () => input.focus(),
            getConsole: () => consoleInstance
        };
    }

    window.createPartnerConsole = createPartnerConsole;
    window.createPartnerDock = createPartnerDock;
    window.DEEPTRACER_LOGO = LOGO;
})();
