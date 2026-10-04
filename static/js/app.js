/**
 * FitTrack AI - Frontend Client Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  initUserDropdown();
  initAddFoodModal();
  initWorkoutTracker();
  initProgressCharts();
  initAICoachChat();
  initWaterTracker();
});

/* Toast Notification Utility */
function showToast(message, type = 'success') {
  const container = document.getElementById('flash-messages') || createToastContainer();
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> <span>${message}</span>`;
  container.appendChild(alert);
  setTimeout(() => {
    alert.style.opacity = '0';
    setTimeout(() => alert.remove(), 300);
  }, 3500);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'flash-messages';
  container.className = 'flash-messages';
  document.body.appendChild(container);
  return container;
}

/* Profile Dropdown Toggle */
function initUserDropdown() {
  const btn = document.getElementById('avatar-dropdown-btn');
  const menu = document.getElementById('user-dropdown-menu');
  if (btn && menu) {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      menu.classList.toggle('show');
    });
    document.addEventListener('click', () => menu.classList.remove('show'));
  }
}

/* Modal Helper */
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('show');
}
function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('show');
}

/* Add Food Modal Logic */
function initAddFoodModal() {
  const modal = document.getElementById('add-food-modal');
  if (!modal) return;

  const form = document.getElementById('add-food-form');
  const qtyInput = document.getElementById('modal-qty-input');
  const foodIdInput = document.getElementById('modal-food-id');

  // Delegated click for food cards "+ Add Food" buttons
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-add-food');
    if (btn) {
      const foodId = btn.dataset.foodId;
      const foodName = btn.dataset.foodName;
      const serving = btn.dataset.foodServing;
      const isPerItem = btn.dataset.isPerItem === '1';

      document.getElementById('modal-food-title').textContent = foodName;
      document.getElementById('modal-food-serving-label').textContent = isPerItem ? 'Quantity (Items):' : 'Quantity (Grams):';
      foodIdInput.value = foodId;
      qtyInput.value = isPerItem ? 1 : 100;

      openModal('add-food-modal');
    }
  });

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(form);
      try {
        const res = await fetch('/api/log-food', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, 'success');
          closeModal('add-food-modal');
          setTimeout(() => window.location.reload(), 800);
        } else {
          showToast(data.message, 'danger');
        }
      } catch (err) {
        showToast('Error saving food log.', 'danger');
      }
    });
  }
}

/* Delete Food Log Handler */
async function deleteFoodLog(logId) {
  if (!confirm('Are you sure you want to delete this food entry?')) return;
  const formData = new FormData();
  formData.append('log_id', logId);

  try {
    const res = await fetch('/api/delete-food-log', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      setTimeout(() => window.location.reload(), 600);
    }
  } catch (err) {
    showToast('Failed to delete log.', 'danger');
  }
}

/* Water Tracker Buttons */
function initWaterTracker() {
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.btn-add-water');
    if (btn) {
      const amount = btn.dataset.amount;
      const formData = new FormData();
      formData.append('amount', amount);

      try {
        const res = await fetch('/api/log-water', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, 'success');
          // Update water UI if elements exist
          const waterValEl = document.getElementById('water-val-display');
          if (waterValEl) waterValEl.textContent = `${data.total} / 3.0 L`;

          const waterFillEl = document.getElementById('water-fill-bar');
          if (waterFillEl) {
            const pct = Math.min((data.total / 3.0) * 100, 100);
            waterFillEl.style.height = `${pct}%`;
          }
        }
      } catch (err) {
        showToast('Error updating water log.', 'danger');
      }
    }
  });
}

/* Interactive Workout Tracker Player */
let activeWorkoutState = null;
let timerInterval = null;

function initWorkoutTracker() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-start-workout');
    if (btn) {
      const workoutData = JSON.parse(btn.dataset.workoutJson);
      startWorkoutPlayer(workoutData);
    }
  });
}

function startWorkoutPlayer(workout) {
  activeWorkoutState = {
    id: workout.info.id,
    name: workout.info.name,
    exercises: workout.exercises,
    currentExerciseIdx: 0,
    currentSet: 1,
    startTime: new Date(),
    timerSeconds: 0
  };

  renderActiveWorkoutModal();
  openModal('workout-player-modal');
}

function renderActiveWorkoutModal() {
  const container = document.getElementById('workout-player-content');
  if (!container || !activeWorkoutState) return;

  const ex = activeWorkoutState.exercises[activeWorkoutState.currentExerciseIdx];
  const isLastEx = activeWorkoutState.currentExerciseIdx === activeWorkoutState.exercises.length - 1;

  container.innerHTML = `
    <div style="text-align: center; margin-bottom: 1.5rem;">
      <span class="ai-badge" style="margin-bottom: 0.5rem;"><i class="fas fa-running"></i> ACTIVE WORKOUT</span>
      <h2>${activeWorkoutState.name}</h2>
      <p style="color: var(--text-secondary);">Exercise ${activeWorkoutState.currentExerciseIdx + 1} of ${activeWorkoutState.exercises.length}</p>
    </div>

    <div style="background: var(--bg-surface); padding: 1.5rem; border-radius: var(--radius-md); border: 1px solid var(--border-color); margin-bottom: 1.5rem; text-align: center;">
      <h3 style="font-size: 1.5rem; color: var(--red-bright); margin-bottom: 0.5rem;">${ex.exercise_name}</h3>
      <p style="font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem;">Set ${activeWorkoutState.currentSet} of ${ex.sets} &bull; ${ex.reps}</p>
      
      <div id="rest-timer-display" style="display: none; font-size: 2rem; font-weight: 800; color: var(--red-bright); margin: 1rem 0;">
        ⏱️ Rest: <span id="rest-timer-val">${ex.rest_seconds}</span>s
      </div>

      <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 1rem;">
        <button class="btn btn-primary" onclick="handleCompleteSet()"><i class="fas fa-check"></i> Complete Set</button>
        <button class="btn btn-secondary" onclick="${isLastEx ? 'finishWorkout()' : 'handleNextExercise()'}">
          ${isLastEx ? '<i class="fas fa-flag-checkered"></i> Finish Workout' : '<i class="fas fa-step-forward"></i> Next Exercise'}
        </button>
      </div>
    </div>
  `;
}

function handleCompleteSet() {
  const ex = activeWorkoutState.exercises[activeWorkoutState.currentExerciseIdx];
  if (activeWorkoutState.currentSet < ex.sets) {
    activeWorkoutState.currentSet++;
    startRestTimer(ex.rest_seconds);
  } else {
    handleNextExercise();
  }
}

function startRestTimer(seconds) {
  const display = document.getElementById('rest-timer-display');
  const valEl = document.getElementById('rest-timer-val');
  if (!display || !valEl) return;

  display.style.display = 'block';
  let left = seconds;
  valEl.textContent = left;

  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    left--;
    valEl.textContent = left;
    if (left <= 0) {
      clearInterval(timerInterval);
      display.style.display = 'none';
      renderActiveWorkoutModal();
    }
  }, 1000);
}

function handleNextExercise() {
  clearInterval(timerInterval);
  if (activeWorkoutState.currentExerciseIdx < activeWorkoutState.exercises.length - 1) {
    activeWorkoutState.currentExerciseIdx++;
    activeWorkoutState.currentSet = 1;
    renderActiveWorkoutModal();
  } else {
    finishWorkout();
  }
}

async function finishWorkout() {
  clearInterval(timerInterval);
  const durationMin = Math.max(1, Math.round((new Date() - activeWorkoutState.startTime) / 60000));
  
  const formData = new FormData();
  formData.append('workout_id', activeWorkoutState.id);
  formData.append('workout_name', activeWorkoutState.name);
  formData.append('duration', durationMin);

  try {
    const res = await fetch('/api/log-workout', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.success) {
      closeModal('workout-player-modal');
      showToast(data.message, 'success');
      setTimeout(() => window.location.reload(), 1000);
    }
  } catch (err) {
    showToast('Failed to save workout.', 'danger');
  }
}

/* Progress Page Chart.js Visualizations */
async function initProgressCharts() {
  const weightCanvas = document.getElementById('weightChart');
  if (!weightCanvas) return;

  try {
    const res = await fetch('/api/progress-data');
    const data = await res.json();

    // Chart Global Colors setup
    Chart.defaults.color = '#B8B8B8';
    Chart.defaults.font.family = 'Inter';

    // 1. Weight Chart
    new Chart(weightCanvas, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Weight (kg)',
          data: data.weight,
          borderColor: '#FF1E2D',
          backgroundColor: 'rgba(255, 30, 45, 0.15)',
          borderWidth: 3,
          fill: true,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { grid: { color: '#252525' } },
          x: { grid: { color: '#252525' } }
        }
      }
    });

    // 2. Calorie Chart
    const calCanvas = document.getElementById('caloriesChart');
    if (calCanvas) {
      new Chart(calCanvas, {
        type: 'bar',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Calories (kcal)',
            data: data.calories,
            backgroundColor: '#E50914',
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: { y: { grid: { color: '#252525' } }, x: { grid: { color: '#252525' } } }
        }
      });
    }

    // 3. Protein Chart
    const protCanvas = document.getElementById('proteinChart');
    if (protCanvas) {
      new Chart(protCanvas, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Protein (g)',
            data: data.protein,
            borderColor: '#FFFFFF',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 2,
            tension: 0.3
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: { y: { grid: { color: '#252525' } }, x: { grid: { color: '#252525' } } }
        }
      });
    }

  } catch (err) {
    console.error('Error loading progress charts:', err);
  }
}

/* AI Assistant & Coach Client Logic */
function initAICoachChat() {
  const form = document.getElementById('ai-assistant-form') || document.getElementById('ai-chat-form');
  const input = document.getElementById('ai-assistant-input') || document.getElementById('ai-chat-input');
  const messagesBox = document.getElementById('chat-messages');
  const generateBtn = document.getElementById('ai-generate-btn');
  const validationMsg = document.getElementById('input-validation-msg');

  if (!form || !input || !messagesBox) return;

  // Hide validation message on typing
  input.addEventListener('input', () => {
    if (validationMsg) validationMsg.style.display = 'none';
    input.style.borderColor = '';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = input.value.trim();

    // Client-side Request Validation: prevent empty requests
    if (!query) {
      if (validationMsg) {
        validationMsg.style.display = 'block';
      }
      input.style.borderColor = 'var(--red-bright)';
      showToast('Please enter a question or request before generating.', 'danger');
      return;
    }

    if (validationMsg) validationMsg.style.display = 'none';
    input.style.borderColor = '';

    // Append User Prompt to Chat Display
    appendChatMessage('user', query);
    input.value = '';

    // Show Loading Indicator & Disable Generate Button
    if (generateBtn) {
      generateBtn.disabled = true;
      generateBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Generating...';
    }

    const typingDiv = document.createElement('div');
    typingDiv.className = 'message ai typing-message';
    typingDiv.id = 'ai-typing-indicator';
    typingDiv.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Generating response with Gemini AI...';
    messagesBox.appendChild(typingDiv);
    messagesBox.scrollTop = messagesBox.scrollHeight;

    try {
      const res = await fetch('/api/ai-assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: query, message: query })
      });

      const data = await res.json();
      document.getElementById('ai-typing-indicator')?.remove();

      if (res.ok && data.success !== false && (data.reply || data.response)) {
        appendChatMessage('ai', data.reply || data.response);
      } else {
        const errorText = data.error || data.reply || 'Request failed. Please try again.';
        appendErrorMessage(errorText);
      }
    } catch (err) {
      document.getElementById('ai-typing-indicator')?.remove();
      appendErrorMessage('Unable to connect to AI Assistant. Please check your network connection and try again.');
    } finally {
      if (generateBtn) {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-sparkles"></i> Generate';
      }
    }
  });

  // Suggestion chip quick clicks
  document.addEventListener('click', (e) => {
    const chip = e.target.closest('.chat-suggestion-chip');
    if (chip && input && form) {
      input.value = chip.dataset.query;
      if (validationMsg) validationMsg.style.display = 'none';
      input.style.borderColor = '';
      form.requestSubmit();
    }
  });
}

function appendChatMessage(sender, text) {
  const box = document.getElementById('chat-messages');
  if (!box) return;

  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;

  if (sender === 'user') {
    msgDiv.textContent = text;
  } else {
    // Format response text with basic HTML escaping and markdown conversion
    let safeText = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    let formatted = safeText
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/^\s*•\s*/gm, '• ')
      .replace(/\n/g, '<br>');

    msgDiv.innerHTML = formatted;
  }

  box.appendChild(msgDiv);
  box.scrollTop = box.scrollHeight;
}

function appendErrorMessage(errorMsg) {
  const box = document.getElementById('chat-messages');
  if (!box) return;

  const errDiv = document.createElement('div');
  errDiv.className = 'message ai error-message';
  errDiv.style.background = 'rgba(255, 30, 45, 0.15)';
  errDiv.style.border = '1px solid var(--red-primary)';
  errDiv.style.color = '#ff9999';
  errDiv.style.borderRadius = 'var(--radius-md)';
  errDiv.style.padding = '0.9rem 1.1rem';
  errDiv.style.fontSize = '0.9rem';
  errDiv.innerHTML = `<i class="fas fa-exclamation-triangle" style="color: var(--red-bright); margin-right: 0.4rem;"></i> <strong>Notice:</strong> ${errorMsg}`;
  box.appendChild(errDiv);
  box.scrollTop = box.scrollHeight;
}
