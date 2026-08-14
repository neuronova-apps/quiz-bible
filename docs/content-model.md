# Modelo de contenido bíblico de Quiz Bible

## Objetivo

Este documento define cómo debe representarse, revisar y publicar una pregunta de Quiz Bible antes de incorporarla a una experiencia jugable.

El objetivo es que cada pregunta sea:

- verificable mediante una o más referencias bíblicas explícitas;
- clara en español y comprensible fuera de contexto;
- resoluble sin depender de una interpretación doctrinal discutible;
- adecuada para feedback educativo después de responder;
- estable como dato, independiente de la interfaz del juego.

La estructura técnica formal se encuentra en `data/question.schema.json`.

## Alcance editorial inicial

El primer MVP debe priorizar preguntas sobre información que pueda comprobarse directamente en el texto bíblico o en un contexto narrativo inmediato, por ejemplo:

- personas y relaciones explícitas;
- lugares mencionados;
- acontecimientos narrados;
- acciones atribuidas directamente a personajes;
- orden o identificación de libros y secciones cuando sea inequívoco para el alcance definido;
- expresiones o enseñanzas cuando la respuesta pueda sostenerse con una referencia clara y sin convertir una interpretación confesional en hecho universal.

No deben utilizarse como respuesta correcta única, en la fase inicial:

- conclusiones doctrinales disputadas entre tradiciones cristianas;
- preguntas cuya respuesta dependa de una traducción específica sin declararlo;
- cronologías, autorías o reconstrucciones históricas discutidas presentadas como hechos indiscutibles;
- formulaciones que exijan aceptar una interpretación teológica particular;
- preguntas trampa basadas en ambigüedad de redacción.

Si un contenido potencialmente útil presenta sensibilidad interpretativa, debe permanecer en estado `draft` hasta que se reformule o se documente el criterio editorial correspondiente.

## Estructura de una pregunta

Cada pregunta utiliza los siguientes campos principales:

### Identidad y ciclo editorial

- `id`: identificador estable y único, por ejemplo `qb-evangelios-001`.
- `version`: versión del modelo de dato; inicialmente `1`.
- `status`: `draft`, `reviewed`, `approved` o `retired`.
- `language`: idioma del contenido; inicialmente `es`.

Una pregunta solo debe entrar al juego cuando tenga estado `approved`.

### Clasificación

- `category`: categoría editorial estable, por ejemplo `evangelios`, `personajes`, `lugares` o `eventos`.
- `difficulty`: `beginner`, `intermediate` o `advanced`.
- `contentType`:
  - `textual_fact`: la respuesta aparece de forma directa en el pasaje o relato indicado;
  - `contextual`: exige relacionar información inmediata de uno o más pasajes, sin añadir una conclusión doctrinal disputable.
- `tags`: palabras clave opcionales para búsqueda, selección o futuros modos de juego.

Las categorías se mantendrán como vocabulario editorial del proyecto y podrán ampliarse sin cambiar la estructura base del objeto.

## Enunciado y opciones

- `prompt`: pregunta completa, redactada de manera autosuficiente.
- `options`: entre 3 y 4 opciones con `id` y `text`.
- `correctOptionId`: identificador de una única opción correcta.

Reglas de redacción:

1. La pregunta debe tener una sola respuesta correcta dentro de las opciones disponibles.
2. Las opciones incorrectas deben ser plausibles, pero no engañosas por diferencias mínimas o trucos lingüísticos.
3. Las opciones deben tener una longitud y estilo razonablemente comparables para no revelar la solución por formato.
4. No debe usarse “todas las anteriores” ni “ninguna de las anteriores” en el MVP inicial.
5. Evitar negaciones dobles y preguntas del tipo “¿cuál NO...?” salvo que exista una razón educativa clara.

## Explicación educativa

- `explanation`: explicación breve que aparece después de responder.

La explicación debe:

- indicar por qué la respuesta correcta encaja con la referencia;
- aportar contexto útil sin convertir la respuesta en un sermón o comentario doctrinal;
- estar redactada principalmente como paráfrasis propia;
- evitar reproducir pasajes extensos de una traducción bíblica protegida por derechos de autor.

La interfaz actual muestra esta explicación una vez comprobada la respuesta y la oculta al pasar a la siguiente pregunta, reiniciar, finalizar o entrar en estado de error.

Cuando sea necesario citar texto literal en el futuro, la traducción y su licencia deberán estar documentadas antes de publicar ese contenido.

## Referencias bíblicas

Cada pregunta requiere al menos una entrada en `references`.

Cada referencia contiene:

- `book`: nombre normalizado del libro en español;
- `chapter`: capítulo;
- `verseStart`: primer versículo relevante;
- `verseEnd`: último versículo relevante, opcional;
- `display`: forma preparada para interfaz, por ejemplo `Génesis 1:1`;
- `translation`: traducción utilizada durante una revisión concreta, opcional;
- `note`: observación editorial breve, opcional.

La referencia canónica es el elemento de verificación principal. El modelo no obliga a una traducción concreta para permitir que el proyecto defina más adelante una política de traducciones y licencias.

La interfaz actual utiliza `display` para presentar la referencia después de comprobar la respuesta. No reproduce el texto completo del pasaje.

## Revisión y sensibilidad doctrinal

El objeto `review` registra el estado de comprobación editorial:

- `referenceChecked`: indica si la pregunta fue contrastada con las referencias declaradas;
- `singleCorrectAnswerChecked`: confirma que las opciones contienen una única respuesta válida;
- `doctrinalSensitivity`: `none` o `possible`;
- `notes`: observaciones internas opcionales.

Una pregunta con `doctrinalSensitivity: "possible"` no debe pasar a `approved` hasta ser reformulada o revisada de forma explícita.

## Política de fuentes

Para el MVP:

1. Toda pregunta debe incluir referencias bíblicas específicas.
2. La respuesta correcta debe poder justificarse con esas referencias sin depender de conocimiento externo obligatorio.
3. Comentarios, diccionarios, cronologías y estudios secundarios pueden servir para revisión interna, pero no sustituyen la referencia bíblica cuando la pregunta se presenta como contenido bíblico textual.
4. Las diferencias de traducción deben resolverse mediante redacción neutral o documentando la traducción necesaria.
5. Después de responder, la interfaz debe mostrar como mínimo la explicación editorial y la referencia bíblica preparada en los datos; no necesita reproducir un versículo completo para que la pregunta sea verificable.

## Ejemplo estructural

El siguiente ejemplo ilustra la forma del dato y no representa una pregunta publicada:

```json
{
  "id": "qb-categoria-001",
  "version": 1,
  "status": "draft",
  "language": "es",
  "category": "categoria",
  "difficulty": "beginner",
  "contentType": "textual_fact",
  "prompt": "Pregunta redactada en lenguaje claro",
  "options": [
    { "id": "a", "text": "Opción A" },
    { "id": "b", "text": "Opción B" },
    { "id": "c", "text": "Opción C" }
  ],
  "correctOptionId": "a",
  "explanation": "Explicación breve basada en la referencia declarada.",
  "references": [
    {
      "book": "Libro",
      "chapter": 1,
      "verseStart": 1,
      "display": "Libro 1:1"
    }
  ],
  "tags": [],
  "review": {
    "referenceChecked": false,
    "singleCorrectAnswerChecked": false,
    "doctrinalSensitivity": "none",
    "notes": ""
  }
}
```

## Flujo editorial recomendado

1. Crear la pregunta como `draft`.
2. Comprobar que el enunciado tenga una única lectura razonable.
3. Contrastar la respuesta con todas las referencias declaradas.
4. Revisar distractores y confirmar una sola opción correcta.
5. Revisar sensibilidad doctrinal y diferencias relevantes de traducción.
6. Redactar explicación educativa y paráfrasis propias.
7. Cambiar a `reviewed` después de la primera revisión completa.
8. Cambiar a `approved` únicamente cuando esté lista para ser incluida en el banco consumido por el juego.
9. Utilizar `retired` para retirar contenido sin reutilizar su `id`.

## Relación con el desarrollo

El modelo se utiliza en `data/questions.json`, que contiene el primer banco aprobado consumido por `quiz.js`. El motor mantiene separada la lógica de interfaz del contenido bíblico y filtra únicamente preguntas `approved` con opción correcta, explicación y referencia válidas.

Después de cada comprobación, la interfaz utiliza `explanation` y `references[].display` para presentar el contexto educativo de la respuesta. Esta mejora no cambia el contrato de datos ni añade almacenamiento de progreso.

La siguiente etapa del producto puede centrarse en persistencia local de avance y puntuación sin mezclar esa responsabilidad con el contenido bíblico.
