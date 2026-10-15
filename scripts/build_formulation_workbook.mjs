import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const [input, output] = process.argv.slice(2);
if (!input || !output) throw new Error('Usage: build_formulation_workbook.mjs SNAPSHOT.json OUTPUT.xlsx');
try { await fs.access(output); throw new Error('Output exists; choose a new filename'); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const batch = JSON.parse(await fs.readFile(input, 'utf8'));
const wb = Workbook.create();
const overview = wb.worksheets.add('配方总览');
const details = wb.worksheets.add('参数与计算');
const title = `${batch.project_id} ${batch.batch_id} 第${batch.revision}版配方`;
const literal = value => typeof value === 'string' && /^[=+@-]/.test(value) ? "'" + value : value;
const numeric = value => {
  const n = Number(value);
  const nonzero = String(value).split(/[eE]/)[0].replace(/[+\-0.]/g, '') !== '';
  if (!Number.isFinite(n) || (n === 0 && nonzero)) throw new Error('Value is outside Excel numeric range: ' + value);
  return n;
};
const readable = value => typeof value === 'object' ? JSON.stringify(value) : String(value);
const gradient = group => Object.entries(group.gradient).map(([k, v]) => `${k}: ${readable(v)}`).join('\n') || '基准组';
const qa = {batch_id: batch.batch_id, revision: batch.revision, comparisons: 0, previews: [], sheets: [], input_change: null};
const expected = [];
let overviewRow = 6;
let detailRow = 6;

function setup(sheet, headers, lastCol, subtitle) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(5);
  sheet.getRange('A2').values = [[literal(title)]];
  sheet.getRange('A3').values = [[subtitle]];
  sheet.getRange(`A5:${lastCol}5`).values = [headers];
  sheet.getRange(`A1:${lastCol}5`).format.font.name = 'Microsoft YaHei';
  sheet.getRange(`A2:${lastCol}2`).format = {font: {name: 'Microsoft YaHei', color: '#17365D', size: 16, bold: true}, rowHeightPx: 38, wrapText: false};
  sheet.getRange(`A3:${lastCol}3`).format = {font: {name: 'Microsoft YaHei', size: 11, color: '#475569'}, wrapText: false, rowHeightPx: 28};
  sheet.getRange(`A5:${lastCol}5`).format = {fill: '#DDEBF7', font: {name: 'Microsoft YaHei', bold: true, size: 11, color: '#17365D'}, wrapText: true, rowHeightPx: 36, horizontalAlignment: 'center', verticalAlignment: 'center'};
}
setup(overview, ['实验组', '梯度', '重复', '原料', '计划用量', '单位', '方案版本', '待补与说明'], 'H',
  '计划计算值；实际称量及结果在确认实验完成后记入日报。Excel修改不自动更新已保存方案。');
setup(details, ['实验组', '参数或计算步骤', '数值', '单位', '输入来源', '公式说明'], 'F',
  '蓝色数值为输入，黑色数值为公式。计算基准和来源随输入保存；缺失数据不按零处理。');
const groupRows = [];
for (const group of batch.groups) {
  const start = detailRow;
  const nodes = group.result.nodes;
  const rows = nodes.map(node => [group.group_id, literal(node.label), node.op ? null : numeric(node.value), node.unit,
    literal(node.source || '由前列输入和计算步骤推导'), node.op ? `${node.op}(${node.args.map(i => `C${start + i}`).join(', ')})` : '输入']);
  if (rows.length) details.getRange(`A${start}:F${start + rows.length - 1}`).values = rows;
  nodes.forEach((node, i) => {
    const cell = `C${start + i}`;
    if (node.op) {
      const args = node.args.map(index => `C${start + index}`);
      let formula;
      if (node.op === 'sum') formula = args.length ? `=${args.join('+')}` : '=0';
      else formula = `=${args[0]}${{mul: '*', div: '/', sub: '-'}[node.op]}${args[1]}`;
      details.getRange(cell).formulas = [[formula]];
    } else {
      details.getRange(cell).format.font.color = '#2563EB';
    }
    expected.push({sheet: details, cell, value: numeric(node.value)});
  });
  for (const material of group.result.materials) {
    const out = group.result.outputs[material.id];
    const node = out ? nodes[out.node] : null;
    const note = group.result.pending.join('\n');
    overview.getRange(`A${overviewRow}:H${overviewRow}`).values = [[group.group_id, literal(gradient(group)), group.repeat,
      literal(material.name), null, node?.unit || '待补', group.plan_version, literal(note || '—')]];
    if (node) {
      overview.getRange(`E${overviewRow}`).formulas = [[`='参数与计算'!C${start + out.node}`]];
      expected.push({sheet: overview, cell: `E${overviewRow}`, value: numeric(node.value)});
    } else overview.getRange(`E${overviewRow}`).values = [['待补']];
    groupRows.push({group, out, cell: `E${overviewRow}`, start});
    overviewRow += 1;
  }
  detailRow += rows.length;
}

for (const [sheet, lastRow, lastCol] of [[overview, overviewRow - 1, 'H'], [details, detailRow - 1, 'F']]) {
  if (lastRow >= 6) {
    const body = sheet.getRange(`A6:${lastCol}${lastRow}`);
    body.format.font.name = 'Microsoft YaHei';
    body.format.font.size = 11;
    body.format.wrapText = true;
    body.format.verticalAlignment = 'center';
    body.format.rowHeightPx = 52;
    body.format.borders = {preset: 'inside', style: 'hair', color: '#E2E8F0'};
    sheet.tables.add(`A5:${lastCol}${lastRow}`, true, sheet === overview ? 'FormulationGroups' : 'FormulationCalculations');
  }
}
const widths = [[overview, {A: 125, B: 185, C: 55, D: 145, E: 130, F: 75, G: 85, H: 320}],
  [details, {A: 125, B: 265, C: 150, D: 110, E: 350, F: 225}]];
for (const [sheet, columns] of widths) for (const [col, width] of Object.entries(columns)) sheet.getRange(`${col}:${col}`).format.columnWidthPx = width;
overview.getRange(`E6:E${Math.max(6, overviewRow - 1)}`).setNumberFormat('General');
details.getRange(`C6:C${Math.max(6, detailRow - 1)}`).setNumberFormat('General');
// Expand source/pending rows to fit actual text instead of clipping long notes.
for (let r = 6; r < overviewRow; r++) {
  const notes = String(overview.getRange(`H${r}`).values[0][0]);
  const lines = notes.split('\n').reduce((n, s) => n + Math.max(1, Math.ceil(s.length / 21)), 0);
  overview.getRange(`A${r}:H${r}`).format.rowHeightPx = Math.max(52, lines * 18 + 10);
}
for (let r = 6; r < detailRow; r++) {
  const values = details.getRange(`A${r}:F${r}`).values[0];
  const lines = Math.max(Math.ceil(String(values[1] || '').length / 18), Math.ceil(String(values[4] || '').length / 24), 2);
  details.getRange(`A${r}:F${r}`).format.rowHeightPx = lines * 18 + 10;
}
wb.recalculate();
for (const item of expected) {
  const actual = item.sheet.getRange(item.cell).values[0][0];
  if (typeof actual !== 'number' || Math.abs(actual - item.value) > Math.max(1e-12, Math.abs(item.value) * 1e-10))
    throw new Error(`Formula differs from Decimal engine at ${item.sheet.name}!${item.cell}: ${actual} != ${item.value}`);
  qa.comparisons++;
}
// Verify a live dependency, then restore the input before the final recalculation/export.
for (const {group, out, cell, start} of groupRows) {
  if (!out) continue;
  const nodes = group.result.nodes;
  const leaves = index => nodes[index].op ? nodes[index].args.flatMap(leaves) : [index];
  const candidate = leaves(out.node).find(i => Number(nodes[i].value) > 0);
  const before = overview.getRange(cell).values[0][0];
  if (candidate === undefined || before === 0) continue;
  const inputCell = `C${start + candidate}`;
  const original = details.getRange(inputCell).values[0][0];
  details.getRange(inputCell).values = [[original * 1.01]];
  wb.recalculate();
  const changed = overview.getRange(cell).values[0][0];
  details.getRange(inputCell).values = [[original]];
  wb.recalculate();
  if (changed === before) continue; // A shared ratio can algebraically cancel itself.
  qa.input_change = {cell: inputCell, output: cell, changed: true, restored: overview.getRange(cell).values[0][0] === before};
  if (!qa.input_change.restored) throw new Error('Input-change verification did not restore output');
  break;
}
const errors = await wb.inspect({kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',
  options: {useRegex: true, maxResults: 30}, maxChars: 4000});
qa.formula_error_scan = errors.ndjson;
if (/"(?:value|text|displayValue)"\s*:\s*"#(?:REF!|DIV\/0!|VALUE!|NAME\?|N\/A|NUM!|NULL!|SPILL!|CALC!)/.test(errors.ndjson))
  throw new Error('Workbook formula error: ' + errors.ndjson);
await fs.mkdir(path.dirname(output), {recursive: true});
const qaDir = output.replace(/\.xlsx$/i, '') + '_qa';
await fs.mkdir(qaDir, {recursive: true});
for (const [sheet, end, col] of [[overview, overviewRow - 1, 'H'], [details, detailRow - 1, 'F']]) {
  qa.sheets.push({name: sheet.name, rows: end});
  // Bound each image's height; render every used row on both sheets.
  let first = 1, page = 1;
  while (first <= end) {
    let last = first, height = 0;
    while (last <= end && (height < 900 || last === first)) {
      height += sheet.getRange(`A${last}`).format.rowHeightPx || 25;
      last++;
    }
    last--;
    const blob = await wb.render({sheetName: sheet.name, range: `A${first}:${col}${last}`, scale: 1.5, format: 'png'});
    const file = path.join(qaDir, `${sheet.name}_${page++}.png`);
    await fs.writeFile(file, new Uint8Array(await blob.arrayBuffer()));
    qa.previews.push(file);
    first = last + 1;
  }
}
const file = await SpreadsheetFile.exportXlsx(wb);
await file.save(output);
await fs.writeFile(output.replace(/\.xlsx$/i, '.qa.json'), JSON.stringify(qa, null, 2));
console.log(JSON.stringify({path: output, comparisons: qa.comparisons, previews: qa.previews, input_change: qa.input_change}));
