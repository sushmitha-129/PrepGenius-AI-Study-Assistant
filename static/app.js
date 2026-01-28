function switchPage(pageId) {
    document.querySelectorAll(".page").forEach(p => {
        p.classList.toggle("visible", p.id === "page-" + pageId);
    });
    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.page === pageId);
    });
}

function downloadOutput(elementId, filename) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.textContent.trim();
    if (!text) {
        alert("Nothing to download yet.");
        return;
    }
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

async function loadDashboard() {
    try {
        const res = await fetch("/api/dashboard");
        const data = await res.json();
        document.getElementById("dayStreak").textContent = data.dayStreak ?? 0;
        document.getElementById("notesCreated").textContent = data.notesCreated ?? 0;
        document.getElementById("quizzesTaken").textContent = data.quizzesTaken ?? 0;

        const done = data.todayActions ?? 0;
        const goal = data.dailyGoal ?? 4;
        document.getElementById("goalBar").style.width = (data.goalProgress ?? 0) + "%";
        document.getElementById("goalSubtitle").textContent =
            `${done} out of ${goal} tasks completed. Keep it up!`;
    } catch (e) {
        console.error("Dashboard error", e);
    }
}

async function loadHistory() {
    const empty = document.getElementById("historyEmpty");
    const list = document.getElementById("historyList");
    empty.textContent = "Loading...";
    list.innerHTML = "";
    try {
        const res = await fetch("/api/history");
        const data = await res.json();
        const items = data.items || [];
        if (!items.length) {
            empty.textContent = "No activity yet. Start by generating notes or a quiz!";
            return;
        }
        empty.textContent = "";
        items.forEach(item => {
            const li = document.createElement("li");
            li.className = "history-item";
            const d = new Date(item.createdAt);
            li.innerHTML = `
                <div class="history-kind">${item.kind}</div>
                <div class="history-title">${item.title}</div>
                <div class="history-time">${d.toLocaleString()}</div>
            `;
            list.appendChild(li);
        });
    } catch (e) {
        console.error("History error", e);
        empty.textContent = "Could not load history.";
    }
}

function renderQuiz(questions) {
    const out = document.getElementById("quizOutput");
    out.innerHTML = "";

    if (!questions.length) {
        out.textContent = "No questions generated.";
        return;
    }

    questions.forEach((q, idx) => {
        const div = document.createElement("div");
        div.className = "quiz-question";

        const optionsHtml = (q.options || []).map((opt, oi) => {
            const name = `q${idx}`;
            const letter = String.fromCharCode(65 + oi);
            return `
                <label class="quiz-option">
                    <input type="radio" name="${name}" value="${oi}">
                    <span>${letter}. ${opt}</span>
                </label>
            `;
        }).join("");

        div.innerHTML = `
            <div class="quiz-q-text">${idx + 1}. ${q.question}</div>
            <div class="quiz-options">
                ${optionsHtml}
            </div>
        `;
        out.appendChild(div);
    });

    const submitBtn = document.createElement("button");
    submitBtn.type = "button";
    submitBtn.textContent = "Submit Quiz";
    submitBtn.addEventListener("click", () => scoreQuiz(questions));
    out.appendChild(submitBtn);

    const resultDiv = document.createElement("div");
    resultDiv.id = "quizResult";
    resultDiv.className = "status";
    resultDiv.style.marginTop = "10px";
    out.appendChild(resultDiv);
}

function scoreQuiz(questions) {
    let correct = 0;
    const total = questions.length;

    questions.forEach((q, idx) => {
        const selected = document.querySelector(`input[name="q${idx}"]:checked`);
        if (!selected) return;
        const chosenIndex = parseInt(selected.value, 10);
        if (chosenIndex === q.answer_index) {
            correct++;
        }
    });

    const resultDiv = document.getElementById("quizResult");
    if (resultDiv) {
        resultDiv.textContent = `You scored ${correct} out of ${total}.`;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    let username = localStorage.getItem("pg_username");
    if (!username) {
        username = prompt("Enter a username for this demo:", "student123") || "Student";
        localStorage.setItem("pg_username", username);
    }
    document.getElementById("usernameDisplay").textContent = username;

    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            switchPage(btn.dataset.page);
            if (btn.dataset.page === "dashboard") loadDashboard();
            if (btn.dataset.page === "history") loadHistory();
        });
    });

    document.querySelectorAll(".tool-card").forEach(card => {
        card.addEventListener("click", () => {
            const page = card.dataset.pageLink;
            switchPage(page);
            if (page === "dashboard") loadDashboard();
            if (page === "history") loadHistory();
        });
    });

    document.getElementById("notesForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const form = e.target;
        const out = document.getElementById("notesOutput");
        out.textContent = "Generating notes with AI...";
        const fd = new FormData(form);
        try {
            const res = await fetch("/api/notes", {
                method: "POST",
                body: fd
            });
            const data = await res.json();
            if (data.error) {
                out.textContent = data.error;
            } else {
                out.textContent = data.notes;
                loadDashboard();
            }
        } catch (err) {
            out.textContent = "Error contacting server.";
        }
    });

    document.getElementById("quizForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const form = e.target;
        const status = document.getElementById("quizStatus");
        const out = document.getElementById("quizOutput");
        status.textContent = "Generating quiz with AI...";
        out.textContent = "";
        const fd = new FormData(form);
        try {
            const res = await fetch("/api/quiz", {
                method: "POST",
                body: fd
            });
            const data = await res.json();
            if (data.error) {
                status.textContent = data.error;
                out.textContent = "";
            } else {
                status.textContent = "Quiz ready";
                renderQuiz(data.questions || []);
                loadDashboard();
            }
        } catch (err) {
            status.textContent = "Error contacting server.";
        }
    });

    document.getElementById("questionsForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const form = e.target;
        const out = document.getElementById("questionsOutput");
        out.textContent = "Generating questions with AI...";
        const fd = new FormData(form);
        try {
            const res = await fetch("/api/questions", {
                method: "POST",
                body: fd
            });
            const data = await res.json();
            if (data.error) {
                out.textContent = data.error;
            } else {
                out.textContent = data.questions;
                loadDashboard();
            }
        } catch (err) {
            out.textContent = "Error contacting server.";
        }
    });

    document.getElementById("chatForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const input = document.getElementById("chatQuestion");
        const out = document.getElementById("chatOutput");
        const question = input.value.trim();
        if (!question) return;
        out.textContent = "Thinking...";
        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({question})
            });
            const data = await res.json();
            if (data.error) {
                out.textContent = data.error;
            } else {
                out.textContent = data.answer;
                input.value = "";
                loadDashboard();
            }
        } catch (err) {
            out.textContent = "Error contacting server.";
        }
    });

    document.getElementById("mentorForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const form = e.target;
        const out = document.getElementById("mentorOutput");
        out.textContent = "Creating your study plan with AI...";
        const payload = {
            subject: form.subject.value,
            totalDays: form.totalDays.value,
            hoursPerDay: form.hoursPerDay.value,
            level: form.level.value,
            notes: form.notes.value
        };
        try {
            const res = await fetch("/api/mentor", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.error) {
                out.textContent = data.error;
            } else {
                out.textContent = data.plan;
                loadDashboard();
            }
        } catch (err) {
            out.textContent = "Error contacting server.";
        }
    });

    loadDashboard();
    loadHistory();
});
