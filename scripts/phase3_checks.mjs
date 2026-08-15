import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, writeFile } from 'node:fs/promises';

const baseURL = process.env.SMOKE_BASE_URL || 'http://127.0.0.1:4173/';
const artifactsDir = 'artifacts/phase3';
const blockingImpacts = new Set(['critical', 'serious']);
const browser = await chromium.launch({ headless: true });
const failures = [];

function assert(condition, message) { if (!condition) throw new Error(message); }
async function saveFailure(page, label, details) {
  await mkdir(artifactsDir, { recursive: true });
  await page.screenshot({ path: `${artifactsDir}/${label}.png`, fullPage: true }).catch(() => {});
  await writeFile(`${artifactsDir}/${label}.json`, JSON.stringify(details, null, 2), 'utf8').catch(() => {});
}
function summarizeViolation(v) { return { id:v.id, impact:v.impact, help:v.help, helpUrl:v.helpUrl, nodes:v.nodes.map(n => ({target:n.target,failureSummary:n.failureSummary})) }; }

async function runAxe(label, viewport, setup) {
  const context = await browser.newContext({ viewport, reducedMotion:'reduce' });
  const page = await context.newPage();
  try {
    const response = await page.goto(baseURL, { waitUntil:'domcontentloaded', timeout:30_000 });
    assert(response && response.status() < 400, `${label}: la página no cargó correctamente.`);
    await page.locator('#quizApp[data-state="playing"], #quizApp[data-state="complete"]').waitFor({state:'attached',timeout:10_000}).catch(() => {});
    await page.waitForTimeout(300);
    if (setup) await setup(page);
    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter(v => blockingImpacts.has(v.impact));
    const advisory = results.violations.filter(v => !blockingImpacts.has(v.impact));
    console.log(`✓ axe ${label}: ${blocking.length} bloqueantes, ${advisory.length} informativas`);
    advisory.forEach(v => console.log(`  · ${v.impact || 'sin impacto'} ${v.id}: ${v.help}`));
    if (blocking.length) {
      const details = blocking.map(summarizeViolation);
      await saveFailure(page, `axe-${label}`, details);
      failures.push({label:`axe-${label}`,errors:details.map(v => `${v.impact} ${v.id}: ${v.help}`)});
      details.forEach(v => console.error(`  - ${v.impact} ${v.id}: ${v.help}`));
    }
  } catch (error) {
    await saveFailure(page, `axe-${label}-exception`, {error:error.message});
    failures.push({label:`axe-${label}`,errors:[error.message]});
  } finally { await context.close(); }
}

async function runFunctionalFlow() {
  const context = await browser.newContext({ viewport:{width:1280,height:800}, reducedMotion:'reduce' });
  const page = await context.newPage();
  try {
    await page.goto(baseURL, { waitUntil:'domcontentloaded', timeout:30_000 });
    const option = page.locator('input[name="quiz-answer"]').first();
    await option.waitFor({state:'visible',timeout:10_000});
    const beforeQuestion = (await page.locator('#quizQuestion').textContent()) || '';
    await option.check();
    assert(!(await page.locator('#checkAnswer').isDisabled()), 'Seleccionar una respuesta no habilitó Comprobar.');
    await page.locator('#checkAnswer').click();
    assert(await page.locator('#quizLearning').isVisible(), 'Comprobar no mostró el contexto educativo.');
    assert(await page.locator('#nextQuestion').isVisible(), 'Comprobar no habilitó la continuación.');
    assert(((await page.locator('#quizExplanation').textContent()) || '').trim().length > 0, 'La explicación educativa quedó vacía.');
    await page.locator('#nextQuestion').click();
    await page.waitForTimeout(100);
    assert(((await page.locator('#quizQuestion').textContent()) || '') !== beforeQuestion, 'El quiz no avanzó a la siguiente pregunta.');
    assert(((await page.locator('#quizProgress').textContent()) || '').includes('2'), 'El progreso no avanzó a la pregunta 2.');
    console.log('✓ funcional Quiz Bible: selección, feedback educativo y avance de pregunta');
  } catch (error) {
    await saveFailure(page, 'functional-quizbible', {error:error.message});
    failures.push({label:'functional-quizbible',errors:[error.message]});
    console.error(`✗ funcional Quiz Bible: ${error.message}`);
  } finally { await context.close(); }
}

await runAxe('home-desktop', {width:1440,height:900});
await runAxe('home-mobile-menu', {width:390,height:844}, async page => {
  const menu = page.locator('header .menu-button, header .menu').first();
  if ((await menu.count()) && (await menu.isVisible())) await menu.click();
});
await runFunctionalFlow();
await browser.close();
if (failures.length) { console.error(`\nFase 3 falló en ${failures.length} comprobación(es).`); process.exit(1); }
console.log('\nFase 3 superada: accesibilidad automática y flujo funcional principal verificados.');
