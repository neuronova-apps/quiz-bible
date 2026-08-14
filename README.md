# Quiz Bible

Quiz Bible es un proyecto de Neuronova Apps orientado a una futura experiencia de preguntas y desafíos sobre contenidos bíblicos.

## Estado actual

**En desarrollo inicial.**

La versión web disponible es una **landing pública de presentación** y acceso a la política de privacidad. Actualmente no existe todavía un quiz jugable ni un banco público de preguntas dentro del repositorio.

La web actual sí incluye:

- presentación del concepto Quiz Bible;
- identidad visual propia dentro de Neuronova Apps;
- navegación hacia privacidad y el ecosistema principal;
- diseño responsive;
- skip link y foco visible;
- módulo central de accesibilidad de Neuronova Apps;
- soporte para `prefers-reduced-motion`;
- metadatos SEO/social básicos;
- sitemap con portada y privacidad.

Todavía no están implementados:

- preguntas jugables;
- opciones de respuesta;
- comprobación y feedback;
- puntuación;
- categorías o niveles;
- progreso o persistencia local;
- cuentas, sincronización o ranking.

Estas funciones deben considerarse futuras hasta estar implementadas y verificadas.

## Alcance de accesibilidad actual

La landing utiliza el módulo central de accesibilidad de Neuronova Apps y una base semántica accesible. Esto describe la página pública actual; no implica todavía validación de accesibilidad para una experiencia de quiz que aún no existe ni certificación formal WCAG.

## Estructura

- `index.html`: presentación principal y estado actual del proyecto.
- `styles.css`: estilos base compartidos.
- `hero-orbit.css`: estilos y animaciones de la órbita del hero.
- `privacy/index.html`: política de privacidad.
- `privacy/privacy.css`: estilos exclusivos de la política de privacidad.
- `sitemap.xml`: rutas públicas indexables.

## Próximas etapas

El desarrollo de la experiencia jugable se documentará de forma incremental. El siguiente trabajo previsto es definir un modelo de contenido bíblico verificable para preguntas, opciones, respuesta correcta, explicación y referencia antes de construir el primer quiz funcional.

## Enlaces

- Web: https://neuronova-apps.github.io/quizbible-app/
- Política de privacidad: https://neuronova-apps.github.io/quizbible-app/privacy/
- Repositorio: https://github.com/neuronova-apps/quizbible-app
- Ecosistema: https://neuronova-apps.github.io/

## Autoría

Proyecto personal desarrollado dentro del ecosistema Neuronova Apps.
