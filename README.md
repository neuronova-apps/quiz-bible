# Quiz Bible

Quiz Bible es una aplicación educativa de Neuronova Apps orientada a aprender y repasar contenidos bíblicos mediante preguntas, explicaciones, referencias y recursos públicos de apoyo.

## Estado del proyecto

- **Web:** MVP funcional en desarrollo activo.
- **Publicación:** disponible mediante GitHub Pages.
- **Android:** existe una rama `android` separada para el desarrollo móvil. Se considera trabajo en progreso y no una versión estable o publicada.

## Funciones disponibles

- quiz jugable de seis preguntas aprobadas;
- cuatro opciones por pregunta;
- comprobación de una respuesta por pregunta;
- explicación educativa y referencia bíblica después de responder;
- puntuación calculada desde el banco actual;
- restauración del progreso mediante `localStorage`;
- reinicio explícito del progreso;
- flujo de teclado y foco reforzado;
- cinco guías educativas públicas e indexables;
- tarjeta social 1200 × 630 y metadatos Open Graph/Twitter;
- política de privacidad y sitemap público.

El contenido prioriza hechos textuales y referencias verificables. Las interpretaciones doctrinales discutibles no se presentan como respuestas universales.

## Tecnología

La versión web utiliza:

- HTML5;
- CSS3;
- JavaScript en el navegador;
- JSON para el banco de preguntas;
- JSON Schema para el contrato del contenido;
- `localStorage` para progreso local;
- GitHub Pages;
- módulo de accesibilidad compartido de Neuronova Apps.

No requiere proceso de compilación para ejecutar la web actual.

## Accesibilidad

Quiz Bible utiliza controles nativos, `fieldset`, radios, instrucciones de teclado, foco visible, estados textuales para respuestas, regiones de estado y gestión programática del foco al avanzar, reiniciar y completar el quiz.

Estas medidas no constituyen una certificación WCAG y siguen pendientes pruebas manuales exhaustivas con tecnologías de asistencia.

## Privacidad

La versión actual no requiere cuenta ni sincronización remota. El progreso permanece en el navegador y puede eliminarse mediante el reinicio del quiz.

Política pública:

https://neuronova-apps.github.io/quizbible-app/privacy/

## Desarrollo local

Para que la carga de `data/questions.json` funcione correctamente, utiliza un servidor HTTP local:

```bash
git clone https://github.com/neuronova-apps/quizbible-app.git
cd quizbible-app
python3 -m http.server 8000
```

Después abre `http://localhost:8000`.

La rama `main` corresponde a la versión web pública. La rama `android` mantiene el trabajo móvil separado.

## Estructura principal

- `index.html`: presentación y quiz;
- `quiz.js`: carga, respuestas, persistencia y puntuación;
- `data/questions.json`: banco actual;
- `data/question.schema.json`: contrato del contenido;
- `docs/content-model.md`: política editorial;
- `styles.css`, `quiz.css`, `hero-orbit.css` y `guide-cards.css`: sistema visual;
- páginas HTML educativas: cinco guías públicas;
- `resources.css`: estilos de las guías;
- `privacy/`: política pública;
- `assets/social/`: tarjeta social;
- `sitemap.xml`: URLs indexables.

## Enlaces

- **Web:** https://neuronova-apps.github.io/quizbible-app/
- **Privacidad:** https://neuronova-apps.github.io/quizbible-app/privacy/
- **Repositorio:** https://github.com/neuronova-apps/quizbible-app
- **Ecosistema:** https://neuronova-apps.github.io/

## Neuronova Apps

Quiz Bible forma parte de **Neuronova Apps** y comparte con el ecosistema criterios de diseño, accesibilidad, privacidad, SEO, documentación y publicación web.

## Autoría

Proyecto personal e independiente desarrollado por Gabriel Berrospi dentro del ecosistema Neuronova Apps.
