# Quiz Bible

Quiz Bible es un proyecto de Neuronova Apps orientado a una experiencia de preguntas y desafíos sobre contenidos bíblicos.

## Estado actual

**MVP web inicial en desarrollo.**

La versión web disponible incorpora un **quiz jugable de seis preguntas aprobadas**. La experiencia permite responder, comprobar, revisar una explicación y referencia bíblica, continuar por el banco, conservar el avance localmente y reiniciar el progreso.

La versión actual incluye:

- presentación del concepto Quiz Bible;
- identidad visual propia dentro de Neuronova Apps;
- primer banco de seis preguntas con estado `approved`;
- preguntas cargadas desde `data/questions.json`;
- cuatro opciones por pregunta;
- selección mediante controles nativos de tipo radio;
- comprobación de una única respuesta por pregunta;
- indicación de respuesta correcta o incorrecta;
- explicación educativa visible después de comprobar;
- referencia bíblica visible después de comprobar;
- avance secuencial por las seis preguntas;
- puntuación calculada a partir de las respuestas comprobadas;
- restauración de pregunta actual, respuestas y resultado después de recargar;
- persistencia local mediante `localStorage`;
- reinicio explícito que elimina el progreso guardado;
- resultado final restaurable;
- instrucciones visibles de teclado;
- estados accesibles para respuesta correcta y elección incorrecta;
- foco gestionado al avanzar, reiniciar y mostrar el resultado;
- anuncios de progreso mediante una región `aria-live` separada;
- foco visible reforzado sobre las opciones y el enunciado;
- diseño responsive;
- skip link y módulo central de accesibilidad de Neuronova Apps;
- soporte para `prefers-reduced-motion`;
- metadatos SEO/social básicos;
- sitemap con portada y privacidad;
- modelo editorial y contrato técnico para el contenido bíblico.

Todavía no están implementados:

- categorías o niveles seleccionables;
- cuentas, sincronización o ranking;
- banco amplio o generación dinámica de preguntas;
- páginas educativas/indexables específicas de Quiz Bible;
- pruebas manuales exhaustivas con lectores de pantalla y otras tecnologías de asistencia;
- certificación o auditoría formal de conformidad WCAG.

Estas funciones o validaciones deben considerarse futuras hasta estar implementadas y verificadas.

## Banco inicial

`data/questions.json` contiene seis preguntas de dificultad `beginner` sobre hechos narrativos directos:

1. Noé y la construcción del arca — `Génesis 6:13–22`;
2. David y Goliat — `1 Samuel 17:49–51`;
3. Zaqueo en Jericó — `Lucas 19:1–4`;
4. Jonás y el gran pez — `Jonás 1:17`;
5. el llamado de Moisés — `Éxodo 3:7–12`;
6. las negaciones de Pedro — `Mateo 26:69–75`.

Todas están marcadas como `approved`, con `referenceChecked: true`, `singleCorrectAnswerChecked: true` y `doctrinalSensitivity: "none"`.

Cada entrada incluye `explanation` y `references`. Después de comprobar una respuesta, `quiz.js` utiliza esos campos para mostrar una paráfrasis educativa y la referencia canónica preparada en `display`. El MVP no reproduce versículos completos ni obliga a una traducción bíblica específica.

## Flujo de juego actual

La sesión sigue este recorrido:

1. `quiz.js` carga `data/questions.json`;
2. se filtran únicamente preguntas `approved` con opción correcta, explicación y referencia jugables;
3. se intenta restaurar un estado local válido;
4. se presenta la pregunta pendiente o la última respuesta comprobada;
5. la persona selecciona una respuesta;
6. **Comprobar respuesta** evalúa la opción una sola vez y guarda esa respuesta;
7. se actualiza la puntuación calculándola desde las respuestas válidas;
8. aparece el bloque **Para aprender**, con explicación y referencia bíblica;
9. **Siguiente pregunta** actualiza la posición guardada y lleva el foco al nuevo enunciado;
10. al terminar se guarda el estado de finalización, se muestra el resultado y el foco pasa al resumen;
11. **Reiniciar progreso** elimina el estado local, vuelve a la primera pregunta y enfoca el nuevo enunciado.

La carga inicial y la restauración automática no fuerzan el foco fuera de la posición actual del navegador. Si el banco no puede cargarse o no contiene preguntas aprobadas con los datos requeridos, la interfaz muestra un estado de error en lugar de bloquear la página.

## Persistencia local

La clave utilizada es:

`quizbible-progress-v1`

El formato actual almacena:

```json
{
  "version": 1,
  "currentQuestionId": "qb-eventos-001",
  "answers": {
    "qb-eventos-001": "b"
  },
  "completed": false
}
```

La puntuación **no se almacena como fuente de verdad**. Cada vez que se renderiza el quiz se calcula comparando las respuestas válidas con `correctOptionId` del banco actual.

### Validación al restaurar

`quiz.js` valida el estado antes de utilizarlo:

- exige `version: 1`;
- solo acepta IDs presentes en el banco jugable actual;
- solo acepta opciones que existan realmente en cada pregunta;
- solo conserva un prefijo secuencial de respuestas válidas;
- la pregunta restaurada debe ser la última respondida o la siguiente pendiente;
- `completed: true` solo se acepta cuando todas las preguntas tienen una respuesta válida;
- los datos incompatibles se normalizan o descartan.

Si `localStorage` no está disponible o lanza un error, el quiz continúa funcionando en memoria durante la sesión.

## Modelo de contenido bíblico

El repositorio mantiene separado el contenido bíblico de la lógica del juego:

- `docs/content-model.md`: política editorial, reglas de redacción, referencias, revisión y flujo de aprobación;
- `data/question.schema.json`: JSON Schema que define la estructura técnica de cada pregunta;
- `data/questions.json`: banco aprobado consumido por el MVP actual.

Cada pregunta debe incluir como mínimo:

- identificador estable y versión;
- estado editorial (`draft`, `reviewed`, `approved` o `retired`);
- categoría y dificultad;
- tipo de contenido (`textual_fact` o `contextual`);
- enunciado;
- entre tres y cuatro opciones;
- una única opción correcta;
- explicación educativa;
- una o más referencias bíblicas;
- etiquetas;
- registro de revisión editorial.

El MVP prioriza hechos textuales y contexto directamente sustentable por referencias bíblicas. Las interpretaciones doctrinales discutibles no deben presentarse como una respuesta correcta universal. Solo las preguntas `approved` se consideran elegibles para el juego.

El modelo no obliga a una traducción bíblica concreta. Las explicaciones se redactan principalmente como paráfrasis propias y cualquier cita literal futura deberá respetar la licencia de la traducción utilizada.

## Privacidad

El progreso permanece en el navegador mediante `localStorage`; no existe base de datos propia, cuenta de usuario ni sincronización remota. Las respuestas guardadas no se envían a un servidor propio de Quiz Bible.

**Reiniciar progreso** elimina la clave local utilizada por el quiz. El usuario también puede borrar los datos del sitio desde la configuración del navegador.

La política pública se mantiene en `privacy/index.html`.

## Accesibilidad específica del quiz

Además de la base compartida de Neuronova Apps, el flujo jugable incorpora ahora medidas específicas:

- `fieldset` y radios nativos para conservar el comportamiento estándar del grupo de respuestas;
- instrucciones visibles sobre Tab, flechas y barra espaciadora;
- foco visual aplicado a toda la tarjeta de la opción cuando su radio recibe `:focus-visible`;
- texto oculto asociado al label que indica, después de comprobar, **Respuesta correcta**, **Respuesta correcta y seleccionada** o **Tu respuesta, incorrecta**;
- región `aria-live` para el resultado de cada comprobación;
- región `aria-live` separada para anunciar pregunta y puntuación al avanzar o reiniciar;
- el nuevo enunciado recibe foco programático después de **Siguiente pregunta** y **Reiniciar progreso**;
- el resumen final recibe foco al completar el recorrido;
- la carga inicial o restaurada evita mover el foco automáticamente;
- el bloque educativo conserva un encabezado semántico y la referencia aparece como texto legible.

Estas medidas mejoran el flujo técnico, pero **no constituyen una certificación WCAG**. Siguen siendo necesarias pruebas manuales con lectores de pantalla, navegación ampliada, alto contraste, zoom, dispositivos móviles y otras tecnologías de asistencia antes de realizar una afirmación formal de conformidad.

## Estructura

- `index.html`: presentación, quiz, instrucciones y estado actual del proyecto.
- `styles.css`: estilos base compartidos.
- `hero-orbit.css`: estilos y animaciones de la órbita del hero.
- `quiz.css`: layout, opciones, feedback, bloque educativo y foco específico del quiz.
- `quiz.js`: carga, validación de persistencia, respuestas, estados accesibles, foco, feedback, puntuación, avance y reinicio.
- `docs/content-model.md`: modelo editorial del contenido bíblico.
- `data/question.schema.json`: contrato JSON Schema para preguntas.
- `data/questions.json`: banco inicial aprobado.
- `privacy/index.html`: política de privacidad.
- `privacy/privacy.css`: estilos exclusivos de la política de privacidad.
- `sitemap.xml`: rutas públicas indexables.

## Próxima etapa

El siguiente trabajo previsto es crear **páginas educativas e indexables** para ampliar Quiz Bible fuera de la experiencia jugable: guías sobre cómo utilizar preguntas para estudiar, cómo leer referencias bíblicas y cómo se revisa el contenido del proyecto, manteniendo un enfoque neutral y verificable.

## Enlaces

- Web: https://neuronova-apps.github.io/quizbible-app/
- Política de privacidad: https://neuronova-apps.github.io/quizbible-app/privacy/
- Repositorio: https://github.com/neuronova-apps/quizbible-app
- Ecosistema: https://neuronova-apps.github.io/

## Autoría

Proyecto personal desarrollado dentro del ecosistema Neuronova Apps.
