# Quiz Bible

Quiz Bible es una aplicación educativa de Neuronova Apps orientada a aprender y repasar contenidos bíblicos mediante preguntas, explicaciones, referencias y recursos públicos de apoyo.

## Estado del proyecto

- **Web:** MVP funcional en desarrollo activo.
- **Publicación:** disponible mediante GitHub Pages.
- **Android:** rama `android` separada en trabajo en progreso; no es una versión estable ni publicada.

## Alcance actual

La versión pública ofrece un quiz breve y funcional con contenido bíblico revisado, feedback educativo y progreso local. Su objetivo actual es aprender y repasar mediante preguntas concretas, no ofrecer formación teológica completa ni resolver interpretaciones doctrinales discutibles como respuestas universales.

## Funciones disponibles

- quiz jugable de seis preguntas aprobadas;
- cuatro opciones por pregunta y una respuesta comprobable;
- explicación educativa y referencia bíblica después de responder;
- puntuación calculada desde el banco actual;
- restauración y reinicio del progreso mediante `localStorage`;
- flujo de teclado y foco reforzado;
- cinco guías educativas públicas e indexables;
- tarjeta social 1200 × 630, metadatos Open Graph/Twitter, política de privacidad y sitemap público.

## Tecnología

La versión web utiliza HTML5, CSS3, JavaScript en el navegador, JSON para el banco de preguntas, JSON Schema para el contrato del contenido, `localStorage`, GitHub Pages y el módulo compartido de accesibilidad de Neuronova Apps. No requiere un proceso de compilación para ejecutar la web actual.

## Accesibilidad

Quiz Bible utiliza controles nativos, `fieldset`, radios, instrucciones de teclado, foco visible, estados textuales, regiones de estado y gestión programática del foco al avanzar, reiniciar y completar el quiz.

La superficie pública forma parte de la auditoría automática central del ecosistema con axe-core. Estas medidas y pruebas no constituyen una certificación WCAG. Continúan pendientes revisiones manuales sistemáticas con teclado, lectores de pantalla, zoom, contraste y dispositivos.

## Privacidad

La versión actual no requiere cuenta ni sincronización remota. El progreso permanece en el navegador y puede eliminarse mediante el reinicio del quiz.

Política pública: https://neuronova-apps.github.io/quizbible-app/privacy/

## Limitaciones conocidas

El banco público actual es reducido y no representa todavía la amplitud prevista del proyecto. No existen niveles completos ni una experiencia de progresión extensa. La rama Android sigue separada y no debe presentarse como aplicación móvil publicada. La revisión manual completa de accesibilidad continúa pendiente.

## Roadmap

Las siguientes líneas de trabajo son ampliar el banco de preguntas, desarrollar niveles progresivos, profundizar la experiencia interactiva, mantener la revisión editorial del contenido y completar pruebas manuales de accesibilidad antes de realizar afirmaciones de conformidad más amplias.

## Desarrollo local

```bash
git clone https://github.com/neuronova-apps/quizbible-app.git
cd quizbible-app
python3 -m http.server 8000
```

Después abre `http://localhost:8000`. La rama `main` corresponde a la versión web pública y `android` mantiene el trabajo móvil separado.

## Estructura principal

- `index.html`: presentación y quiz;
- `quiz.js`: carga, respuestas, persistencia y puntuación;
- `data/questions.json`: banco actual;
- `data/question.schema.json`: contrato del contenido;
- `docs/content-model.md`: política editorial;
- hojas CSS: sistema visual y recursos;
- páginas HTML educativas: cinco guías públicas;
- `privacy/`: política pública;
- `assets/social/`: tarjeta social;
- `sitemap.xml`: URLs indexables.

## Enlaces

- **Web:** https://neuronova-apps.github.io/quizbible-app/
- **Privacidad:** https://neuronova-apps.github.io/quizbible-app/privacy/
- **Repositorio:** https://github.com/neuronova-apps/quizbible-app
- **Ecosistema:** https://neuronova-apps.github.io/

## Neuronova Apps

Quiz Bible forma parte de Neuronova Apps y comparte con el ecosistema criterios de diseño, accesibilidad, privacidad, SEO, documentación y publicación web, manteniendo su repositorio y evolución técnica independientes.

## Autoría

Proyecto personal e independiente desarrollado por Gabriel Berrospi dentro del ecosistema Neuronova Apps.

## Última revisión

2026-08-15
