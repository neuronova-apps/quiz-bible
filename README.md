# Quiz Bible

Quiz Bible es un proyecto de Neuronova Apps orientado a una experiencia de preguntas y desafíos sobre contenidos bíblicos.

## Estado actual

**MVP web inicial en desarrollo.**

La versión web disponible incorpora un **quiz jugable de seis preguntas aprobadas** y cinco páginas educativas públicas. La experiencia permite responder, comprobar, revisar una explicación y referencia bíblica, continuar por el banco, conservar el avance localmente, reiniciar el progreso y ampliar el estudio mediante guías indexables.

La versión actual incluye:

- primer banco de seis preguntas con estado `approved`;
- preguntas cargadas desde `data/questions.json`;
- cuatro opciones por pregunta;
- comprobación de una única respuesta por pregunta;
- explicación educativa y referencia bíblica visibles después de comprobar;
- puntuación calculada desde las respuestas válidas;
- progreso restaurable mediante `localStorage`;
- reinicio explícito que elimina el progreso guardado;
- flujo de teclado reforzado, foco gestionado y estados accesibles de respuestas;
- cinco guías educativas públicas e indexables;
- sitemap con portada, cinco guías y privacidad;
- modelo editorial y contrato técnico para el contenido bíblico.

Todavía no están implementados:

- categorías o niveles seleccionables;
- cuentas, sincronización o ranking;
- banco amplio o generación dinámica de preguntas;
- tarjeta social dedicada 1200×630;
- pruebas manuales exhaustivas con lectores de pantalla y otras tecnologías de asistencia;
- certificación o auditoría formal de conformidad WCAG.

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

1. `quiz.js` carga `data/questions.json`.
2. Se filtran preguntas `approved` con opción correcta, explicación y referencia válidas.
3. Se intenta restaurar un estado local compatible.
4. Se presenta la pregunta pendiente o la última respuesta comprobada.
5. La persona selecciona una respuesta.
6. **Comprobar respuesta** evalúa y guarda esa elección una sola vez.
7. Se recalcula la puntuación desde las respuestas válidas.
8. Aparece el bloque **Para aprender**, con explicación y referencia.
9. **Siguiente pregunta** actualiza la posición guardada y lleva el foco al nuevo enunciado.
10. Al terminar se guarda el estado de finalización y se muestra el resultado.
11. **Reiniciar progreso** elimina el estado local y vuelve a la primera pregunta.

La carga inicial y la restauración automática no fuerzan el foco. Si el banco no puede cargarse o no contiene preguntas válidas, la interfaz muestra un estado de error.

## Persistencia local

La clave utilizada es `quizbible-progress-v1`.

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

La puntuación no se almacena como fuente de verdad. Se calcula comparando las respuestas restauradas con `correctOptionId` del banco actual.

La restauración:

- exige `version: 1`;
- solo acepta IDs presentes en el banco actual;
- solo acepta opciones existentes;
- conserva un prefijo secuencial de respuestas válidas;
- valida la posición restaurada;
- solo acepta `completed: true` cuando todas las preguntas tienen una respuesta válida.

Si `localStorage` falla, el quiz continúa funcionando en memoria durante la sesión.

## Modelo de contenido bíblico

El contenido se mantiene separado de la lógica del juego:

- `docs/content-model.md`: política editorial, referencias, revisión y flujo de aprobación;
- `data/question.schema.json`: contrato JSON Schema para cada pregunta;
- `data/questions.json`: banco aprobado consumido por el MVP.

El proyecto prioriza hechos textuales y contexto directamente sustentable por referencias. Las interpretaciones doctrinales discutibles no deben presentarse como respuesta correcta universal.

## Guías educativas públicas

El sitio dispone ahora de cinco páginas estáticas e indexables:

- `como-estudiar-con-preguntas-biblicas.html`: cómo convertir preguntas, explicación y referencia en una rutina breve de estudio;
- `leer-referencias-biblicas.html`: cómo interpretar libro, capítulo y versículos;
- `revision-contenido-biblico.html`: cómo funciona el flujo editorial y qué intenta evitar;
- `usar-feedback-quiz-bible.html`: cómo aprovechar aciertos, errores, explicación y puntuación;
- `guia-quiz-bible-principiantes.html`: recorrido completo por uso, teclado, progreso local y reinicio.

Estas guías **no modifican la partida**, no responden preguntas automáticamente y no representan nuevas modalidades del motor. Son contenido educativo complementario y enlazan de vuelta al quiz.

Todas incluyen:

- meta description propia;
- canonical absoluto;
- `robots="index, follow"`;
- H1 único;
- skip link;
- navegación cruzada entre recursos;
- CTA de regreso al quiz.

Comparten `resources.css`, mientras la portada utiliza `guide-cards.css` para presentar las cinco tarjetas.

## Privacidad

El progreso permanece en el navegador mediante `localStorage`; no existe cuenta ni sincronización remota. **Reiniciar progreso** elimina la clave utilizada por el quiz. La política pública está en `privacy/index.html`.

Las páginas educativas son contenido estático y no añaden datos personales ni un nuevo formato de persistencia.

## Accesibilidad específica del quiz

Además de la base compartida de Neuronova Apps, el flujo jugable incorpora:

- `fieldset` y radios nativos;
- instrucciones visibles sobre Tab, flechas y barra espaciadora;
- foco visual sobre toda la tarjeta de respuesta;
- estados textuales ocultos para respuesta correcta o elección incorrecta;
- regiones `aria-live` separadas para resultado y progreso;
- foco programático al avanzar, reiniciar y mostrar el resumen;
- carga/restauración sin robo de foco.

Estas medidas no constituyen una certificación WCAG. Siguen pendientes pruebas manuales con lectores de pantalla, zoom, alto contraste y otras tecnologías de asistencia.

## Estructura principal

- `index.html`: presentación, quiz, guías y estado del proyecto.
- `styles.css`: estilos base.
- `hero-orbit.css`: hero.
- `quiz.css`: interfaz y accesibilidad específica del quiz.
- `guide-cards.css`: tarjetas de guías en portada.
- `resources.css`: estilos compartidos de las páginas educativas.
- `quiz.js`: carga, persistencia, respuestas, accesibilidad, feedback y puntuación.
- `docs/content-model.md`: política editorial.
- `data/question.schema.json`: esquema de preguntas.
- `data/questions.json`: banco inicial.
- `privacy/index.html`: política de privacidad.
- `sitemap.xml`: siete URLs públicas indexables.

## Próxima etapa

El siguiente trabajo previsto es crear una **tarjeta social dedicada de 1200×630** y normalizar Open Graph/Twitter en portada, cinco guías y privacidad. Actualmente las páginas siguen utilizando `favicon.svg` como imagen social.

## Enlaces

- Web: https://neuronova-apps.github.io/quizbible-app/
- Política de privacidad: https://neuronova-apps.github.io/quizbible-app/privacy/
- Repositorio: https://github.com/neuronova-apps/quizbible-app
- Ecosistema: https://neuronova-apps.github.io/

## Autoría

Proyecto personal desarrollado dentro del ecosistema Neuronova Apps.
