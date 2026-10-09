"""Extract paragraph-based legacy reports and shaded daily cards without editing Word."""
from __future__ import annotations

import argparse
from lab_config import configure_console
import hashlib
import json
import re
from pathlib import Path

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

DATE_RE = re.compile(r"^(20\d{2})\s*[年-]\s*(\d{1,2})\s*[月-]\s*(\d{1,2})\s*日?")
MARKER_RE = re.compile(r"【([^】]+)】")
SAMPLE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*-\d{8}-\d+(?:-B\d+)*")
FIELD_NAMES = {
    'record_id': '记录标识', 'origin_record_id': '来源记录标识', 'project': '项目', 'sample_id': '样品编号',
    'created_date': '创建日期', 'step': '步骤', 'source_sample': '来源样品',
    'source_step': '来源步骤', 'experiment_type': '实验类型', 'state': '当前状态',
    'today': '今日实验', 'details': '配方与细节', 'follow_up': '后续跟进',
    'risk': '问题与风险', 'context_version': '背景版本',
    'plan_stage': '方案工序', 'plan_id': '方案编号', 'plan_version': '方案版本',
}


def iter_blocks(document):
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def normalize_text(text):
    return '\n'.join(line.strip() for line in text.replace('\r', '\n').split('\n') if line.strip())


def parse_marker_fields(text):
    text = normalize_text(text)
    matches = list(MARKER_RE.finditer(text))
    return {m[1].strip(): text[m.end():matches[i+1].start() if i+1 < len(matches) else len(text)].strip(' \n:：|')
            for i, m in enumerate(matches)}


def extract_docx(path: Path):
    doc = Document(path)
    from lab_materials_docx import read_material_payload
    materials = read_material_payload(doc)
    records, parts = [], []
    current_date = None
    sample_status = None

    def flush():
        if not parts:
            return
        raw = normalize_text('\n'.join(parts))
        parts.clear()
        fields = parse_marker_fields(raw)
        if '项目' not in fields or '样品编号' not in fields:
            return
        record = {k: fields.get(v, '') for k, v in FIELD_NAMES.items()}
        record.update(date=current_date, raw=raw, fields=fields,
                      phenomenon=fields.get('实验现象', ''), data=fields.get('数据记录', ''))
        record['sample_ids'] = list(dict.fromkeys(SAMPLE_RE.findall(record['sample_id'])))
        # Identical legacy records in monthly snapshots get the same ID; no guessed identities.
        record['record_id'] = record['record_id'] or 'legacy-' + hashlib.sha256(
            ((current_date or '') + '\n' + raw).encode()).hexdigest()[:24]
        if record['record_id'] in materials:
            record['materials'] = materials[record['record_id']]
        records.append(record)

    for block in iter_blocks(doc):
        if isinstance(block, Table):
            if not block.rows:
                continue
            matrix = [[normalize_text(c.text) for c in row.cells] for row in block.rows]
            if matrix[0][0] == '样品编号':
                flush()
                sample_status = {'headers': matrix[0], 'rows': matrix[1:]}
                continue
            # Cards may use multiple rows. Avoid duplicating merged cell text.
            seen, texts = set(), []
            for row in block.rows:
                for cell in row.cells:
                    if cell._tc not in seen:
                        seen.add(cell._tc)
                        texts.append(cell.text)
            lines = '\n'.join(texts).splitlines()
            # This label belongs to the nested visible table, not the preceding field.
            lines = [line for line in lines if line.strip() != '用药与样品用量']
        else:
            lines = block.text.splitlines()
        for line in lines:
            line = line.strip()
            match = DATE_RE.match(line)
            if match:
                flush()
                y, m, d = match.groups()
                current_date = f'{y}-{int(m):02d}-{int(d):02d}'
            elif line.startswith('【样品进度追踪表】'):
                flush()
            elif line.startswith('【记录标识】') or (line.startswith('【项目】') and any('【项目】' in p for p in parts)):
                flush()
                parts.append(line)
            elif line and (parts or line.startswith('【项目】')):
                parts.append(line)
        if isinstance(block, Table):
            flush()
    flush()
    return {'source': str(path), 'records': records, 'sample_status': sample_status}


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_docx', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    data = extract_docx(args.input_docx)
    output = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding='utf-8')
    else:
        print(output)


if __name__ == '__main__':
    main()
