// Local fallback for plan QA when the Documents LibreOffice renderer is unavailable.
// Uses the bundled artifact-tool DOCX importer/layout engine, not native Word or a cloud service.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {DocumentFile, FileBlob, layoutDocumentPages, drawDocumentToCtx} from '@oai/artifact-tool';
const {Canvas} = createRequire(import.meta.resolve('@oai/artifact-tool'))('skia-canvas');

if (process.argv.length !== 4) throw new Error('Usage: render_lab_plan_docx.mjs INPUT.docx OUTPUT_DIR');
const input = path.resolve(process.argv[2]);
const output = path.resolve(process.argv[3]);
if (!input.toLowerCase().endsWith('.docx')) throw new Error('Input must be a DOCX file');
const document = await DocumentFile.importDocx(await FileBlob.load(input));
const measuring = new Canvas(816, 1056);
const pages = layoutDocumentPages(document, measuring.getContext('2d'));
await fs.mkdir(output, {recursive: true});
const layout = await document.export({format: 'layout'});
await fs.writeFile(path.join(output, 'layout.json'), new Uint8Array(await layout.arrayBuffer()));
const images = [];
for (let i = 0; i < pages.length; i++) {
  const canvas = new Canvas(Math.ceil(pages[i].widthPx * 1.5), Math.ceil(pages[i].heightPx * 1.5));
  const context = canvas.getContext('2d');
  context.scale(1.5, 1.5);
  drawDocumentToCtx(document, context, {pageIndex: i, drawPageOutline: false});
  const file = path.join(output, `page-${i + 1}.png`);
  await fs.writeFile(file, await canvas.toBuffer('png'));
  images.push(file);
}
const report = {input, engine: 'bundled-artifact-tool', pages: pages.length, images};
await fs.writeFile(path.join(output, 'render-report.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
