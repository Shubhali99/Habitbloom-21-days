const STORAGE_KEY = "habit-tracker-21-days";
const TOTAL_DAYS = 21;

const initialState = {
  habitName: "",
  selectedDay: 1,
  days: Array.from({ length: TOTAL_DAYS }, (_, index) => ({
    day: index + 1,
    completed: false,
    note: ""
  }))
};

const habitNameInput = document.getElementById("habitName");
const progressPercent = document.getElementById("progressPercent");
const streakCount = document.getElementById("streakCount");
const completedCount = document.getElementById("completedCount");
const statusMessage = document.getElementById("statusMessage");
const selectedDayLabel = document.getElementById("selectedDayLabel");
const dayNote = document.getElementById("dayNote");
const daysGrid = document.getElementById("daysGrid");
const markTodayButton = document.getElementById("markTodayButton");
const resetButton = document.getElementById("resetButton");
const progressRing = document.querySelector(".progress-ring");
const habitSetupCard = document.getElementById("habitSetupCard");
const habitSetupForm = document.getElementById("habitSetupForm");
const habitSetupInput = document.getElementById("habitSetupInput");
const habitSetupFeedback = document.getElementById("habitSetupFeedback");
const authApi = window.habitTrackerAuth;

if (!habitNameInput || !progressPercent || !streakCount || !completedCount || !statusMessage || !selectedDayLabel || !dayNote || !daysGrid || !markTodayButton || !resetButton || !progressRing) {
  throw new Error("Tracker UI is missing required elements.");
}

let state = cloneInitialState();

function cloneInitialState() {
  return {
    habitName: initialState.habitName,
    selectedDay: initialState.selectedDay,
    days: initialState.days.map((day) => ({ ...day }))
  };
}

function loadState() {
  return cloneInitialState();
}

async function saveState() {
  await authApi.apiRequest("/api/tracker", {
    method: "PUT",
    body: JSON.stringify(state)
  });
}

function countCompletedDays() {
  return state.days.filter((day) => day.completed).length;
}

function countCurrentStreak() {
  let streak = 0;

  for (const day of state.days) {
    if (!day.completed) {
      break;
    }

    streak += 1;
  }

  return streak;
}

function nextIncompleteDay() {
  return state.days.find((day) => !day.completed);
}

function formatDayLabel(dayNumber) {
  return `Day ${dayNumber}`;
}

function getStatusText() {
  const completed = countCompletedDays();

  if (!state.habitName.trim()) {
    return "Start by choosing the habit you want to track.";
  }

  if (completed === TOTAL_DAYS) {
    return "You completed all 21 days. Keep the habit going.";
  }

  const nextDay = nextIncompleteDay();

  if (!nextDay) {
    return "All days are complete.";
  }

  if (completed === 0) {
    return "Start with day 1 today.";
  }

  return ``;
}

function syncHabitSetupVisibility() {
  const hasHabit = Boolean(state.habitName.trim());

  if (habitSetupCard) {
    habitSetupCard.hidden = hasHabit;
  }

  daysGrid.hidden = !hasHabit;
  dayNote.disabled = !hasHabit;
  markTodayButton.disabled = !hasHabit || countCompletedDays() === TOTAL_DAYS;

  if (!hasHabit) {
    selectedDayLabel.textContent = "Choose your habit first, then select a day.";
    dayNote.value = "";
  }
}

function updateSummary() {
  const completed = countCompletedDays();
  const streak = countCurrentStreak();
  const percent = Math.round((completed / TOTAL_DAYS) * 100);

  progressPercent.textContent = `${percent}%`;
  streakCount.textContent = `${streak} day${streak === 1 ? "" : "s"}`;
  completedCount.textContent = `${completed} / ${TOTAL_DAYS} days`;
  statusMessage.textContent = getStatusText();
  progressRing.style.setProperty("--progress-angle", `${(percent / 100) * 360}deg`);

  markTodayButton.textContent = completed === TOTAL_DAYS ? "Tracker completed" : "Mark next day complete";
  syncHabitSetupVisibility();
}

function renderDays() {
  daysGrid.innerHTML = "";

  state.days.forEach((day) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "day-card";
    card.setAttribute("aria-label", `${formatDayLabel(day.day)}${day.completed ? ", completed" : ", not completed"}`);

    if (day.completed) {
      card.classList.add("is-complete");
    }

    if (state.selectedDay === day.day) {
      card.classList.add("is-selected");
    }

    const notePreview = day.note.trim() ? day.note.trim().slice(0, 58) : "Today's motivation";
    const suffix = day.note.trim().length > 58 ? "..." : "";
    const top = document.createElement("div");
    top.className = "day-card__top";

    const number = document.createElement("p");
    number.className = "day-number";
    number.textContent = formatDayLabel(day.day);

    const pill = document.createElement("span");
    pill.className = "check-pill";
    pill.textContent = day.completed ? "Done" : "Open";

    const preview = document.createElement("p");
    preview.className = "day-note-preview";
    preview.textContent = `${notePreview}${suffix}`;

    top.append(number, pill);
    card.append(top, preview);

    card.addEventListener("click", () => {
      state.selectedDay = day.day;
      saveState();
      render();
    });

    daysGrid.appendChild(card);
  });
}

function updateNoteEditor() {
  if (!state.habitName.trim()) {
    selectedDayLabel.textContent = "Choose your habit first, then select a day.";
    dayNote.value = "";
    dayNote.disabled = true;
    return;
  }

  const selectedDay = state.days.find((day) => day.day === state.selectedDay);

  if (!selectedDay) {
    selectedDayLabel.textContent = "Select a day to write a note.";
    dayNote.value = "";
    dayNote.disabled = true;
    return;
  }

  selectedDayLabel.textContent = `${formatDayLabel(selectedDay.day)} note`;
  dayNote.disabled = false;
  dayNote.value = selectedDay.note;
}

function render() {
  habitNameInput.value = state.habitName;
  renderDays();
  updateSummary();
  updateNoteEditor();
}

habitNameInput.addEventListener("input", (event) => {
  state.habitName = event.target.value;
  saveState();
  updateSummary();
});

dayNote.addEventListener("input", (event) => {
  const selectedDay = state.days.find((day) => day.day === state.selectedDay);

  if (!selectedDay) {
    return;
  }

  selectedDay.note = event.target.value;
  saveState();
  renderDays();
});

markTodayButton.addEventListener("click", () => {
  if (!state.habitName.trim()) {
    if (habitSetupInput) {
      habitSetupInput.focus();
    }
    return;
  }

  const nextDay = nextIncompleteDay();

  if (!nextDay) {
    return;
  }

  nextDay.completed = true;
  state.selectedDay = nextDay.day;
  saveState();
  render();
});

resetButton.addEventListener("click", () => {
  state = cloneInitialState();
  saveState();
  render();
});

if (habitSetupForm) {
  habitSetupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const habitName = habitSetupInput.value.trim();
    if (!habitName) {
      habitSetupFeedback.textContent = "Please enter the habit you want to track.";
      habitSetupFeedback.dataset.state = "error";
      return;
    }

    state.habitName = habitName;
    habitSetupFeedback.textContent = "Saving your habit...";
    habitSetupFeedback.dataset.state = "";
    await saveState();
    habitSetupFeedback.textContent = "";
    habitNameInput.value = habitName;
    render();
  });
}

async function bootstrapTracker() {
  try {
    const serverState = await authApi.apiRequest("/api/tracker", { method: "GET" });
    const mergedDays = initialState.days.map((defaultDay, index) => ({
      ...defaultDay,
      ...(serverState.days?.[index] ?? {})
    }));

    state = {
      habitName: serverState.habitName ?? "",
      selectedDay: serverState.selectedDay ?? 1,
      days: mergedDays
    };
    render();
    if (!state.habitName.trim() && habitSetupInput) {
      habitSetupInput.focus();
    }
  } catch (error) {
    statusMessage.textContent = error.message;
  }
}

bootstrapTracker();
