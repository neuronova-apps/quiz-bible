# Quiz Bible

Quiz Bible es un proyecto de Neuronova Apps orientado a una futura experiencia de preguntas y desafíos sobre contenidos bíblicos.

## Estado actual

**En desarrollo inicial.**

La versión web disponible es una **landing pública de presentación** y acceso a la política de privacidad. Actualmente no existe todavía un quiz jugable ni un banco público de preguntas aprobadas.

La web actual sí incluye:

- presentación del concepto Quiz Bible;
- identidad visual propia dentro de Neuronova Apps;
- navegación hacia privacidad y el ecosistema principal;
- diseño responsive;
- skip link y foco visible;
- módulo central de accesibilidad de Neuronova Apps;
- soporte para `prefers-reduced-motion`;
- metadatos SEO/social básicos;
- sitemap con portada y privacidad;
- modelo editorial y contrato técnico para futuras preguntas bíblicas.

Todavía no están implementados:

- preguntas jugables;
- banco de preguntas `approved` consumido por la interfaz;
- opciones de respuesta interactivas;
- comprobación y feedback;
- puntuación;
- categorías o niveles jugables;
- progreso o persistencia local;
- cuentas, sincronización o ranking.

Estas funciones deben considerarse futuras hasta estar implementadas y verificadas.

## Modelo de contenido bíblico

El repositorio dispone ahora de un modelo explícito para separar el contenido bíblico de la futura lógica de juego:

- `docs/content-model.md`: política editorial, reglas de redacción, referencias, revisión y flujo de aprobación;
- `data/question.schema.json`: JSON Schema que define la estructura técnica de cada pregunta.

Cada pregunta futura debe incluir como mínimo:

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

El MVP inicial priorizará hechos textuales y contexto directamente sustentable por referencias bíblicas. Las interpretaciones doctrinales discutibles no deben presentarse como una respuesta correcta universal. Una pregunta solo debe incorporarse al juego cuando su estado sea `approved` y se haya comprobado tanto la referencia como la existencia de una única respuesta correcta.

El modelo no obliga todavía a una traducción bíblica concreta. Las explicaciones deben redactarse principalmente como paráfrasis propias y cualquier cita literal futura deberá respetar la licencia de la traducción utilizada.

## Alcance de accesibilidad actual

La landing utiliza el módulo central de accesibilidad de Neuronova Apps y una base semántica accesible. Esto describe la página pública actual; no implica todavía validación de accesibilidad para una experiencia de quiz que aún no existe ni certificación formal WCAG.

## Estructura

- `index.html`: presentación principal y estado actual del proyecto.
- `styles.css`: estilos base compartidos.
- `hero-orbit.css`: estilos y animaciones de la órbita del hero.
- `docs/content-model.md`: modelo editorial del contenido bíblico.
- `data/question.schema.json`: contrato JSON Schema para preguntas.
- `privacy/index.html`: política de privacidad.
- `privacy/privacy.css`: estilos exclusivos de la política de privacidad.
- `sitemap.xml`: rutas públicas indexables.

## Próximas etapas

El modelo de contenido ya está definido. El siguiente trabajo previsto es crear un **primer quiz web funcional** apoyado en un banco inicial de preguntas revisadas conforme a este contrato, con selección de respuesta, comprobación, puntuación y reinicio.

## Enlaces

- Web: https://neuronova-apps.github.io/quizbible-app/
- Política de privacidad: https://neuronova-apps.github.io/quizbible-app/privacy/
- Repositorio: https://github.com/neuronova-apps/quizbible-app
- Ecosistema: https://neuronova-apps.github.io/

## Autoría

Proyecto personal desarrollado dentro del ecosistema Neuronova Apps.
