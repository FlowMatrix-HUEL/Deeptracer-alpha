(() => {
    "use strict";

    const canvas = document.getElementById("turtleCanvas");
    const context = canvas.getContext("2d");
    const elements = {
        workspace: document.querySelector(".turtle-workspace"),
        studio: document.querySelector(".turtle-studio"),
        collapseControlPanel: document.getElementById("collapseControlPanel"),
        openControlPanel: document.getElementById("openControlPanel"),
        toggleCodePanel: document.getElementById("toggleCodePanel"),
        applyStudentCode: document.getElementById("applyStudentCode"),
        collapseVariablePanel: document.getElementById("collapseVariablePanel"),
        openVariablePanel: document.getElementById("openVariablePanel"),
        controlResizeHandle: document.getElementById("controlResizeHandle"),
        codeResizeHandle: document.getElementById("codeResizeHandle"),
        variableResizeHandle: document.getElementById("variableResizeHandle"),
        commandCount: document.getElementById("commandCount"),
        commandHistory: document.getElementById("commandHistory"),
        turtlePose: document.getElementById("turtlePose"),
        stepStatus: document.getElementById("stepStatus"),
        angleStatus: document.getElementById("angleStatus"),
        currentLengthValue: document.getElementById("currentLengthValue"),
        currentAngleValue: document.getElementById("currentAngleValue"),
        currentHeadingValue: document.getElementById("currentHeadingValue"),
        penStatus: document.getElementById("penStatus"),
        generatedCode: document.getElementById("generatedTurtleCode"),
        patternResult: document.getElementById("patternResult"),
        copyCode: document.getElementById("copyTurtleCode"),
        toast: document.getElementById("turtleToast"),
        resetExecution: document.getElementById("resetExecution"),
        clearWorkspace: document.getElementById("clearWorkspace"),
        stepExecution: document.getElementById("stepExecution"),
        playExecution: document.getElementById("playExecution"),
        playbackSpeed: document.getElementById("playbackSpeed"),
        playbackSpeedValue: document.getElementById("playbackSpeedValue"),
        fullSpeedExecution: document.getElementById("fullSpeedExecution"),
        studentSource: document.getElementById("studentSource"),
        studentLineNumbers: document.getElementById("studentLineNumbers"),
        studentLineHighlight: document.getElementById("studentLineHighlight"),
        studentLineHover: document.getElementById("studentLineHover"),
        compileStatus: document.getElementById("compileStatus"),
        momentRail: document.getElementById("momentRail"),
        momentRailList: document.getElementById("momentRailList"),
        momentRailCount: document.getElementById("momentRailCount"),
        momentSource: document.getElementById("momentSource"),
        momentNext: document.getElementById("momentNext"),
        momentToggle: document.getElementById("momentToggle"),
        turtleError: document.getElementById("turtleError"),
        variableList: document.getElementById("variableList"),
        turtleStateList: document.getElementById("turtleStateList"),
        taskSelect: document.getElementById("taskSelect"),
        loadTask: document.getElementById("loadTask"),
        checkTask: document.getElementById("checkTask"),
        taskDescription: document.getElementById("taskDescription"),
        taskPreview: document.getElementById("taskPreview"),
        taskHint: document.getElementById("taskHint"),
        taskFeedback: document.getElementById("taskFeedback"),
        narrationEnabled: document.getElementById("narrationEnabled"),
        conceptNarration: document.getElementById("conceptNarration"),
        workName: document.getElementById("workName"),
        saveWork: document.getElementById("saveWork"),
        exportPng: document.getElementById("exportPng"),
        exportPython: document.getElementById("exportPython"),
        deleteWork: document.getElementById("deleteWork"),
        penColorInput: document.getElementById("penColorInput"),
        penSizeInput: document.getElementById("penSizeInput"),
        penSizeValue: document.getElementById("penSizeValue"),
        fillColorInput: document.getElementById("fillColorInput"),
        beginFill: document.getElementById("beginFill"),
        endFill: document.getElementById("endFill"),
        interactiveCodeToggle: document.getElementById("interactiveCodeToggle"),
        trailEnabled: document.getElementById("trailEnabled"),
        workList: document.getElementById("workList")
    };

    const state = {
        commands: [],
        distance: 60,
        angle: 90,
        penColor: "#3370ff",
        penSize: 2,
        fillColor: "#3370ff",
        filling: false,
        controlWidth: 256,
        variableWidth: 238,
        codeHeight: 280,
        generatedCode: "",
        toastTimer: 0,
        compileResult: null,
        compileTimer: 0,
        compileRequest: 0,
        executionIndex: -1,
        playbackTimer: 0,
        playing: false,
        breakpoints: new Set(),
        sourceMode: "auto",
        highlightedSourceLine: null,
        highlightedSourceIsError: false,
        activeTaskId: "",
        hintLevel: 0,
        taskAwaitingCheck: false,
        taskPassed: false,
        showTrail: true,
        interactiveCode: false,
        works: [],
        activeWorkId: "",
        previewCleared: false,
        moments: [],
        activeMomentId: null,
        momentsEnabled: true,
        momentEnrichTimer: 0,
        momentEnrichRequest: 0
    };

    const compass = ["东", "东北", "北", "西北", "西", "西南", "南", "东南"];
    const playbackSpeeds = [0.1, 0.5, 1, 2];
    const WORK_STORAGE_KEY = "deeptracer.turtle.works.v1";
    const tasks = {
        line: {
            title: "画一条线",
            description: "让海龟向前移动 80。",
            starter: "length = 80\n# 让海龟前进 length\n",
            shape: "line",
            expect: {moves: 1, closed: false},
            hints: [
                "使用 forward 命令向前移动。",
                "代码结构：forward(length)",
                "length = 80\nforward(length)"
            ]
        },
        square: {
            title: "画正方形",
            description: "重复 4 次前进和 90° 转向。",
            starter: "length = 80\nangle = 90\n# 使用 for i in range(4):\n",
            shape: "square",
            expect: {
                moves: 4,
                closed: true,
                minLoops: 1,
                iterations: 4,
                sideCount: 4,
                turnAngle: 90,
                uniformSides: true
            },
            hints: [
                "正方形需要重复执行同一组动作。",
                "代码结构：for i in range(4):",
                "for i in range(4):\n    forward(length)\n    right(angle)"
            ]
        },
        triangle: {
            title: "画正三角形",
            description: "重复 3 次，每次转向 120°。",
            starter: "length = 80\nangle = 120\n",
            shape: "triangle",
            expect: {
                moves: 3,
                closed: true,
                minLoops: 1,
                iterations: 3,
                sideCount: 3,
                turnAngle: 120,
                uniformSides: true
            },
            hints: [
                "正多边形外角等于 360° ÷ 边数。",
                "使用 for i in range(3)。",
                "for i in range(3):\n    forward(length)\n    right(angle)"
            ]
        },
        pentagon: {
            title: "画正五边形",
            description: "重复 5 次，每次转向 72°。",
            starter: "length = 70\nangle = 72\n",
            shape: "pentagon",
            expect: {
                moves: 5,
                closed: true,
                minLoops: 1,
                iterations: 5,
                sideCount: 5,
                turnAngle: 72,
                uniformSides: true
            },
            hints: [
                "五边形的外角是 360° ÷ 5。",
                "使用 for i in range(5)。",
                "for i in range(5):\n    forward(length)\n    right(angle)"
            ]
        },
        star: {
            title: "画五角星",
            description: "前进 5 次，每次右转 144°。",
            starter: "length = 90\nangle = 144\n",
            shape: "star",
            expect: {
                moves: 5,
                closed: true,
                minLoops: 1,
                iterations: 5,
                sideCount: 5,
                turnAngle: 144,
                uniformSides: true
            },
            hints: [
                "五角星的尖角路线与普通五边形不同。",
                "尝试 for i in range(5)，每次转向 144°。",
                "for i in range(5):\n    forward(length)\n    right(144)"
            ]
        },
        spiral: {
            title: "画螺旋",
            description: "循环中逐渐增加前进距离。",
            starter:
                "length = 20\n" +
                "for i in range(20):\n" +
                "    forward(length)\n" +
                "    right(30)\n" +
                "    # 每一轮都要增加 length\n",
            shape: "spiral",
            expect: {
                minMoves: 20,
                closed: false,
                minLoops: 1,
                iterations: 20,
                turnAngle: 30,
                growingLengths: true
            },
            hints: [
                "螺旋的边长需要随循环变化。",
                "在循环内更新 length。",
                "forward(length)\nright(30)\nlength = length + 5"
            ]
        },
        functions: {
            title: "用函数画正方形",
            description: "定义 draw_square 函数，再调用一次。",
            starter: "length = 80\ndef draw_square(size):\n    # 补充函数内容\n    pass\ndraw_square(length)\n",
            shape: "square",
            expect: {
                moves: 4,
                closed: true,
                minLoops: 1,
                minFunctions: 1,
                iterations: 4,
                sideCount: 4,
                turnAngle: 90,
                uniformSides: true
            },
            hints: [
                "把画正方形的重复动作放进函数。",
                "函数结构：def draw_square(size):",
                "for i in range(4):\n    forward(size)\n    right(90)"
            ]
        },
        refactor: {
            title: "把重复代码改成循环",
            description: "保持正方形不变，用 for 循环替代重复代码。",
            starter: "length = 60\nforward(length)\nright(90)\nforward(length)\nright(90)\nforward(length)\nright(90)\nforward(length)\nright(90)\n",
            shape: "square",
            expect: {
                moves: 4,
                closed: true,
                minLoops: 1,
                iterations: 4,
                sideCount: 4,
                turnAngle: 90,
                uniformSides: true
            },
            hints: [
                "先找出重复出现的两条命令。",
                "把重复 4 次的命令放进 for。",
                "for i in range(4):\n    forward(length)\n    right(90)"
            ]
        },
        branch: {
            title: "循环中的分支",
            description: "循环移动 6 次，并在第 3 次时改变转向。",
            starter:
                "length = 70\n" +
                "for i in range(6):\n" +
                "    forward(length)\n" +
                "    # 在第 3 轮使用 if 改变转向\n",
            shape: "branch",
            expect: {
                minMoves: 6,
                closed: false,
                minLoops: 1,
                iterations: 6,
                minConditionals: 1
            },
            hints: [
                "if 只在条件成立时执行，else 处理其余情况。",
                "在循环中判断 i == 2，只在第 3 轮改变方向。",
                "if i == 2:\n    right(120)\nelse:\n    right(60)"
            ]
        }
    };

    function addCommand(command) {
        state.commands.push({...command});
        if (state.sourceMode === "manual") {
            const source = elements.studentSource.value.replace(/\s+$/, "");
            elements.studentSource.value =
                `${source}${source ? "\n" : ""}${simpleCommandLine(command)}`;
            updateStudentLineNumbers();
            scheduleCompile(160);
        }
        refresh();
    }

    function simpleCommandLine(command) {
        if (command.type === "forward" || command.type === "back") {
            return `${command.type}(${formatNumber(command.distance)})`;
        }
        if (command.type === "left" || command.type === "right") {
            return `${command.type}(${formatNumber(command.angle)})`;
        }
        if (command.type === "face_move") {
            return (
                `setheading(${formatNumber(command.heading)})\n` +
                `forward(${formatNumber(command.distance)})`
            );
        }
        if (command.type === "style") {
            if (command.color) return `pencolor("${command.color}")`;
            if (command.size) return `pensize(${formatNumber(command.size)})`;
            if (command.fillColor) {
                return `fillcolor("${command.fillColor}")`;
            }
        }
        if (command.type === "fill_start") return "begin_fill()";
        if (command.type === "fill_end") return "end_fill()";
        return `${command.down ? "pendown" : "penup"}()`;
    }

    function move(direction) {
        addCommand({
            type: direction,
            distance: state.distance
        });
    }

    function moveInDirection(heading) {
        addCommand({
            type: "face_move",
            heading: normalizedHeading(heading),
            distance: state.distance
        });
    }

    function turn(direction) {
        addCommand({
            type: direction,
            angle: state.angle
        });
    }

    function togglePen() {
        const geometry = computeGeometry(state.commands);
        addCommand({
            type: "pen",
            down: !geometry.penDown
        });
    }

    function setPenColor(color) {
        state.penColor = color;
        addCommand({type: "style", color});
    }

    function setPenSize(size) {
        const next = Math.max(1, Math.min(10, Math.round(Number(size))));
        state.penSize = next;
        elements.penSizeInput.value = String(next);
        elements.penSizeValue.textContent = String(next);
        addCommand({type: "style", size: next});
    }

    function setFillColor(color) {
        state.fillColor = color;
        addCommand({type: "style", fillColor: color});
    }

    function beginFill() {
        if (state.filling) return;
        state.filling = true;
        addCommand({type: "fill_start", color: state.fillColor});
    }

    function endFill() {
        if (!state.filling) return;
        state.filling = false;
        addCommand({type: "fill_end", color: state.fillColor});
    }

    function undo() {
        if (!state.commands.length) return;
        state.commands.pop();
        state.filling = computeGeometry(state.commands).filling;
        refresh();
    }

    function clear() {
        clearWorkspace();
    }

    function clearWorkspace() {
        pausePlayback();
        state.compileRequest += 1;
        window.clearTimeout(state.compileTimer);
        state.momentEnrichRequest += 1;
        window.clearTimeout(state.momentEnrichTimer);
        state.commands = [];
        state.filling = false;
        state.sourceMode = "auto";
        state.compileResult = null;
        state.moments = [];
        state.activeMomentId = null;
        state.breakpoints.clear();
        state.executionIndex = -1;
        state.previewCleared = true;
        state.highlightedSourceLine = null;
        state.highlightedSourceIsError = false;
        state.taskAwaitingCheck = false;
        state.taskPassed = false;
        elements.studentSource.value = "";
        updateStudentLineNumbers();
        renderMomentRail();
        renderHistory();
        renderPattern(null);
        renderVariables(null);
        renderNarration(null);
        renderTaskFeedback(null, []);
        elements.turtleError.hidden = true;
        elements.turtleError.innerHTML = "";
        elements.commandCount.textContent = "0";
        resetExecution();
        elements.compileStatus.textContent = "等待输入";
        if (elements.momentSource) {
            elements.momentSource.textContent = "本地规则";
        }
        showToast("已清空画布、代码和关键瞬间");
    }

    function drawSquare() {
        state.commands = [];
        const distance = state.distance;
        const angle = state.angle;
        for (let index = 0; index < 4; index += 1) {
            state.commands.push({type: "forward", distance});
            state.commands.push({type: "right", angle});
        }
        refresh();
        showToast("已匹配重复动作，并生成 for 循环");
    }

    function computeGeometry(commands) {
        let x = 0;
        let y = 0;
        let heading = 0;
        let penDown = true;
        let color = state.penColor;
        let size = state.penSize;
        let fillColor = state.fillColor;
        let filling = false;
        let fillPoints = [];
        const points = [{x, y}];
        const segments = [];
        const fills = [];

        commands.forEach(command => {
            if (command.type === "face_move") {
                heading = normalizedHeading(command.heading) * Math.PI / 180;
            }
            if (
                command.type === "forward" ||
                command.type === "back" ||
                command.type === "face_move"
            ) {
                const distance = Number(command.distance) || 0;
                const signedDistance = command.type === "back" ? -distance : distance;
                const nextX = x + Math.cos(heading) * signedDistance;
                const nextY = y + Math.sin(heading) * signedDistance;
                if (penDown) {
                    segments.push({
                        from: {x, y},
                        to: {x: nextX, y: nextY},
                        color,
                        size
                    });
                }
                x = nextX;
                y = nextY;
                points.push({x, y});
                if (filling) fillPoints.push({x, y});
            } else if (command.type === "left" || command.type === "right") {
                const angle = (Number(command.angle) || 0) * Math.PI / 180;
                heading += command.type === "left" ? angle : -angle;
            } else if (command.type === "pen") {
                penDown = Boolean(command.down);
            } else if (command.type === "style") {
                if (command.color) color = command.color;
                if (command.size) size = Number(command.size);
                if (command.fillColor) fillColor = command.fillColor;
            } else if (command.type === "fill_start") {
                filling = true;
                fillPoints = [{x, y}];
            } else if (command.type === "fill_end") {
                if (filling && fillPoints.length > 2) {
                    fills.push({
                        points: fillPoints.map(point => ({...point})),
                        color: command.color || fillColor
                    });
                }
                filling = false;
                fillPoints = [];
            }
        });

        return {
            x,
            y,
            heading,
            penDown,
            color,
            size,
            fillColor,
            filling,
            points,
            segments,
            fills
        };
    }

    function normalizeCommands(commands) {
        const normalized = [];
        commands.forEach(command => {
            if (command.type === "forward" || command.type === "back") {
                const previous = normalized[normalized.length - 1];
                if (previous?.type === command.type) {
                    const total =
                        Number(previous.distance) + Number(command.distance);
                    normalized.pop();
                    if (total !== 0) {
                        normalized.push({
                            type: command.type,
                            distance: total
                        });
                    }
                    return;
                }
            }

            if (command.type === "face_move") {
                const previous = normalized[normalized.length - 1];
                if (
                    previous?.type === "face_move" &&
                    normalizedHeading(previous.heading) ===
                    normalizedHeading(command.heading)
                ) {
                    normalized.pop();
                    normalized.push({
                        type: "face_move",
                        heading: normalizedHeading(command.heading),
                        distance:
                            Number(previous.distance) + Number(command.distance)
                    });
                    return;
                }
            }

            if (command.type === "left" || command.type === "right") {
                const signed = command.type === "right"
                    ? Number(command.angle)
                    : -Number(command.angle);
                const previous = normalized[normalized.length - 1];
                if (previous && (previous.type === "left" || previous.type === "right")) {
                    const previousSigned = previous.type === "right"
                        ? previous.angle
                        : -previous.angle;
                    const total = previousSigned + signed;
                    normalized.pop();
                    if (total !== 0) {
                        normalized.push({
                            type: total >= 0 ? "right" : "left",
                            angle: Math.abs(total)
                        });
                    }
                    return;
                }
            }

            if (command.type === "pen") {
                const previousPen = [...normalized]
                    .reverse()
                    .find(item => item.type === "pen");
                const previousDown = previousPen ? previousPen.down : true;
                if (previousDown === Boolean(command.down)) return;
            }
            normalized.push({...command});
        });
        return normalized;
    }

    function commandKey(command) {
        if (command.type === "forward" || command.type === "back") {
            return `${command.type}:${command.distance}`;
        }
        if (command.type === "face_move") {
            return `face_move:${normalizedHeading(command.heading)}:${command.distance}`;
        }
        if (command.type === "left" || command.type === "right") {
            return `${command.type}:${command.angle}`;
        }
        if (command.type === "style") {
            return `style:${command.color || ""}:${command.size || ""}:${command.fillColor || ""}`;
        }
        if (command.type === "fill_start" || command.type === "fill_end") {
            return command.type;
        }
        return `${command.type}:${Boolean(command.down)}`;
    }

    function findRepeatedPattern(commands) {
        let best = null;
        const maxPatternLength = Math.min(4, Math.floor(commands.length / 3));
        for (let patternLength = 1; patternLength <= maxPatternLength; patternLength += 1) {
            for (
                let start = 0;
                start <= commands.length - patternLength * 3;
                start += 1
            ) {
                const pattern = commands.slice(start, start + patternLength);
                const key = pattern.map(commandKey).join("|");
                let repeats = 1;
                let cursor = start + patternLength;
                while (cursor + patternLength <= commands.length) {
                    const candidate = commands.slice(cursor, cursor + patternLength);
                    if (candidate.map(commandKey).join("|") !== key) break;
                    repeats += 1;
                    cursor += patternLength;
                }
                if (repeats < 3) continue;
                const covered = repeats * patternLength;
                const candidate = {
                    start,
                    end: cursor,
                    pattern,
                    repeats,
                    covered
                };
                if (
                    !best ||
                    candidate.covered > best.covered ||
                    (
                        candidate.covered === best.covered &&
                        candidate.pattern.length > best.pattern.length
                    )
                ) {
                    best = candidate;
                }
            }
        }
        return best;
    }

    const helpers = {
        forward: {
            name: "move_forward",
            signature: "artist, distance",
            body: "artist.forward(distance)"
        },
        back: {
            name: "move_backward",
            signature: "artist, distance",
            body: "artist.backward(distance)"
        },
        left: {
            name: "turn_left",
            signature: "artist, angle",
            body: "artist.left(angle)"
        },
        right: {
            name: "turn_right",
            signature: "artist, angle",
            body: "artist.right(angle)"
        },
        lift_pen: {
            name: "lift_pen",
            signature: "artist",
            body: "artist.penup()"
        },
        lower_pen: {
            name: "lower_pen",
            signature: "artist",
            body: "artist.pendown()"
        }
    };

    function sceneCommand(command, indent = 0) {
        const prefix = "    ".repeat(indent);
        if (command.type === "forward" || command.type === "back") {
            return `${prefix}${helpers[command.type].name}(artist, ${formatNumber(command.distance)})`;
        }
        if (command.type === "face_move") {
            return (
                `${prefix}artist.setheading(${formatNumber(command.heading)})\n` +
                `${prefix}${helpers.forward.name}(artist, ${formatNumber(command.distance)})`
            );
        }
        if (command.type === "left" || command.type === "right") {
            return `${prefix}${helpers[command.type].name}(artist, ${formatNumber(command.angle)})`;
        }
        if (command.type === "style") {
            if (command.color) return `${prefix}artist.pencolor("${command.color}")`;
            if (command.size) return `${prefix}artist.pensize(${formatNumber(command.size)})`;
            if (command.fillColor) {
                return `${prefix}artist.fillcolor("${command.fillColor}")`;
            }
        }
        if (command.type === "fill_start") {
            return `${prefix}artist.begin_fill()`;
        }
        if (command.type === "fill_end") {
            return `${prefix}artist.end_fill()`;
        }
        const helper = command.down ? helpers.lower_pen : helpers.lift_pen;
        return `${prefix}${helper.name}(artist)`;
    }

    function emitSceneCommands(lines, commands, indent = 1) {
        commands.forEach(command => lines.push(sceneCommand(command, indent)));
    }

    function helperTypeForCommand(command) {
        if (["forward", "back", "left", "right"].includes(command.type)) {
            return command.type;
        }
        if (command.type === "face_move") return "forward";
        return command.down ? "lower_pen" : "lift_pen";
    }

    function formatNumber(value) {
        const number = Number(value);
        if (!Number.isFinite(number)) return "0";
        const normalized = Math.abs(number) < 0.0005 ? 0 : number;
        return Number.isInteger(normalized)
            ? String(normalized)
            : normalized.toFixed(1);
    }

    function normalizedHeading(value) {
        return ((Number(value) % 360) + 360) % 360;
    }

    function headingLabel(value) {
        const heading = normalizedHeading(value);
        const index = Math.round(heading / 45) % compass.length;
        return `${compass[index]} ${formatNumber(heading)}°`;
    }

    function setTurtleReadouts({
        length = state.distance,
        angle = state.angle,
        heading = 0,
        penDown = true
    } = {}) {
        elements.currentLengthValue.textContent = formatNumber(length);
        elements.currentAngleValue.textContent = `${formatNumber(angle)}°`;
        elements.currentHeadingValue.textContent = headingLabel(heading);
        elements.penStatus.textContent = penDown ? "画笔落下" : "画笔抬起";
    }

    function generateCode(commands) {
        const normalized = normalizeCommands(commands);
        const pattern = findRepeatedPattern(normalized);
        const usedHelpers = new Set(
            normalized.map(command => helperTypeForCommand(command))
        );
        const lines = ["import turtle", ""];

        ["forward", "back", "left", "right", "lift_pen", "lower_pen"]
            .filter(type => usedHelpers.has(type))
            .forEach(type => {
                const helper = helpers[type];
                lines.push(`def ${helper.name}(${helper.signature}):`);
                lines.push(`    ${helper.body}`);
                lines.push("");
            });

        lines.push("def draw_scene(artist):");
        if (!normalized.length) {
            lines.push("    # 使用方向键记录动作后，代码会自动出现在这里。");
            lines.push("    pass");
        } else if (pattern) {
            const before = normalized.slice(0, pattern.start);
            const after = normalized.slice(pattern.end);
            emitSceneCommands(lines, before);
            lines.push(`    # 相同动作重复 ${pattern.repeats} 次，使用循环更容易阅读`);
            lines.push(`    for _ in range(${pattern.repeats}):`);
            emitSceneCommands(lines, pattern.pattern, 2);
            if (after.length) {
                emitSceneCommands(lines, after);
            }
        } else {
            emitSceneCommands(lines, normalized);
        }

        lines.push(
            "",
            "",
            "def main():",
            "    screen = turtle.Screen()",
            '    screen.title("我的 Turtle 图形")',
            "    artist = turtle.Turtle()",
            '    artist.shape("classic")',
            "    artist.speed(3)",
            "    draw_scene(artist)",
            "    screen.mainloop()",
            "",
            "",
            'if __name__ == "__main__":',
            "    main()"
        );
        return {
            code: lines.join("\n"),
            normalized,
            pattern
        };
    }

    function generateSimplifiedSource(commands) {
        const normalized = normalizeCommands(commands);
        const pattern = findRepeatedPattern(normalized);
        const firstMove = normalized.find(
            command =>
                command.type === "forward" ||
                command.type === "back" ||
                command.type === "face_move"
        );
        const firstTurn = normalized.find(
            command => command.type === "left" || command.type === "right"
        );
        const length = firstMove?.distance ?? state.distance;
        const angle = firstTurn?.angle ?? state.angle;
        const lines = [`length = ${formatNumber(length)}`, `angle = ${formatNumber(angle)}`];

        const appendCommands = (items, indent = 0) => {
            items.forEach(command => {
                const prefix = "    ".repeat(indent);
                if (command.type === "face_move") {
                    lines.push(
                        `${prefix}setheading(${formatNumber(command.heading)})`
                    );
                    const argument = Number(command.distance) === Number(length)
                        ? "length"
                        : formatNumber(command.distance);
                    lines.push(
                        `${prefix}forward(${argument})`
                    );
                } else if (command.type === "forward" || command.type === "back") {
                    const argument = Number(command.distance) === Number(length)
                        ? "length"
                        : formatNumber(command.distance);
                    lines.push(`${prefix}${command.type}(${argument})`);
                } else if (command.type === "left" || command.type === "right") {
                    const argument = Number(command.angle) === Number(angle)
                        ? "angle"
                        : formatNumber(command.angle);
                    lines.push(`${prefix}${command.type}(${argument})`);
                } else if (command.type === "style") {
                    if (command.color) {
                        lines.push(`${prefix}pencolor("${command.color}")`);
                    } else if (command.size) {
                        lines.push(`${prefix}pensize(${formatNumber(command.size)})`);
                    } else if (command.fillColor) {
                        lines.push(`${prefix}fillcolor("${command.fillColor}")`);
                    }
                } else if (command.type === "fill_start") {
                    lines.push(`${prefix}begin_fill()`);
                } else if (command.type === "fill_end") {
                    lines.push(`${prefix}end_fill()`);
                } else {
                    lines.push(`${prefix}${command.down ? "pendown" : "penup"}()`);
                }
            });
        };

        if (pattern) {
            const before = normalized.slice(0, pattern.start);
            const after = normalized.slice(pattern.end);
            if (before.length) {
                appendCommands(before);
                lines.push("");
            }
            lines.push(`for i in range(${pattern.repeats}):`);
            appendCommands(pattern.pattern, 1);
            if (after.length) {
                lines.push("");
                appendCommands(after);
            }
        } else if (normalized.length) {
            lines.push("");
            appendCommands(normalized);
        }
        return lines.join("\n");
    }

    function updateStudentLineNumbers() {
        const count = Math.max(1, elements.studentSource.value.split("\n").length);
        const momentLineSet = momentLines();
        const fragment = document.createDocumentFragment();
        for (let line = 1; line <= count; line += 1) {
            const number = document.createElement("span");
            number.className = "student-line-number";
            number.dataset.line = String(line);
            number.textContent = String(line);
            if (state.breakpoints.has(line)) {
                number.classList.add("has-breakpoint");
            }
            if (momentLineSet.has(line)) {
                number.classList.add("has-moment");
            }
            fragment.appendChild(number);
        }
        elements.studentLineNumbers.replaceChildren(fragment);
        setStudentHighlight(state.highlightedSourceLine, false, false);
    }

    function setStudentSource(source, {manual = false, compileNow = false} = {}) {
        elements.studentSource.value = source;
        state.sourceMode = manual ? "manual" : "auto";
        updateStudentLineNumbers();
        scheduleCompile(compileNow ? 0 : 220);
    }

    function scheduleCompile(delay = 220) {
        window.clearTimeout(state.compileTimer);
        state.momentEnrichRequest += 1;
        window.clearTimeout(state.momentEnrichTimer);
        const request = ++state.compileRequest;
        elements.compileStatus.textContent = "正在分析";
        state.compileTimer = window.setTimeout(
            () => void compileStudentSource(request),
            delay
        );
    }

    async function compileStudentSource(request = ++state.compileRequest) {
        state.momentEnrichRequest += 1;
        window.clearTimeout(state.momentEnrichTimer);
        const source = elements.studentSource.value;
        try {
            const response = await fetch("/api/turtle/compile", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({source})
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload.detail || `HTTP ${response.status}`);
            }
            if (request !== state.compileRequest) return;
            return applyCompileResult(payload);
        } catch (error) {
            if (request !== state.compileRequest) return;
            state.compileResult = null;
            elements.compileStatus.textContent = "连接失败";
            showTurtleError({
                category: "runtime",
                title: "无法运行当前代码",
                hint: error.message,
                line: null
            });
            if (state.taskAwaitingCheck) {
                state.taskAwaitingCheck = false;
                renderTaskFeedback(false, ["无法连接教学执行器，请稍后重试。"]);
            }
        }
    }

    function applyCompileResult(result) {
        state.compileResult = result;
        state.generatedCode = result.generatedCode || "";
        state.moments = Array.isArray(result.moments) ? result.moments : [];
        state.activeMomentId = null;
        if (elements.momentSource) {
            elements.momentSource.textContent = "本地规则";
        }
        renderMomentRail();
        updateStudentLineNumbers();
        scheduleMomentEnrichment();
        syncControlsFromResult(result);
        renderGeneratedCode(
            displayedGeneratedCode(result.generatedCode || ""),
            result.lineMap || {}
        );
        renderError(result.error);
        if (result.error) {
            const errorLine = Number(result.error.line) || null;
            if (result.steps?.length) {
                renderExecutionStep(result.steps.length - 1);
            } else {
                resetExecution();
            }
            elements.compileStatus.textContent = result.error.category === "syntax"
                ? "语法错误"
                : "运行错误";
            setExecutionHighlight(errorLine, true);
            if (state.taskAwaitingCheck) {
                state.taskAwaitingCheck = false;
                renderTaskFeedback(false, [
                    `先修正第 ${errorLine || "?"} 行的${
                        result.error.category === "syntax" ? "语法" : "运行"
                    }错误，再检查任务。`
                ]);
            }
            return;
        }
        elements.compileStatus.textContent = `${result.steps.length} 个执行步骤`;
        const finalIndex = result.steps.length ? result.steps.length - 1 : -1;
        renderExecutionStep(finalIndex);
        if (state.taskAwaitingCheck) {
            state.taskAwaitingCheck = false;
            evaluateActiveTask();
        }
        return result;
    }

    function syncControlsFromResult(result) {
        const steps = result.steps || [];
        const variables = steps.flatMap(step => step.variables || []);
        const lengthVariable = variables.find(variable =>
            variable.name === "length" && Number.isFinite(Number(variable.value))
        );
        const angleVariable = variables.find(variable =>
            variable.name === "angle" && Number.isFinite(Number(variable.value))
        );
        if (lengthVariable) state.distance = Number(lengthVariable.value);
        if (angleVariable) state.angle = Number(angleVariable.value);
    }

    function renderError(error) {
        if (!error) {
            elements.turtleError.hidden = true;
            elements.turtleError.innerHTML = "";
            return;
        }
        elements.turtleError.hidden = false;
        const category = {
            syntax: "语法错误",
            runtime: "运行错误",
            logic: "逻辑检查"
        }[error.category] || "运行错误";
        elements.turtleError.innerHTML = `
            <strong>${escapeText(category)}${error.line ? ` · 第 ${escapeText(String(error.line))} 行` : ""}</strong>
            <span>${escapeText(error.title || error.message || "运行失败")}</span><br>
            <span>${escapeText(error.hint || "")}</span>
        `;
    }

    function showTurtleError(error) {
        renderError(error);
        setExecutionHighlight(error.line, true);
    }

    function displayedGeneratedCode(code) {
        if (!state.interactiveCode || !code.trim()) return code;
        const marker = "    screen.mainloop()";
        const markerIndex = code.lastIndexOf(marker);
        if (markerIndex < 0) return code;
        const interactionCode = [
            "    # 方向键与鼠标交互：把代码保存后，可直接用 Python 运行。",
            "    move_distance = 40",
            "",
            "    def move_forward():",
            "        artist.forward(move_distance)",
            "",
            "    def move_backward():",
            "        artist.backward(move_distance)",
            "",
            "    def turn_left():",
            "        artist.left(30)",
            "",
            "    def turn_right():",
            "        artist.right(30)",
            "",
            '    screen.onkeypress(move_forward, "Up")',
            '    screen.onkeypress(move_backward, "Down")',
            '    screen.onkeypress(turn_left, "Left")',
            '    screen.onkeypress(turn_right, "Right")',
            "",
            "    def place_dot(x, y):",
            "        artist.penup()",
            "        artist.goto(x, y)",
            "        artist.dot(8)",
            "        artist.pendown()",
            "",
            "    screen.onscreenclick(place_dot)",
            "    screen.listen()",
            marker
        ].join("\n");
        return code.slice(0, markerIndex) + interactionCode + code.slice(markerIndex + marker.length);
    }

    function renderGeneratedCode(code, lineMap = {}) {
        const reverseLineMap = Object.fromEntries(
            Object.entries(lineMap).map(([sourceLine, standardLine]) => [
                String(standardLine),
                Number(sourceLine)
            ])
        );
        const fragment = document.createDocumentFragment();
        code.split("\n").forEach((line, index) => {
            const lineElement = document.createElement("span");
            lineElement.className = "code-line";
            lineElement.dataset.standardLine = String(index + 1);
            if (reverseLineMap[index + 1]) {
                lineElement.dataset.sourceLine = String(reverseLineMap[index + 1]);
            }
            const number = document.createElement("span");
            number.className = "code-line__number";
            number.textContent = String(index + 1).padStart(2, "0");
            const source = document.createElement("span");
            source.className = "code-line__source";
            appendHighlightedLine(source, line);
            lineElement.append(number, source);
            fragment.appendChild(lineElement);
        });
        elements.generatedCode.replaceChildren(fragment);
    }

    function appendHighlightedLine(container, line) {
        const tokenPattern =
            /(#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b[A-Za-z_]\w*\b|\b\d+(?:\.\d+)?\b)/g;
        const keywords = new Set([
            "import", "from", "as", "def", "return", "if", "else",
            "elif", "for", "while", "in", "not", "and", "or",
            "__name__", "__main__"
        ]);
        const modules = new Set([
            "turtle", "artist", "screen", "distance", "angle"
        ]);
        let cursor = 0;
        let match;
        while ((match = tokenPattern.exec(line)) !== null) {
            if (match.index > cursor) {
                container.appendChild(
                    document.createTextNode(line.slice(cursor, match.index))
                );
            }
            const token = match[0];
            const tokenElement = document.createElement("span");
            if (token.startsWith("#")) tokenElement.className = "tok-comment";
            else if (token.startsWith('"') || token.startsWith("'")) tokenElement.className = "tok-string";
            else if (/^\d/.test(token)) tokenElement.className = "tok-number";
            else if (keywords.has(token)) tokenElement.className = "tok-keyword";
            else if (modules.has(token)) tokenElement.className = "tok-module";
            tokenElement.textContent = token;
            container.appendChild(tokenElement);
            cursor = tokenPattern.lastIndex;
        }
        if (cursor < line.length) {
            container.appendChild(document.createTextNode(line.slice(cursor)));
        }
    }

    function setStudentHighlight(line, isError = false, keepVisible = false) {
        state.highlightedSourceLine = line || null;
        state.highlightedSourceIsError = Boolean(isError && line);
        elements.studentLineNumbers
            .querySelectorAll(".student-line-number")
            .forEach(item => {
                item.classList.toggle(
                    "is-active",
                    Number(item.dataset.line) === Number(line)
                );
            });
        if (!line) {
            elements.studentLineHighlight.hidden = true;
            return;
        }
        const lineHeight = 16.8;
        elements.studentLineHighlight.hidden = false;
        elements.studentLineHighlight.classList.toggle("is-error", isError);
        elements.studentLineHighlight.style.top =
            `${10 + (Number(line) - 1) * lineHeight - elements.studentSource.scrollTop}px`;
        if (keepVisible) {
            const visibleTop = elements.studentSource.scrollTop;
            const targetTop = (Number(line) - 1) * lineHeight;
            if (
                targetTop < visibleTop ||
                targetTop > visibleTop + elements.studentSource.clientHeight - lineHeight * 2
            ) {
                elements.studentSource.scrollTop = Math.max(
                    0,
                    targetTop - elements.studentSource.clientHeight / 2
                );
                elements.studentLineNumbers.scrollTop =
                    elements.studentSource.scrollTop;
            }
        }
    }

    function setExecutionHighlight(line, isError = false) {
        setStudentHighlight(line, isError, true);
        elements.generatedCode
            .querySelectorAll(".code-line")
            .forEach(item => {
                item.classList.remove("is-current", "is-error");
            });
        if (!line || !state.compileResult?.lineMap) return;
        const standardLine = state.compileResult.lineMap[String(line)];
        if (!standardLine) return;
        const target = elements.generatedCode
            .querySelector(`[data-standard-line="${standardLine}"]`);
        target?.classList.add(isError ? "is-error" : "is-current");
        target?.scrollIntoView({block: "nearest"});
    }

    function highlightLinkedLine(sourceLine) {
        elements.studentLineNumbers
            .querySelectorAll(".student-line-number")
            .forEach(item => {
                item.classList.toggle(
                    "is-hover",
                    Number(item.dataset.line) === Number(sourceLine)
                );
            });
        elements.generatedCode
            .querySelectorAll(".code-line.is-linked")
            .forEach(item => item.classList.remove("is-linked"));
        if (!sourceLine) {
            elements.studentLineHover.hidden = true;
            return;
        }
        elements.studentLineHover.hidden = false;
        elements.studentLineHover.style.top =
            `${10 + (Number(sourceLine) - 1) * 16.8 - elements.studentSource.scrollTop}px`;
        if (!state.compileResult?.lineMap) return;
        const standardLine = state.compileResult.lineMap[String(sourceLine)];
        if (!standardLine) return;
        elements.generatedCode
            .querySelector(`[data-standard-line="${standardLine}"]`)
            ?.classList.add("is-linked");
    }

    function clearLinkedLine() {
        elements.studentLineHover.hidden = true;
        elements.studentLineNumbers
            .querySelectorAll(".student-line-number.is-hover")
            .forEach(item => item.classList.remove("is-hover"));
        elements.generatedCode
            .querySelectorAll(".code-line.is-linked")
            .forEach(item => item.classList.remove("is-linked"));
    }

    function variableValue(step, name, fallback) {
        const variable = step?.variables?.find(item => item.name === name);
        return variable ? variable.value : fallback;
    }

    function stepDisplayValues(step) {
        const commands = (state.compileResult?.commands || []).slice(
            0,
            Number(step?.commandCount) || 0
        );
        const lastMove = [...commands]
            .reverse()
            .find(command => command.type === "move");
        const lastTurn = [...commands]
            .reverse()
            .find(command => command.type === "turn");
        const movedDistance = lastMove
            ? Math.hypot(
                Number(lastMove.to.x) - Number(lastMove.from.x),
                Number(lastMove.to.y) - Number(lastMove.from.y)
            )
            : null;
        const turnedAngle = lastTurn
            ? Math.abs(
                normalizedHeading(
                    Number(lastTurn.toHeading) - Number(lastTurn.fromHeading)
                )
            )
            : null;
        return {
            length: variableValue(
                step,
                "length",
                movedDistance ?? state.distance
            ),
            angle: variableValue(
                step,
                "angle",
                turnedAngle ?? state.angle
            )
        };
    }

    function geometryFromCompileStep(step) {
        const commands = (state.compileResult?.commands || []).slice(
            0,
            Number(step?.commandCount) || 0
        );
        const points = [{x: 0, y: 0}];
        const segments = [];
        const fills = [];
        commands.forEach(command => {
            if (command.type === "move") {
                points.push(command.from, command.to);
                if (command.penDown) {
                    segments.push({
                        from: command.from,
                        to: command.to,
                        color: command.color,
                        size: command.size
                    });
                }
            } else if (command.type === "fill") {
                fills.push({
                    points: command.points || [],
                    color: command.color
                });
            }
        });
        const currentStyleCommand = [...commands]
            .reverse()
            .find(command => command.type === "style");
        const turtle = step?.turtle || {
            x: 0,
            y: 0,
            heading: 0,
            penDown: true,
            color: state.penColor,
            size: state.penSize
        };
        if (points.length === 1 && Number(turtle.x) !== 0) {
            points.push({x: Number(turtle.x), y: Number(turtle.y)});
        }
        return {
            x: Number(turtle.x),
            y: Number(turtle.y),
            heading: Number(turtle.heading) * Math.PI / 180,
            penDown: Boolean(turtle.penDown),
            color: currentStyleCommand?.color || turtle.color || state.penColor,
            size: currentStyleCommand?.size || turtle.size || state.penSize,
            fillColor: turtle.fillColor || state.fillColor,
            filling: Boolean(turtle.filling),
            points,
            segments,
            fills
        };
    }

    function geometryFromCommands(commands) {
        return geometryFromCompileStep({
            commandCount: commands.length,
            turtle: state.compileResult?.finalState
        });
    }

    function renderVariables(step) {
        const variables = step?.variables || [];
        if (!variables.length) {
            elements.variableList.innerHTML =
                '<p class="variable-empty">当前步骤没有变量。</p>';
        } else {
            elements.variableList.innerHTML = variables.map(variable => `
                <div class="variable-row">
                    <span>
                        <code>${escapeText(variable.name)}</code>
                        <small>
                            <i class="scope-badge ${variable.scopeKind === "local" ? "is-local" : ""}">
                                ${variable.scopeKind === "local" ? "局部" : "全局"}
                            </i>
                            ${escapeText(variable.type)} · ${escapeText(variable.scope)}
                        </small>
                    </span>
                    <strong>${escapeText(formatVariable(variable.value))}</strong>
                </div>
            `).join("");
        }
        const callStack = step?.callStack || [];
        if (callStack.length > 1) {
            const stack = document.createElement("div");
            stack.className = "call-stack";
            stack.innerHTML = `<span>调用栈</span>${callStack.map(frame =>
                `<code>${escapeText(frame.name)}:${escapeText(frame.line)}</code>`
            ).join("<i>→</i>")}`;
            elements.variableList.prepend(stack);
        }
        const turtle = step?.turtle || {
            x: 0,
            y: 0,
            heading: 0,
            penDown: true,
            color: "#3370ff",
            size: state.penSize,
            fillColor: state.fillColor,
            filling: false
        };
        elements.turtleStateList.innerHTML = [
            ["朝向", headingLabel(turtle.heading)],
            ["画笔", turtle.penDown ? "落下" : "抬起"],
            ["颜色", turtle.color || "#3370ff"],
            ["粗细", formatNumber(turtle.size || 2)],
            ["填充", turtle.filling ? "进行中" : "未进行"]
        ].map(([label, value]) => `
            <div class="state-row">
                <span>${escapeText(label)}</span>
                <span>${escapeText(value)}</span>
            </div>
        `).join("");
    }

    function formatVariable(value) {
        if (typeof value === "string") return JSON.stringify(value);
        if (value === null) return "None";
        if (typeof value === "boolean") return value ? "True" : "False";
        if (typeof value === "object") return JSON.stringify(value);
        return String(value);
    }

    function renderNarration(step) {
        if (!elements.narrationEnabled.checked) {
            elements.conceptNarration.textContent = "概念旁白已关闭。";
            return;
        }
        if (!step) {
            elements.conceptNarration.textContent =
                "单步执行时显示当前代码概念。";
            return;
        }
        const source = String(step.sourceText || "").trim();
        if (!source) {
            elements.conceptNarration.textContent =
                `正在执行第 ${step.line} 行。`;
            return;
        }

        let explanation = "这一行会按顺序执行一次，观察变量和海龟状态的变化。";
        const loop = source.match(/^for\s+([A-Za-z_]\w*)\s+in\s+range\(([^)]*)\)\s*:/);
        if (loop) {
            const loopVariable = (step.variables || []).find(
                variable => variable.name === loop[1]
            );
            explanation =
                `${loop[1]} 会依次取 range(${loop[2]}) 中的值，` +
                "循环体每轮执行一次。" +
                (
                    loopVariable
                        ? ` 当前 ${loop[1]} = ${formatVariable(loopVariable.value)}。`
                        : ""
                );
        } else if (/^def\s+([A-Za-z_]\w*)\s*\(/.test(source)) {
            const name = source.match(/^def\s+([A-Za-z_]\w*)/)?.[1] || "这个函数";
            explanation =
                `${name} 在这里被定义。函数把一组步骤打包，调用时才会执行。`;
        } else if (/^if\s+/.test(source)) {
            explanation =
                "先判断 if 后面的条件：成立时进入缩进块，不成立时跳过。";
        } else if (/^else\s*:/.test(source)) {
            explanation =
                "前面的条件不成立时，才会执行 else 缩进块。";
        } else if (/onkeypress|onkey\(/.test(source)) {
            explanation =
                "这里把按键和函数绑定起来；用户按键后，对应函数才会运行。";
        } else if (/onscreenclick|onclick\(/.test(source)) {
            explanation =
                "这里注册鼠标点击处理函数，并把点击坐标传给它。";
        } else if (/^forward|^backward|^back\(/.test(source)) {
            explanation =
                "海龟沿当前朝向移动。移动距离来自括号中的参数。";
        } else if (/^left\(|^right\(/.test(source)) {
            explanation =
                "海龟原地转向，坐标不变，但朝向会改变。";
        } else if (/^penup\(/.test(source)) {
            explanation = "抬起画笔后海龟仍会移动，但不会留下轨迹。";
        } else if (/^pendown\(/.test(source)) {
            explanation = "落下画笔后，海龟的移动会留下轨迹。";
        } else if (/^(pencolor|pensize|fillcolor)\(/.test(source)) {
            explanation =
                "这一行修改画笔样式，后续轨迹会使用新的颜色或粗细。";
        } else if (/^(begin_fill|end_fill)\(/.test(source)) {
            explanation =
                "这两个命令围出一个区域，Turtle 会用填充色覆盖该区域。";
        } else if (/=/.test(source) && !/==|<=|>=|!=/.test(source)) {
            const variable = source.split("=")[0].trim();
            explanation =
                `计算右侧表达式，并把结果保存到变量 ${variable}。`;
        }
        elements.conceptNarration.textContent = explanation;
    }

    function populateTasks() {
        const fragment = document.createDocumentFragment();
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "选择练习任务";
        fragment.appendChild(placeholder);
        Object.entries(tasks).forEach(([id, task]) => {
            const option = document.createElement("option");
            option.value = id;
            option.textContent = task.title;
            fragment.appendChild(option);
        });
        elements.taskSelect.replaceChildren(fragment);
    }

    function loadActiveTask() {
        const taskId = elements.taskSelect.value;
        const task = tasks[taskId];
        if (!task) {
            showToast("请先选择一个练习任务");
            return;
        }
        pausePlayback();
        state.activeTaskId = taskId;
        state.hintLevel = 0;
        state.taskAwaitingCheck = false;
        state.taskPassed = false;
        state.commands = [];
        state.filling = false;
        elements.taskDescription.textContent = task.description;
        elements.taskHint.textContent = "需要时逐层查看提示。";
        elements.taskHint.classList.remove("is-code");
        renderTaskFeedback(null, []);
        renderTaskPreview(task.shape);
        setStudentSource(task.starter, {manual: true, compileNow: true});
        showToast(`已载入任务：${task.title}`);
    }

    function taskRoute(shape) {
        if (shape === "line") {
            return [
                {type: "forward", distance: 80}
            ];
        }
        if (shape === "square") {
            return [
                {type: "forward", distance: 70}, {type: "right", angle: 90},
                {type: "forward", distance: 70}, {type: "right", angle: 90},
                {type: "forward", distance: 70}, {type: "right", angle: 90},
                {type: "forward", distance: 70}, {type: "right", angle: 90}
            ];
        }
        if (shape === "triangle") {
            return [
                {type: "forward", distance: 78}, {type: "right", angle: 120},
                {type: "forward", distance: 78}, {type: "right", angle: 120},
                {type: "forward", distance: 78}, {type: "right", angle: 120}
            ];
        }
        if (shape === "pentagon") {
            return Array.from({length: 5}).flatMap(() => [
                {type: "forward", distance: 61},
                {type: "right", angle: 72}
            ]);
        }
        if (shape === "star") {
            return Array.from({length: 5}).flatMap(() => [
                {type: "forward", distance: 82},
                {type: "right", angle: 144}
            ]);
        }
        if (shape === "spiral") {
            let distance = 10;
            return Array.from({length: 24}).flatMap(() => {
                const commands = [
                    {type: "forward", distance},
                    {type: "right", angle: 30}
                ];
                distance += 3;
                return commands;
            });
        }
        if (shape === "branch") {
            return [
                {type: "forward", distance: 58}, {type: "right", angle: 60},
                {type: "forward", distance: 58}, {type: "right", angle: 60},
                {type: "forward", distance: 58}, {type: "right", angle: 120},
                {type: "forward", distance: 58}, {type: "right", angle: 60},
                {type: "forward", distance: 58}, {type: "right", angle: 60},
                {type: "forward", distance: 58}, {type: "right", angle: 60}
            ];
        }
        return [];
    }

    function renderTaskPreview(shape) {
        const commands = taskRoute(shape);
        if (!commands.length) {
            elements.taskPreview.replaceChildren();
            return;
        }
        const route = computeGeometry(commands);
        const xs = route.points.map(point => point.x);
        const ys = route.points.map(point => point.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        const scale = Math.min(
            190 / Math.max(1, maxX - minX),
            80 / Math.max(1, maxY - minY),
            1
        );
        const offsetX = 110 - (minX + maxX) / 2 * scale;
        const offsetY = 55 + (minY + maxY) / 2 * scale;
        const points = route.points.map(point =>
            `${offsetX + point.x * scale},${offsetY - point.y * scale}`
        ).join(" ");
        elements.taskPreview.innerHTML =
            `<polyline points="${points}"></polyline>`;
    }

    function dominantTurnAngle(commands) {
        const histogram = new Map();
        commands
            .filter(command => command.type === "turn")
            .forEach(command => {
                const raw = Number(command.toHeading) - Number(command.fromHeading);
                const signed = ((raw + 180) % 360 + 360) % 360 - 180;
                const angle = Math.round(Math.abs(signed));
                histogram.set(angle, (histogram.get(angle) || 0) + 1);
            });
        return [...histogram.entries()]
            .sort((left, right) => right[1] - left[1])[0]?.[0] ?? null;
    }

    function commandGeometryStats(commands, programFeatures) {
        const moves = commands.filter(command => command.type === "move");
        const turns = commands.filter(command => command.type === "turn");
        const lastMove = moves[moves.length - 1];
        const endpoint = lastMove?.to || {x: 0, y: 0};
        const lengths = moves.map(command => Math.hypot(
            Number(command.to.x) - Number(command.from.x),
            Number(command.to.y) - Number(command.from.y)
        ));
        const averageLength = lengths.length
            ? lengths.reduce((sum, value) => sum + value, 0) / lengths.length
            : 0;
        return {
            moves: moves.length,
            turns: turns.length,
            endpoint,
            closed: Math.hypot(Number(endpoint.x), Number(endpoint.y))
                <= Math.max(2.5, averageLength * 0.06),
            turnAngle: dominantTurnAngle(commands),
            lengths,
            averageLength,
            minLength: lengths.length ? Math.min(...lengths) : 0,
            maxLength: lengths.length ? Math.max(...lengths) : 0,
            growingLengths: lengths.length > 1 && lengths[lengths.length - 1] > lengths[0] + 0.5,
            features: programFeatures || {}
        };
    }

    function evaluateActiveTask() {
        const task = tasks[state.activeTaskId];
        if (!task) return;
        const result = state.compileResult;
        if (!result?.ok) {
            renderTaskFeedback(false, ["代码还不能正常运行，请先处理错误。"]);
            return;
        }
        const expect = task.expect || {};
        const stats = commandGeometryStats(
            result.commands || [],
            result.programFeatures
        );
        const failures = [];
        const notes = [];
        const loopIterations = stats.features.loopIterations || [];

        if (expect.moves && stats.moves !== expect.moves) {
            failures.push(
                `目标需要 ${expect.moves} 次移动，当前执行了 ${stats.moves} 次。`
            );
        }
        if (expect.minMoves && stats.moves < expect.minMoves) {
            failures.push(
                `目标至少需要 ${expect.minMoves} 次移动，当前只有 ${stats.moves} 次。`
            );
        }
        if (expect.closed === true && !stats.closed) {
            failures.push(
                `图形还没有闭合：终点距原点 ${formatNumber(
                    Math.hypot(stats.endpoint.x, stats.endpoint.y)
                )}。检查所有边长和转向角度。`
            );
        }
        if (
            expect.turnAngle &&
            stats.turnAngle !== null &&
            Math.abs(stats.turnAngle - expect.turnAngle) >= 2
        ) {
            failures.push(
                `主要转向角度是 ${stats.turnAngle}°，目标应接近 ${expect.turnAngle}°。`
            );
        }
        if (
            expect.uniformSides &&
            stats.lengths.length > 1 &&
            stats.maxLength - stats.minLength > Math.max(1.5, stats.averageLength * 0.04)
        ) {
            failures.push(
                `边长不完全一致：最短 ${formatNumber(stats.minLength)}，` +
                `最长 ${formatNumber(stats.maxLength)}。`
            );
        }
        if (expect.growingLengths && !stats.growingLengths) {
            failures.push("每一轮的边长没有增加，请更新循环中使用的 length。");
        }
        if ((stats.features.loops || 0) < (expect.minLoops || 0)) {
            failures.push("这个任务需要用 for 或 while 让重复动作形成循环。");
        }
        if (
            expect.iterations &&
            loopIterations.length &&
            !loopIterations.includes(expect.iterations)
        ) {
            failures.push(
                `循环范围是 ${loopIterations.join("、")} 次，` +
                `目标应重复 ${expect.iterations} 次。`
            );
        }
        if (
            (stats.features.functions || []).length < (expect.minFunctions || 0)
        ) {
            failures.push("请把绘制步骤封装进 def 函数，然后调用这个函数。");
        }
        if (
            (stats.features.conditionals || 0) < (expect.minConditionals || 0)
        ) {
            failures.push("请使用 if 或 if/else，根据循环变量选择不同动作。");
        }

        if (expect.closed === true && stats.closed) {
            notes.push("图形终点回到起点，闭合检查通过。");
        }
        if (expect.turnAngle && stats.turnAngle !== null) {
            notes.push(`主要转向角度：${stats.turnAngle}°。`);
        }
        notes.push(`共移动 ${stats.moves} 次，平均边长 ${formatNumber(stats.averageLength)}。`);

        state.taskPassed = failures.length === 0;
        renderTaskFeedback(state.taskPassed, state.taskPassed ? notes : failures);
    }

    function renderTaskFeedback(success, messages) {
        elements.taskFeedback.classList.remove("is-success", "is-error", "is-pending");
        if (success === null) {
            elements.taskFeedback.textContent =
                "修改代码后点击“运行代码”或“检查”。";
            elements.taskFeedback.classList.add("is-pending");
            return;
        }
        elements.taskFeedback.classList.add(success ? "is-success" : "is-error");
        const heading = success ? "逻辑检查通过" : "逻辑检查还有差异";
        elements.taskFeedback.innerHTML =
            `<strong>${heading}</strong>` +
            messages.map(message => `<span>${escapeText(message)}</span>`).join("");
    }

    function renderExecutionStep(index) {
        const steps = state.compileResult?.steps || [];
        if (!steps.length) {
            resetExecution();
            return;
        }
        const safeIndex = Math.max(0, Math.min(steps.length - 1, index));
        state.executionIndex = safeIndex;
        const activeMoment = state.moments.find(
            moment =>
                moment.step_index !== null &&
                moment.step_index !== undefined &&
                Number(moment.step_index) === safeIndex
        );
        state.activeMomentId = activeMoment ? activeMoment.id : null;
        updateMomentActiveState();
        state.previewCleared = false;
        const step = steps[safeIndex];
        drawScene(
            geometryFromCompileStep(step),
            geometryFromCommands(state.compileResult?.commands || [])
        );
        elements.commandCount.textContent = String(step.commandCount || 0);
        const {length, angle} = stepDisplayValues(step);
        const heading = Number(step.turtle?.heading || 0);
        setTurtleReadouts({
            length,
            angle,
            heading,
            penDown: step.turtle?.penDown
        });
        elements.compileStatus.textContent =
            `步骤 ${safeIndex + 1}/${steps.length}`;
        renderVariables(step);
        renderNarration(step);
        setExecutionHighlight(step.line, false);
        if (safeIndex === steps.length - 1) {
            state.playing = false;
            elements.playExecution.textContent = "继续";
            elements.playExecution.classList.remove("is-active");
        }
    }

    function momentLines() {
        if (!state.momentsEnabled) return new Set();
        return new Set(
            state.moments
                .map(moment => Number(moment.line))
                .filter(line => Number.isFinite(line) && line > 0)
        );
    }

    function renderMomentRail() {
        if (!elements.momentRail) return;
        if (!state.momentsEnabled) {
            elements.momentRail.hidden = false;
            elements.momentRailCount.textContent = "已关闭";
            elements.momentRailList.replaceChildren();
            return;
        }
        const moments = state.moments.filter(moment => moment && moment.id);
        elements.momentRail.hidden = moments.length === 0;
        elements.momentRailCount.textContent = moments.length
            ? `${moments.length} 个`
            : "";
        if (!moments.length) {
            elements.momentRailList.replaceChildren();
            return;
        }
        const fragment = document.createDocumentFragment();
        moments.forEach(moment => {
            const card = document.createElement("button");
            card.type = "button";
            card.className = `moment-card moment-card--${moment.severity || "info"}`;
            card.dataset.momentId = moment.id;
            card.title = moment.why || moment.label || "";
            if (moment.id === state.activeMomentId) {
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
            const hasStep =
                moment.step_index !== null &&
                moment.step_index !== undefined &&
                Number.isFinite(Number(moment.step_index));
            meta.textContent = hasStep
                ? `第 ${Number(moment.step_index) + 1} 步`
                : "";
            card.append(label, why, meta);
            card.addEventListener("click", () => {
                if (hasStep) {
                    renderExecutionStep(Number(moment.step_index));
                }
                state.activeMomentId = moment.id;
                updateMomentActiveState();
            });
            fragment.appendChild(card);
        });
        elements.momentRailList.replaceChildren(fragment);
    }

    function updateMomentActiveState() {
        if (!elements.momentRailList) return;
        elements.momentRailList.querySelectorAll(".moment-card").forEach(card => {
            card.classList.toggle(
                "is-active",
                card.dataset.momentId === state.activeMomentId
            );
        });
    }

    function nextMoment() {
        const moments = state.moments.filter(moment => moment && moment.id);
        if (!moments.length) return;
        const currentIndex = moments.findIndex(
            moment => moment.id === state.activeMomentId
        );
        const next = moments[(currentIndex + 1) % moments.length];
        if (next.step_index !== null && next.step_index !== undefined) {
            const stepIndex = Number(next.step_index);
            if (Number.isFinite(stepIndex)) {
                renderExecutionStep(stepIndex);
            }
        }
        state.activeMomentId = next.id;
        updateMomentActiveState();
    }

    function scheduleMomentEnrichment() {
        window.clearTimeout(state.momentEnrichTimer);
        if (!state.momentsEnabled || !state.moments.length) return;
        const requestId = state.momentEnrichRequest;
        const source = elements.studentSource.value;
        state.momentEnrichTimer = window.setTimeout(() => {
            void enrichMomentCopy(requestId, source);
        }, 800);
    }

    async function enrichMomentCopy(requestId, source) {
        if (requestId !== state.momentEnrichRequest || !state.moments.length) return;
        try {
            const response = await fetch("/api/breakpoints/enrich", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    world: "turtle",
                    code: source,
                    moments: state.moments
                })
            });
            if (!response.ok) return;
            const payload = await response.json();
            if (requestId !== state.momentEnrichRequest) return;
            const enriched = Array.isArray(payload.moments) ? payload.moments : [];
            if (!enriched.some(moment => moment && moment.enriched)) return;
            const byId = new Map(
                enriched
                    .filter(moment => moment && moment.id)
                    .map(moment => [moment.id, moment])
            );
            state.moments = state.moments.map(moment => {
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
            if (elements.momentSource) {
                elements.momentSource.textContent = "本地规则 + AI 文案";
            }
            renderMomentRail();
        } catch (error) {
            // Keep rule-based copy when the optional enrichment fails.
        }
    }

    function pausePlayback() {
        window.clearTimeout(state.playbackTimer);
        state.playing = false;
        elements.playExecution.textContent = "继续";
        elements.playExecution.classList.remove("is-active");
    }

    function resetExecution() {
        pausePlayback();
        state.executionIndex = -1;
        state.previewCleared = true;
        drawScene({
            x: 0,
            y: 0,
            heading: 0,
            penDown: true,
            points: [{x: 0, y: 0}],
            segments: []
        });
        elements.commandCount.textContent = "0";
        setTurtleReadouts();
        renderVariables(null);
        renderNarration(null);
        setExecutionHighlight(null);
        elements.compileStatus.textContent = state.compileResult?.error
            ? (
                state.compileResult.error.category === "syntax"
                    ? "语法错误"
                    : "运行错误"
            )
            : (
                state.compileResult?.ok
                    ? `就绪 · ${state.compileResult.steps.length} 步`
                    : "等待运行"
            );
    }

    function stepExecution() {
        pausePlayback();
        const steps = state.compileResult?.steps || [];
        if (!steps.length) return;
        const next = state.executionIndex < 0
            ? 0
            : Math.min(steps.length - 1, state.executionIndex + 1);
        renderExecutionStep(next);
    }

    function playbackTick() {
        if (!state.playing) return;
        const steps = state.compileResult?.steps || [];
        const next = state.executionIndex + 1;
        if (next >= steps.length) {
            pausePlayback();
            return;
        }
        renderExecutionStep(next);
        if (state.breakpoints.has(Number(steps[next].line))) {
            pausePlayback();
            elements.compileStatus.textContent =
                `断点停在第 ${steps[next].line} 行`;
            return;
        }
        const speed = playbackSpeeds[Number(elements.playbackSpeed.value)] || 1;
        state.playbackTimer = window.setTimeout(
            playbackTick,
            Math.max(80, 620 / speed)
        );
    }

    function togglePlayback() {
        if (state.playing) {
            pausePlayback();
            return;
        }
        const steps = state.compileResult?.steps || [];
        if (!steps.length) return;
        if (state.executionIndex >= steps.length - 1) {
            state.executionIndex = -1;
        }
        state.playing = true;
        elements.playExecution.textContent = "暂停";
        elements.playExecution.classList.add("is-active");
        playbackTick();
    }

    function fullSpeedExecution() {
        pausePlayback();
        const steps = state.compileResult?.steps || [];
        if (!steps.length) return;
        renderExecutionStep(steps.length - 1);
        elements.compileStatus.textContent = "全速完成";
    }

    function refresh() {
        const geometry = computeGeometry(state.commands);
        const generated = generateCode(state.commands);
        if (state.sourceMode === "auto") {
            const simplified = generateSimplifiedSource(state.commands);
            if (elements.studentSource.value !== simplified) {
                elements.studentSource.value = simplified;
                updateStudentLineNumbers();
            }
            scheduleCompile(180);
        }
        elements.commandCount.textContent = String(state.commands.length);
        setTurtleReadouts({
            length: state.distance,
            angle: state.angle,
            heading: geometry.heading,
            penDown: geometry.penDown
        });
        renderHistory();
        renderPattern(generated.pattern);
        if (state.sourceMode === "auto") {
            state.previewCleared = false;
            drawScene(geometry);
        }
    }

    function renderHistory() {
        elements.commandHistory.innerHTML = "";
        if (!state.commands.length) {
            const item = document.createElement("li");
            item.className = "command-empty";
            item.textContent = "还没有动作";
            elements.commandHistory.appendChild(item);
            return;
        }
        state.commands.forEach((command, index) => {
            const item = document.createElement("li");
            item.textContent = `${index + 1}. ${commandLabel(command)}`;
            elements.commandHistory.appendChild(item);
        });
        elements.commandHistory.scrollLeft = elements.commandHistory.scrollWidth;
    }

    function commandLabel(command) {
        if (command.type === "forward") return `forward(${formatNumber(command.distance)})`;
        if (command.type === "back") return `back(${formatNumber(command.distance)})`;
        if (command.type === "left") return `left(${formatNumber(command.angle)})`;
        if (command.type === "right") return `right(${formatNumber(command.angle)})`;
        if (command.type === "face_move") {
            return (
                `setheading(${formatNumber(command.heading)}) · ` +
                `forward(${formatNumber(command.distance)})`
            );
        }
        return command.down ? "pendown()" : "penup()";
    }

    function renderPattern(pattern) {
        elements.patternResult.classList.toggle("is-matched", Boolean(pattern));
        if (!pattern) {
            elements.patternResult.innerHTML =
                '<span class="pattern-dot"></span>还没有可匹配的重复图形';
            return;
        }
        const patternLabel = pattern.pattern.map(commandLabel).join(" → ");
        elements.patternResult.innerHTML =
            `<span class="pattern-dot"></span>匹配到“${escapeText(patternLabel)}”重复 ` +
            `${pattern.repeats} 次，已转换为 for 循环`;
    }

    function escapeText(value) {
        const div = document.createElement("div");
        div.textContent = String(value);
        return div.innerHTML;
    }

    function resizeCanvas() {
        const bounds = canvas.getBoundingClientRect();
        const ratio = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.max(1, Math.round(bounds.width * ratio));
        canvas.height = Math.max(1, Math.round(bounds.height * ratio));
        context.setTransform(ratio, 0, 0, ratio, 0, 0);
        redrawCurrentScene();
    }

    function currentSceneGeometry() {
        if (state.previewCleared) {
            return {
                x: 0,
                y: 0,
                heading: 0,
                penDown: true,
                points: [{x: 0, y: 0}],
                segments: [],
                fills: []
            };
        }
        const step = state.compileResult?.steps?.[state.executionIndex];
        if (step) return geometryFromCompileStep(step);
        return computeGeometry(state.commands);
    }

    function currentViewGeometry() {
        const step = state.compileResult?.steps?.[state.executionIndex];
        if (step) {
            return geometryFromCommands(state.compileResult?.commands || []);
        }
        return currentSceneGeometry();
    }

    function redrawCurrentScene() {
        drawScene(currentSceneGeometry(), currentViewGeometry());
    }

    function fitSceneViewport(points, width, height) {
        const xs = points.map(point => Number(point.x) || 0);
        const ys = points.map(point => Number(point.y) || 0);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        const spanX = Math.max(0.001, maxX - minX);
        const spanY = Math.max(0.001, maxY - minY);
        const paddingX = Math.min(80, Math.max(36, width * 0.12));
        const paddingY = Math.min(72, Math.max(36, height * 0.16));
        const scale = Math.max(0.00001, Math.min(
            3.2,
            Math.max(0.001, width - paddingX * 2) / spanX,
            Math.max(0.001, height - paddingY * 2) / spanY
        ));
        return {
            scale,
            originX: width / 2 - ((minX + maxX) / 2) * scale,
            originY: height / 2 + ((minY + maxY) / 2) * scale
        };
    }

    function sceneBoundsPoints(viewGeometry, currentGeometry) {
        const points = [];
        (viewGeometry.segments || []).forEach(segment => {
            points.push(segment.from, segment.to);
        });
        (viewGeometry.fills || []).forEach(fill => {
            points.push(...(fill.points || []));
        });
        points.push({x: currentGeometry.x, y: currentGeometry.y});
        if (!points.length) points.push({x: 0, y: 0});
        return points;
    }

    function drawScene(geometry, viewGeometry = geometry) {
        const bounds = canvas.getBoundingClientRect();
        const width = bounds.width;
        const height = bounds.height;
        if (!width || !height) return;
        context.clearRect(0, 0, width, height);

        const allPoints = sceneBoundsPoints(viewGeometry, geometry);
        const {scale, originX, originY} = fitSceneViewport(
            allPoints,
            width,
            height
        );
        canvas.dataset.viewScale = String(scale);
        canvas.dataset.viewBounds =
            `${Math.min(...allPoints.map(point => point.x))},` +
            `${Math.min(...allPoints.map(point => point.y))},` +
            `${Math.max(...allPoints.map(point => point.x))},` +
            `${Math.max(...allPoints.map(point => point.y))}`;
        const toScreen = point => ({
            x: originX + point.x * scale,
            y: originY - point.y * scale
        });

        context.save();
        context.lineCap = "round";
        context.lineJoin = "round";
        (geometry.fills || []).forEach(fill => {
            if (!fill.points?.length) return;
            context.beginPath();
            fill.points.forEach((point, index) => {
                const screenPoint = toScreen(point);
                if (index === 0) context.moveTo(screenPoint.x, screenPoint.y);
                else context.lineTo(screenPoint.x, screenPoint.y);
            });
            context.closePath();
            context.fillStyle = fill.color || state.fillColor;
            context.fill();
        });
        if (state.showTrail) {
            geometry.segments.forEach(segment => {
                const from = toScreen(segment.from);
                const to = toScreen(segment.to);
                context.strokeStyle = segment.color || "#3370ff";
                context.lineWidth = Number(segment.size) || 2.6;
                context.beginPath();
                context.moveTo(from.x, from.y);
                context.lineTo(to.x, to.y);
                context.stroke();
            });
        }
        context.restore();

        const cursor = toScreen({x: geometry.x, y: geometry.y});
        drawArrow(cursor.x, cursor.y, Math.PI / 2 - geometry.heading);
    }

    function drawArrow(x, y, rotation) {
        context.save();
        context.translate(x, y);
        context.rotate(rotation);
        context.strokeStyle = "#3370ff";
        context.fillStyle = "#3370ff";
        context.lineWidth = 2.2;
        context.lineCap = "round";
        context.lineJoin = "round";
        context.beginPath();
        context.moveTo(0, 15);
        context.lineTo(0, -12);
        context.stroke();
        context.beginPath();
        context.moveTo(0, -20);
        context.lineTo(-7, -10);
        context.lineTo(0, -13);
        context.lineTo(7, -10);
        context.closePath();
        context.fill();
        context.restore();
    }

    function showToast(message) {
        window.clearTimeout(state.toastTimer);
        elements.toast.textContent = message;
        elements.toast.classList.add("is-visible");
        state.toastTimer = window.setTimeout(() => {
            elements.toast.classList.remove("is-visible");
        }, 1800);
    }

    async function copyCode() {
        const code = displayedGeneratedCode(state.generatedCode);
        try {
            await navigator.clipboard.writeText(code);
            showToast("Python 代码已复制");
        } catch (error) {
            const fallback = document.createElement("textarea");
            fallback.value = code;
            fallback.style.position = "fixed";
            fallback.style.opacity = "0";
            document.body.appendChild(fallback);
            fallback.select();
            document.execCommand("copy");
            fallback.remove();
            showToast("Python 代码已复制");
        }
    }

    function loadSavedWorks() {
        try {
            const stored = JSON.parse(localStorage.getItem(WORK_STORAGE_KEY) || "[]");
            state.works = Array.isArray(stored)
                ? stored.filter(work => work && work.id && work.name)
                : [];
        } catch (error) {
            state.works = [];
        }
        renderWorkList();
    }

    function persistSavedWorks() {
        try {
            localStorage.setItem(WORK_STORAGE_KEY, JSON.stringify(state.works));
            return true;
        } catch (error) {
            showToast("浏览器本地存储已满，请先删除旧作品");
            return false;
        }
    }

    function renderWorkList() {
        const fragment = document.createDocumentFragment();
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "选择已保存作品";
        fragment.appendChild(placeholder);
        [...state.works]
            .sort((left, right) => Number(right.updatedAt) - Number(left.updatedAt))
            .forEach(work => {
                const option = document.createElement("option");
                option.value = work.id;
                option.textContent = work.name;
                fragment.appendChild(option);
            });
        elements.workList.replaceChildren(fragment);
        elements.workList.value = state.activeWorkId || "";
    }

    function saveCurrentWork() {
        const name = elements.workName.value.trim() || "未命名 Turtle 作品";
        const now = Date.now();
        let work = state.works.find(item => item.id === state.activeWorkId);
        if (!work) {
            work = {
                id: `work-${now}-${Math.random().toString(36).slice(2, 7)}`,
                createdAt: now
            };
            state.works.push(work);
        }
        Object.assign(work, {
            name,
            updatedAt: now,
            source: elements.studentSource.value,
            taskId: state.activeTaskId,
            commands: state.commands.map(command => ({...command})),
            distance: state.distance,
            angle: state.angle,
            penColor: state.penColor,
            penSize: state.penSize,
            fillColor: state.fillColor,
            generatedCode: state.generatedCode,
            image: canvas.toDataURL("image/png")
        });
        if (!persistSavedWorks()) return;
        state.activeWorkId = work.id;
        elements.workName.value = name;
        renderWorkList();
        showToast(`已保存“${name}”`);
    }

    function loadSelectedWork() {
        const work = state.works.find(item => item.id === elements.workList.value);
        if (!work) return;
        pausePlayback();
        state.activeWorkId = work.id;
        elements.workName.value = work.name;
        state.distance = Number(work.distance) || 60;
        state.angle = Number(work.angle) || 90;
        state.penColor = work.penColor || "#3370ff";
        state.penSize = Number(work.penSize) || 2;
        state.fillColor = work.fillColor || "#3370ff";
        elements.penColorInput.value = state.penColor;
        elements.penSizeInput.value = String(state.penSize);
        elements.penSizeValue.textContent = String(state.penSize);
        elements.fillColorInput.value = state.fillColor;
        state.commands = Array.isArray(work.commands)
            ? work.commands.map(command => ({...command}))
            : [];
        state.activeTaskId = work.taskId || "";
        if (tasks[state.activeTaskId]) {
            elements.taskSelect.value = state.activeTaskId;
            elements.taskDescription.textContent =
                tasks[state.activeTaskId].description;
            renderTaskPreview(tasks[state.activeTaskId].shape);
            renderTaskFeedback(null, []);
        }
        setStudentSource(String(work.source || ""), {
            manual: true,
            compileNow: true
        });
        showToast(`已打开“${work.name}”`);
    }

    function deleteSelectedWork() {
        const selectedId = elements.workList.value || state.activeWorkId;
        const work = state.works.find(item => item.id === selectedId);
        if (!work) {
            showToast("请先选择要删除的作品");
            return;
        }
        state.works = state.works.filter(item => item.id !== work.id);
        if (state.activeWorkId === work.id) state.activeWorkId = "";
        if (!persistSavedWorks()) return;
        renderWorkList();
        showToast(`已删除“${work.name}”`);
    }

    function safeFilename(value, fallback) {
        const cleaned = String(value || "")
            .replace(/[\\/:*?"<>|]+/g, "-")
            .replace(/\s+/g, " ")
            .trim();
        return cleaned || fallback;
    }

    function downloadUrl(url, filename) {
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
    }

    function exportCanvasPng() {
        const exportCanvas = document.createElement("canvas");
        exportCanvas.width = canvas.width;
        exportCanvas.height = canvas.height;
        const exportContext = exportCanvas.getContext("2d");
        exportContext.fillStyle = "#f7f8fa";
        exportContext.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
        exportContext.drawImage(canvas, 0, 0);
        downloadUrl(
            exportCanvas.toDataURL("image/png"),
            `${safeFilename(elements.workName.value, "turtle")}.png`
        );
    }

    function exportPythonCode() {
        const code = displayedGeneratedCode(state.generatedCode);
        if (!code.trim()) {
            showToast("还没有可导出的 Python 代码");
            return;
        }
        const blob = new Blob(
            [code, code.endsWith("\n") ? "" : "\n"],
            {type: "text/x-python;charset=utf-8"}
        );
        const url = URL.createObjectURL(blob);
        downloadUrl(
            url,
            `${safeFilename(elements.workName.value, "turtle")}.py`
        );
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    function applyControlWidth(width) {
        if (!elements.workspace) return;
        const maximum = Math.max(
            220,
            Math.min(390, elements.workspace.clientWidth - 500)
        );
        state.controlWidth = Math.max(210, Math.min(maximum, width));
        elements.workspace.style.setProperty(
            "--control-width",
            `${Math.round(state.controlWidth)}px`
        );
        resizeCanvas();
    }

    function applyVariableWidth(width) {
        if (!elements.workspace) return;
        const maximum = Math.max(
            190,
            Math.min(360, elements.workspace.clientWidth - 600)
        );
        state.variableWidth = Math.max(170, Math.min(maximum, width));
        elements.workspace.style.setProperty(
            "--variable-width",
            `${Math.round(state.variableWidth)}px`
        );
        resizeCanvas();
    }

    function applyCodeHeight(height) {
        if (!elements.studio) return;
        const maximum = Math.max(
            150,
            Math.min(430, elements.studio.clientHeight - 190)
        );
        state.codeHeight = Math.max(150, Math.min(maximum, height));
        elements.studio.style.setProperty(
            "--code-height",
            `${Math.round(state.codeHeight)}px`
        );
        resizeCanvas();
    }

    function setStepLength(value) {
        const next = Math.max(
            20,
            Math.min(120, Math.round(Number(value) / 10) * 10)
        );
        state.distance = next;
        elements.currentLengthValue.textContent = String(next);
    }

    function setTurnAngle(value) {
        const next = Math.max(1, Math.min(180, Math.round(Number(value))));
        state.angle = next;
        elements.currentAngleValue.textContent = `${next}°`;
    }

    function setPenState(down) {
        const geometry = computeGeometry(state.commands);
        if (geometry.penDown === Boolean(down)) return;
        addCommand({type: "pen", down: Boolean(down)});
    }

    function setControlCollapsed(collapsed) {
        elements.workspace.classList.toggle("is-control-collapsed", collapsed);
        elements.collapseControlPanel.hidden = collapsed;
        elements.openControlPanel.hidden = !collapsed;
        window.requestAnimationFrame(resizeCanvas);
    }

    function setVariableCollapsed(collapsed) {
        elements.workspace.classList.toggle("is-variable-collapsed", collapsed);
        elements.collapseVariablePanel.hidden = collapsed;
        elements.openVariablePanel.hidden = !collapsed;
        window.requestAnimationFrame(resizeCanvas);
    }

    function toggleCodePanel() {
        const collapsed = !elements.studio.classList.contains("is-code-collapsed");
        elements.studio.classList.toggle("is-code-collapsed", collapsed);
        elements.toggleCodePanel.textContent = collapsed ? "展开" : "收起";
        elements.toggleCodePanel.setAttribute(
            "aria-label",
            collapsed ? "展开代码面板" : "收起代码面板"
        );
        window.requestAnimationFrame(resizeCanvas);
    }

    function bindDragResize(handle, cursor, axis, readValue, writeValue) {
        if (!handle) return;
        handle.addEventListener("pointerdown", event => {
            if (window.matchMedia("(max-width: 900px)").matches) return;
            event.preventDefault();
            document.body.classList.add("is-resizing");
            document.body.style.cursor = cursor;
            const horizontal = axis === "x" || axis === "x-reverse";
            const startCoordinate = horizontal ? event.clientX : event.clientY;
            const startValue = readValue();
            const finish = () => {
                document.body.classList.remove("is-resizing");
                document.body.style.cursor = "";
                window.removeEventListener("pointermove", move);
                window.removeEventListener("pointerup", finish);
                window.removeEventListener("pointercancel", finish);
            };
            const move = moveEvent => {
                const currentCoordinate =
                    horizontal ? moveEvent.clientX : moveEvent.clientY;
                const delta = axis === "x"
                    ? currentCoordinate - startCoordinate
                    : axis === "x-reverse"
                        ? startCoordinate - currentCoordinate
                        : startCoordinate - currentCoordinate;
                writeValue(startValue + delta);
            };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", finish);
            window.addEventListener("pointercancel", finish);
        });
    }

    function initPanelResizing() {
        bindDragResize(
            elements.controlResizeHandle,
            "col-resize",
            "x",
            () => state.controlWidth,
            applyControlWidth
        );
        bindDragResize(
            elements.codeResizeHandle,
            "row-resize",
            "y",
            () => state.codeHeight,
            applyCodeHeight
        );
        bindDragResize(
            elements.variableResizeHandle,
            "col-resize",
            "x-reverse",
            () => state.variableWidth,
            applyVariableWidth
        );

        elements.controlResizeHandle?.addEventListener("keydown", event => {
            if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
            event.preventDefault();
            applyControlWidth(
                state.controlWidth + (event.key === "ArrowRight" ? 16 : -16)
            );
        });
        elements.codeResizeHandle?.addEventListener("keydown", event => {
            if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
            event.preventDefault();
            applyCodeHeight(
                state.codeHeight + (event.key === "ArrowUp" ? 16 : -16)
            );
        });
        elements.variableResizeHandle?.addEventListener("keydown", event => {
            if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
            event.preventDefault();
            applyVariableWidth(
                state.variableWidth + (event.key === "ArrowLeft" ? 16 : -16)
            );
        });
        elements.controlResizeHandle?.addEventListener("dblclick", () => {
            applyControlWidth(256);
        });
        elements.codeResizeHandle?.addEventListener("dblclick", () => {
            applyCodeHeight(280);
        });
        elements.variableResizeHandle?.addEventListener("dblclick", () => {
            applyVariableWidth(238);
        });
    }

    elements.collapseControlPanel.addEventListener("click", () => {
        setControlCollapsed(true);
    });
    elements.openControlPanel.addEventListener("click", () => {
        setControlCollapsed(false);
    });
    elements.collapseVariablePanel.addEventListener("click", () => {
        setVariableCollapsed(true);
    });
    elements.openVariablePanel.addEventListener("click", () => {
        setVariableCollapsed(false);
    });
    elements.toggleCodePanel.addEventListener("click", toggleCodePanel);
    elements.applyStudentCode.addEventListener("click", () => {
        state.taskAwaitingCheck = Boolean(state.activeTaskId);
        state.compileRequest += 1;
        void compileStudentSource(state.compileRequest);
    });
    elements.checkTask.addEventListener("click", () => {
        if (!state.activeTaskId) {
            showToast("请先选择并载入练习任务");
            return;
        }
        state.taskAwaitingCheck = true;
        state.compileRequest += 1;
        void compileStudentSource(state.compileRequest);
    });
    elements.loadTask.addEventListener("click", loadActiveTask);
    elements.taskSelect.addEventListener("change", () => {
        state.hintLevel = 0;
        elements.taskHint.textContent =
            elements.taskSelect.value ? "点击“载入”开始练习。" : "需要时逐层查看提示。";
        elements.taskHint.classList.remove("is-code");
    });
    document.querySelectorAll("[data-task-hint]").forEach(button => {
        button.addEventListener("click", () => {
            const task = tasks[state.activeTaskId || elements.taskSelect.value];
            if (!task) {
                showToast("请先载入一个练习任务");
                return;
            }
            const level = Math.max(
                1,
                Math.min(3, Number(button.dataset.taskHint))
            );
            state.hintLevel = level;
            const message = task.hints[level - 1];
            elements.taskHint.classList.toggle("is-code", level === 3);
            elements.taskHint.innerHTML = level === 3
                ? `<strong>结构片段</strong><pre>${escapeText(message)}</pre>`
                : `<strong>提示 ${level}</strong><span>${escapeText(message)}</span>`;
        });
    });
    elements.copyCode.addEventListener("click", copyCode);
    elements.resetExecution.addEventListener("click", resetExecution);
    elements.clearWorkspace?.addEventListener("click", clearWorkspace);
    elements.stepExecution.addEventListener("click", stepExecution);
    elements.playExecution.addEventListener("click", togglePlayback);
    elements.fullSpeedExecution.addEventListener("click", fullSpeedExecution);
    elements.momentNext?.addEventListener("click", nextMoment);
    elements.momentToggle?.addEventListener("click", () => {
        state.momentsEnabled = !state.momentsEnabled;
        elements.momentToggle.setAttribute(
            "aria-pressed",
            String(state.momentsEnabled)
        );
        elements.momentToggle.textContent = state.momentsEnabled
            ? "智能断点"
            : "智能断点（关）";
        renderMomentRail();
        updateStudentLineNumbers();
        if (state.momentsEnabled) scheduleMomentEnrichment();
    });
    elements.playbackSpeed.addEventListener("input", () => {
        const speed = playbackSpeeds[Number(elements.playbackSpeed.value)] || 1;
        elements.playbackSpeedValue.textContent = `${speed}x`;
    });
    elements.studentSource.addEventListener("input", () => {
        const wasAuto = state.sourceMode === "auto";
        state.sourceMode = "manual";
        if (wasAuto) {
            state.commands = [];
            state.filling = false;
            renderHistory();
            renderPattern(null);
        }
        if (state.activeTaskId) {
            state.taskAwaitingCheck = false;
            state.taskPassed = false;
            renderTaskFeedback(null, []);
        }
        updateStudentLineNumbers();
        scheduleCompile(320);
    });
    elements.studentLineNumbers.addEventListener("click", event => {
        const lineNumber = event.target.closest(".student-line-number");
        if (!lineNumber) return;
        const line = Number(lineNumber.dataset.line);
        if (state.breakpoints.has(line)) state.breakpoints.delete(line);
        else state.breakpoints.add(line);
        updateStudentLineNumbers();
    });
    elements.studentSource.addEventListener("mousemove", event => {
        const bounds = elements.studentSource.getBoundingClientRect();
        const line = Math.max(
            1,
            Math.floor(
                (event.clientY - bounds.top + elements.studentSource.scrollTop) /
                16.8
            ) + 1
        );
        highlightLinkedLine(line);
    });
    elements.studentSource.addEventListener("mouseleave", clearLinkedLine);
    elements.studentSource.addEventListener("scroll", () => {
        elements.studentLineNumbers.scrollTop = elements.studentSource.scrollTop;
        clearLinkedLine();
        setStudentHighlight(
            state.highlightedSourceLine,
            state.highlightedSourceIsError,
            false
        );
    });
    elements.generatedCode.addEventListener("mouseover", event => {
        const line = event.target.closest(".code-line");
        if (!line?.dataset.sourceLine) return;
        highlightLinkedLine(Number(line.dataset.sourceLine));
    });
    elements.generatedCode.addEventListener("mouseleave", clearLinkedLine);
    elements.narrationEnabled.addEventListener("change", () => {
        const step = state.compileResult?.steps?.[state.executionIndex];
        renderNarration(step || null);
    });
    elements.penColorInput.addEventListener("change", () => {
        setPenColor(elements.penColorInput.value);
    });
    elements.penSizeInput.addEventListener("input", () => {
        elements.penSizeValue.textContent = elements.penSizeInput.value;
    });
    elements.penSizeInput.addEventListener("change", () => {
        setPenSize(elements.penSizeInput.value);
    });
    elements.fillColorInput.addEventListener("change", () => {
        setFillColor(elements.fillColorInput.value);
    });
    elements.beginFill.addEventListener("click", beginFill);
    elements.endFill.addEventListener("click", endFill);
    elements.interactiveCodeToggle.addEventListener("change", () => {
        state.interactiveCode = elements.interactiveCodeToggle.checked;
        if (state.compileResult) {
            renderGeneratedCode(
                displayedGeneratedCode(state.generatedCode),
                state.compileResult.lineMap || {}
            );
            setExecutionHighlight(
                state.compileResult.steps?.[state.executionIndex]?.line || null
            );
        }
        showToast(
            state.interactiveCode
                ? "已加入方向键和点击事件代码"
                : "已恢复普通绘图代码"
        );
    });
    elements.trailEnabled.addEventListener("change", () => {
        state.showTrail = elements.trailEnabled.checked;
        redrawCurrentScene();
    });
    elements.saveWork.addEventListener("click", saveCurrentWork);
    elements.workList.addEventListener("change", loadSelectedWork);
    elements.deleteWork.addEventListener("click", deleteSelectedWork);
    elements.exportPng.addEventListener("click", exportCanvasPng);
    elements.exportPython.addEventListener("click", exportPythonCode);
    canvas.addEventListener("pointerdown", () => {
        canvas.focus({preventScroll: true});
    });

    document.addEventListener("keydown", event => {
        const editable = event.target.closest?.(
            "input, select, textarea, [contenteditable='true'], [role='separator']"
        );
        if (event.key === "Escape" && editable) {
            event.preventDefault();
            editable.blur?.();
            canvas.focus({preventScroll: true});
            return;
        }
        if (editable) {
            return;
        }
        if (event.repeat) {
            const repeatedShortcut = [
                "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
                "[", "]", "-", "=", "+", " ", "F5", "F6", "F8",
                "p", "P", "u", "U", "d", "D", "c", "C", "s", "S",
                "q", "Q", "e", "E", "z", "Z"
            ].includes(event.key);
            if (repeatedShortcut) event.preventDefault();
            return;
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
            event.preventDefault();
            undo();
            return;
        }
        if (event.key === "F8") {
            event.preventDefault();
            stepExecution();
            return;
        }
        if (event.key === "F5") {
            event.preventDefault();
            togglePlayback();
            return;
        }
        if (event.key === "F6") {
            event.preventDefault();
            resetExecution();
            return;
        }
        if (event.shiftKey && event.key.startsWith("Arrow")) {
            event.preventDefault();
            if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                setStepLength(
                    state.distance + (event.key === "ArrowUp" ? 10 : -10)
                );
            } else {
                setTurnAngle(
                    state.angle + (event.key === "ArrowRight" ? 5 : -5)
                );
            }
            return;
        }
        const actions = {
            ArrowUp: 90,
            ArrowDown: 270,
            ArrowLeft: 180,
            ArrowRight: 0
        };
        if (Object.prototype.hasOwnProperty.call(actions, event.key)) {
            event.preventDefault();
            moveInDirection(actions[event.key]);
            return;
        }
        if (
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey &&
            (event.key === "[" || event.key === "]")
        ) {
            event.preventDefault();
            setTurnAngle(
                state.angle + (event.key === "]" ? 5 : -5)
            );
            return;
        }
        if (
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey &&
            (event.key === "-" || event.key === "=" || event.key === "+")
        ) {
            event.preventDefault();
            setStepLength(
                state.distance + (event.key === "-" ? -10 : 10)
            );
            return;
        }
        if (
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey &&
            (event.key.toLowerCase() === "q" || event.key.toLowerCase() === "e")
        ) {
            event.preventDefault();
            turn(event.key.toLowerCase() === "q" ? "left" : "right");
            return;
        }
        if (
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey &&
            event.key.toLowerCase() === "p"
        ) {
            event.preventDefault();
            togglePen();
            return;
        }
        if (
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey &&
            (event.key.toLowerCase() === "u" || event.key.toLowerCase() === "d")
        ) {
            event.preventDefault();
            setPenState(event.key.toLowerCase() === "d");
            return;
        }
        if (
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey &&
            event.key.toLowerCase() === "c"
        ) {
            event.preventDefault();
            clear();
            return;
        }
        if (
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey &&
            event.key.toLowerCase() === "s"
        ) {
            event.preventDefault();
            drawSquare();
            return;
        }
        if (event.code === "Space") {
            event.preventDefault();
            togglePen();
        }
    });

    initPanelResizing();
    new ResizeObserver(resizeCanvas).observe(canvas);
    window.addEventListener("resize", () => {
        applyControlWidth(state.controlWidth);
        applyVariableWidth(state.variableWidth);
        applyCodeHeight(state.codeHeight);
    });
    populateTasks();
    loadSavedWorks();
    refresh();
    resetExecution();
    resizeCanvas();
    window.requestAnimationFrame(() => canvas.focus({preventScroll: true}));
})();
