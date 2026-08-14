(() => {
  const app = document.querySelector('#quizApp');
  if (!app) return;

  const progress = document.querySelector('#quizProgress');
  const scoreNode = document.querySelector('#quizScore');
  const category = document.querySelector('#quizCategory');
  const questionNode = document.querySelector('#quizQuestion');
  const form = document.querySelector('#quizForm');
  const optionsNode = document.querySelector('#quizOptions');
  const feedback = document.querySelector('#quizFeedback');
  const checkButton = document.querySelector('#checkAnswer');
  const nextButton = document.querySelector('#nextQuestion');
  const restartButton = document.querySelector('#restartQuiz');

  let questions = [];
  let currentIndex = 0;
  let score = 0;
  let answered = false;

  const categoryLabel = value => ({
    eventos: 'Eventos',
    personajes: 'Personajes',
    lugares: 'Lugares',
    evangelios: 'Evangelios'
  }[value] || value);

  const difficultyLabel = value => ({
    beginner: 'Inicial',
    intermediate: 'Intermedia',
    advanced: 'Avanzada'
  }[value] || value);

  function isPlayableQuestion(question) {
    if (!question || question.status !== 'approved') return false;
    if (!Array.isArray(question.options) || question.options.length < 3) return false;
    if (!question.correctOptionId || !question.options.some(option => option.id === question.correctOptionId)) return false;
    return typeof question.prompt === 'string' && question.prompt.trim().length > 0;
  }

  function getSelectedOptionId() {
    return form.querySelector('input[name="quiz-answer"]:checked')?.value || null;
  }

  function setOptionsDisabled(disabled) {
    optionsNode.querySelectorAll('input[name="quiz-answer"]').forEach(input => {
      input.disabled = disabled;
    });
  }

  function updateScore() {
    scoreNode.textContent = `Puntuación: ${score}/${questions.length}`;
  }

  function renderQuestion() {
    const question = questions[currentIndex];
    answered = false;
    app.dataset.state = 'playing';
    optionsNode.hidden = false;
    checkButton.hidden = false;
    nextButton.hidden = true;
    restartButton.hidden = true;
    checkButton.disabled = true;
    feedback.textContent = 'Elige una opción y comprueba tu respuesta.';
    feedback.className = 'quiz-feedback neutral';

    progress.textContent = `Pregunta ${currentIndex + 1} de ${questions.length}`;
    updateScore();
    category.textContent = `${categoryLabel(question.category)} · Dificultad ${difficultyLabel(question.difficulty).toLowerCase()}`;
    questionNode.textContent = question.prompt;
    optionsNode.innerHTML = '<legend class="visually-hidden">Elige una respuesta</legend>';

    question.options.forEach(option => {
      const label = document.createElement('label');
      label.className = 'quiz-option';
      label.dataset.optionId = option.id;

      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'quiz-answer';
      input.value = option.id;

      const marker = document.createElement('span');
      marker.className = 'quiz-option-marker';
      marker.setAttribute('aria-hidden', 'true');
      marker.textContent = option.id.toUpperCase();

      const text = document.createElement('span');
      text.className = 'quiz-option-text';
      text.textContent = option.text;

      label.append(input, marker, text);
      optionsNode.append(label);
    });

    optionsNode.querySelector('input')?.focus({ preventScroll: true });
  }

  function checkAnswer() {
    if (answered) return;

    const selectedId = getSelectedOptionId();
    if (!selectedId) {
      feedback.textContent = 'Selecciona una respuesta antes de comprobar.';
      return;
    }

    const question = questions[currentIndex];
    const correctOption = question.options.find(option => option.id === question.correctOptionId);
    const isCorrect = selectedId === question.correctOptionId;
    answered = true;
    setOptionsDisabled(true);

    optionsNode.querySelectorAll('.quiz-option').forEach(label => {
      const optionId = label.dataset.optionId;
      if (optionId === question.correctOptionId) label.classList.add('correct');
      if (optionId === selectedId && !isCorrect) label.classList.add('incorrect');
    });

    if (isCorrect) {
      score += 1;
      feedback.textContent = 'Correcto.';
      feedback.className = 'quiz-feedback success';
    } else {
      feedback.textContent = `No es correcto. La respuesta es ${correctOption.text}.`;
      feedback.className = 'quiz-feedback error';
    }

    updateScore();
    checkButton.hidden = true;
    nextButton.hidden = false;
    nextButton.textContent = currentIndex === questions.length - 1 ? 'Ver resultado' : 'Siguiente pregunta';
    nextButton.focus({ preventScroll: true });
  }

  function showResult() {
    app.dataset.state = 'complete';
    progress.textContent = 'Quiz completado';
    updateScore();
    category.textContent = 'Resultado de la sesión';
    questionNode.textContent = `Has respondido correctamente ${score} de ${questions.length} preguntas.`;
    optionsNode.hidden = true;
    checkButton.hidden = true;
    nextButton.hidden = true;
    restartButton.hidden = false;
    feedback.textContent = 'Puedes reiniciar para volver a recorrer el banco inicial.';
    feedback.className = 'quiz-feedback neutral';
    restartButton.focus({ preventScroll: true });
  }

  function nextQuestion() {
    if (!answered) return;
    if (currentIndex >= questions.length - 1) {
      showResult();
      return;
    }
    currentIndex += 1;
    renderQuestion();
  }

  function restartQuiz() {
    currentIndex = 0;
    score = 0;
    renderQuestion();
  }

  optionsNode.addEventListener('change', () => {
    if (!answered) checkButton.disabled = !getSelectedOptionId();
  });

  form.addEventListener('submit', event => {
    event.preventDefault();
    checkAnswer();
  });

  nextButton.addEventListener('click', nextQuestion);
  restartButton.addEventListener('click', restartQuiz);

  fetch('data/questions.json')
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(data => {
      questions = Array.isArray(data) ? data.filter(isPlayableQuestion) : [];
      if (!questions.length) throw new Error('No hay preguntas aprobadas disponibles.');
      renderQuestion();
    })
    .catch(() => {
      app.dataset.state = 'error';
      progress.textContent = 'Quiz no disponible';
      scoreNode.textContent = '';
      category.textContent = 'Error de carga';
      questionNode.textContent = 'No se pudo cargar el banco de preguntas.';
      optionsNode.hidden = true;
      checkButton.hidden = true;
      nextButton.hidden = true;
      restartButton.hidden = true;
      feedback.textContent = 'Recarga la página para intentarlo de nuevo.';
      feedback.className = 'quiz-feedback error';
    });
})();
