import fs from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const program = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token.startsWith("--")) {
      args[token.slice(2)] = argv[index + 1];
      index += 1;
    }
  }
  return args;
}

const cli = parseArgs(process.argv.slice(2));
if (!cli.summary || !cli.outputDir) throw new Error("Required: --summary INPUT.json --outputDir OUTPUT_DIR");
const summaryPath = cli.summary;
const templatePath = cli.template ?? path.join(program, "templates", "monthly-summary.xlsx");

const summary = JSON.parse(await fs.readFile(summaryPath, "utf8"));
const [year, month] = summary.month.split("-");
const outputDir = cli.outputDir;
if (!summary.rows?.length) throw new Error("No summary rows to export");
const outputPath =
  cli.output ?? path.join(outputDir, `新品月度研发工作总结_${year}年${month}月.xlsx`);
const previewPath =
  cli.preview ?? path.join(outputDir, `monthly_report_${year}_${month}_preview.png`);

function rowRange(rowIndex) {
  return `A${rowIndex}:E${rowIndex}`;
}

function estimateRowHeightPx(row) {
  const contentLines = row.content.split(/\n/).length;
  const contentWrap = Math.ceil(row.content.length / 90);
  const commentWrap = Math.ceil(row.comment.length / 32);
  const targetWrap = Math.ceil(row.target.length / 28);
  const lines = Math.max(contentLines + contentWrap, commentWrap, targetWrap);
  return Math.min(780, Math.max(180, lines * 15));
}

const input = await FileBlob.load(templatePath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheet = workbook.worksheets.getItemAt(0);
sheet.name = summary.sheet_name;

// Remove sample-month sheets from the template after the target sheet is ready.
for (;;) {
  try {
    const extraSheet = workbook.worksheets.getItemAt(1);
    if (!extraSheet || extraSheet.name === sheet.name) break;
    extraSheet.delete();
  } catch {
    break;
  }
}

sheet.showGridLines = false;
sheet.freezePanes.freezeRows(2);

const usedRows = summary.rows.length + 2;
sheet.getRange(`A1:E${Math.max(200, usedRows)}`).unmerge();
sheet.getRange(`A1:E${Math.max(200, usedRows)}`).clear({ applyTo: "contents" });

sheet.getRange("A1:E1").merge();
sheet.getRange("A1").values = [[summary.title]];
sheet.getRange("A1:E1").format = {
  fill: "#EEF4F8",
  font: { name: "Microsoft YaHei", bold: true, size: 15, color: "#1F2937" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: "#D6DEE6" },
};
sheet.getRange("A1:E1").format.rowHeightPx = 38;

sheet.getRange("A2:E2").values = [[
  "周次",
  "项目名称",
  "项目目标",
  "研发内容（含配方细节/现象/数据）",
  "小结点评",
]];
sheet.getRange("A2:E2").format = {
  fill: "#1F4E78",
  font: { name: "Microsoft YaHei", bold: true, color: "#FFFFFF", size: 10 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#D6DEE6" },
};
sheet.getRange("A2:E2").format.rowHeightPx = 34;

const values = summary.rows.map((row) => [
  row.week,
  row.project,
  row.target,
  row.content,
  row.comment,
]);
sheet.getRangeByIndexes(2, 0, values.length, 5).values = values;

const widths = [78, 226, 330, 960, 390];
for (let col = 0; col < widths.length; col += 1) {
  sheet.getRangeByIndexes(0, col, Math.max(usedRows, 12), 1).format.columnWidthPx = widths[col];
}

sheet.getRange(`A1:E${usedRows}`).format = {
  font: { name: "Microsoft YaHei", size: 9, color: "#111827" },
  wrapText: true,
  verticalAlignment: "top",
  borders: { preset: "all", style: "thin", color: "#D6DEE6" },
};

sheet.getRange("A1:E1").format = {
  fill: "#EEF4F8",
  font: { name: "Microsoft YaHei", bold: true, size: 15, color: "#1F2937" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: "#D6DEE6" },
};
sheet.getRange("A2:E2").format = {
  fill: "#1F4E78",
  font: { name: "Microsoft YaHei", bold: true, color: "#FFFFFF", size: 10 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#D6DEE6" },
};

for (let index = 0; index < summary.rows.length; index += 1) {
  const rowIndex = index + 3;
  const row = summary.rows[index];
  const range = sheet.getRange(rowRange(rowIndex));
  range.format = {
    font: { name: "Microsoft YaHei", size: 8, color: "#111827" },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#D6DEE6" },
  };
  range.format.rowHeightPx = estimateRowHeightPx(row);
  sheet.getRange(`A${rowIndex}:B${rowIndex}`).format = {
    fill: "#F7FBFD",
    font: { name: "Microsoft YaHei", size: 8, bold: true, color: "#1F2937" },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#D6DEE6" },
  };
  sheet.getRange(`A${rowIndex}:A${rowIndex}`).format = {
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    font: { name: "Microsoft YaHei", size: 8, bold: true, color: "#1F2937" },
    borders: { preset: "all", style: "thin", color: "#D6DEE6" },
  };
  sheet.getRange(`E${rowIndex}:E${rowIndex}`).format = {
    fill: "#FFFDF4",
    font: { name: "Microsoft YaHei", size: 8, color: "#111827" },
    wrapText: true,
    verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#D6DEE6" },
  };
}

const inspection = await workbook.inspect({
  kind: "table",
  range: `${summary.sheet_name}!A1:E${usedRows}`,
  include: "values",
  tableMaxRows: 10,
  tableMaxCols: 5,
  tableMaxCellChars: 120,
  maxChars: 6000,
});
console.log(inspection.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(outputDir, { recursive: true });
const preview = await workbook.render({
  sheetName: summary.sheet_name,
  range: `A1:E${usedRows}`,
  scale: 1,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`preview=${previewPath}`);
console.log(`output=${outputPath}`);
