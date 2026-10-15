"""Formulation batches: preview/save/list/show/export/complete, with recoverable daily writes."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from decimal import Decimal

from lab_config import configure_console, data_root, PROGRAM_ROOT
from lab_formulation_calc import expand, fields, text
from lab_plans import PlanStore, identifier, atomic_write, json_bytes, read_json
from lab_quantities import PROPERTIES, raw_materials, format_number
from lab_records import Store, STATES


SAVE_FIELDS = ('project_id', 'stage_id', 'stage_name', 'batch_id', 'operation_id', 'description',
               'recipe', 'variables', 'combination', 'repeats', 'base_version', 'plan_content', 'date')
REPORT_FIELDS = ('date', 'created_date', 'sample_id', 'step', 'state', 'experiment_type', 'today',
                 'follow_up', 'details', 'as_planned', 'materials', 'observed_patch', 'source_sample', 'source_step', 'context_version')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def today(offset='+08:00'):
    if not re.fullmatch(r'[+-]\d{2}:\d{2}', offset):
        raise ValueError('timezone须为±HH:MM')
    hour, minute = map(int, offset[1:].split(':'))
    if minute > 59 or hour > 14 or (hour == 14 and minute):
        raise ValueError('无效时区偏移')
    delta = timedelta(hours=hour, minutes=minute) * (1 if offset[0] == '+' else -1)
    return datetime.now(timezone(delta)).date().isoformat()


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError('批次正在写入；异常退出后先确认无写入进程，再移除该锁：' + str(path)) from exc
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        path.unlink()


def planned_materials(group):
    result = group['result']
    rows = []
    for material in result['materials']:
        mid = material['id']
        out = result['outputs'].get(mid)
        quantity = result['nodes'][out['node']] if out else None
        props = {k: v for k, v in material.get('properties', {}).items() if k in PROPERTIES}
        row = dict(operation='配方投料', name=material['name'], role=material.get('role', '原料'),
                   material_type=material.get('material_type', 'unknown'), quantity_kind='planned',
                   original=(format_number(Decimal(quantity['value'])) + ' ' + quantity['unit'] + '（计划计算值）') if quantity else '计划用量待补',
                   properties=props, measurements=[],
                   note='配方计算值；不是天平读数。计算依据保存在批次快照。')
        if material.get('component'):
            row['component'] = material['component']
        if material.get('formula'):
            row['formula'] = material['formula']
        if quantity:
            row['measurements'] = [dict(kind=out['kind'], value=quantity['value'], unit=quantity['unit'],
                                         basis=out['basis'], source='批次配方计算（计划）')]
        rows.append(row)
    return rows


class BatchStore:
    def __init__(self, root, project, stage, batch):
        self.root = Path(root).resolve()
        self.project, self.stage, self.batch = map(identifier, (project, stage, batch))
        self.plans = PlanStore(self.root, self.project, self.stage)
        self.folder = self.plans.folder / 'batches'
        self.path = self.folder / (self.batch + '.json')
        if not self.path.resolve().is_relative_to(self.root):
            raise ValueError('批次路径超出数据目录')

    def load(self):
        data = read_json(self.path)
        if data.get('schema_version') != 1 or (data.get('project_id'), data.get('stage_id'), data.get('batch_id')) != (self.project, self.stage, self.batch):
            raise ValueError('批次版本或身份不一致')
        return data

    def write(self, data):
        atomic_write(self.path, json_bytes(data))

    def preview(self, request):
        fields(request, SAVE_FIELDS, '批次')
        text(request.get('description'), '原始要求')
        from lab_plans import validate_content
        validate_content(request.get('plan_content', {}))
        if (request.get('project_id'), request.get('stage_id'), request.get('batch_id')) != (self.project, self.stage, self.batch):
            raise ValueError('输入项目、工序、批次不一致')
        stage_name = text(request.get('stage_name', self.stage), '工序名称')
        if not self.plans.path.exists():
            if 'base_version' in request:
                raise ValueError('新工序尚无可引用的基准版本')
            for path in self.plans.folder.parent.glob('*/plan.json'):
                other = read_json(path)
                if other['stage_name'].strip().casefold() == stage_name.strip().casefold():
                    raise ValueError('该工序已存在，请复用编号：' + other['stage_id'])
        groups = expand(request)
        if not groups:
            raise ValueError('批次没有实验组')
        return dict(project_id=self.project, stage_id=self.stage, batch_id=self.batch,
                    groups=groups, group_count=len(groups), description=request['description'])

    def show(self, revision=None):
        data = self.load()
        revision = len(data['revisions']) if revision is None else revision
        if isinstance(revision, bool) or not isinstance(revision, int) or not 1 <= revision <= len(data['revisions']):
            raise ValueError('批次版本不存在')
        result = deepcopy(data['revisions'][revision - 1])
        result.update(project_id=self.project, stage_id=self.stage, batch_id=self.batch)
        result['completions'] = {g['group_id']: deepcopy(data['completions'].get(f'{revision}:{g["group_id"]}')) for g in result['groups']}
        return result

    def save(self, request):
        preview = self.preview(request)
        operation = text(request.get('operation_id'), '稳定操作编号')
        signature = fingerprint(request)
        with locked(self.folder / (self.batch + '.lock')):
            data = self.load() if self.path.exists() else dict(schema_version=1, project_id=self.project,
                stage_id=self.stage, batch_id=self.batch, revisions=[], operations={}, completions={})
            prior = data['operations'].get(operation)
            if prior:
                if prior['signature'] != signature or prior['action'] != 'save':
                    raise ValueError('同一操作编号对应不同输入')
                if prior.get('done'):
                    return self.show(prior['revision'])
                revision = data['revisions'][prior['revision'] - 1]
            else:
                if any(not op.get('done') for op in data['operations'].values()):
                    raise ValueError('批次有未完成写入，请先使用原操作编号及原输入恢复')
                base = None
                if self.plans.path.exists():
                    plans = self.plans.load()
                    base = self.plans.resolve(plans, request.get('base_version', 'best'))
                day = request.get('date', today())
                date.fromisoformat(day)
                revision = dict(revision=len(data['revisions']) + 1, date=day, request=deepcopy(request),
                    base_version=base, status='saving', groups=preview['groups'])
                data['revisions'].append(revision)
                data['operations'][operation] = dict(action='save', signature=signature, revision=revision['revision'], done=False)
                self.write(data)  # intent is durable before any plan mutation
            for group in revision['groups']:
                if 'plan_version' in group:
                    continue
                if 'plan_operation' in group:
                    saved = self.plans.apply(group['plan_operation']['action'], group['plan_operation']['request'])
                    group.update(plan_id=saved['plan_id'], plan_version=saved['version'])
                    self.write(data)
                    continue
                content = deepcopy(request.get('plan_content', {}))
                from lab_plans import validate_content
                validate_content(content)
                material_map = {r['name']: r['original'] for r in planned_materials(group)}
                if len(material_map) != len(group['result']['materials']):
                    raise ValueError('原料名称须唯一，避免方案文本覆盖')
                content['materials'] = material_map
                # Retain exact inputs in plan identity even when displayed outputs round alike.
                labels = {'molar_mass': '摩尔质量', 'density': '密度', 'purity': '纯度', 'solids': '固含量',
                          'molarity': '摩尔浓度', 'mass_concentration': '质量浓度',
                          'functionality': '官能度', 'equivalent_weight': '当量质量'}
                for material in group['result']['materials']:
                    for prop, value in material.get('properties', {}).items():
                        content['materials'][material['name']] += f'；{labels[prop]} {value["value"]} {value["unit"]}（{value["source"]}）'
                inputs = [f'{n["label"]}：{n["value"]} {n["unit"]}（{n["source"]}）'
                          for n in group['result']['nodes'] if not n['op']]
                content.setdefault('conditions', {})['配方计算输入'] = '\n'.join(dict.fromkeys(inputs)) or '计算依据待补'
                content['pending'] = list(dict.fromkeys(content.get('pending', []) + group['result']['pending']))
                plan_request = dict(project_id=self.project, stage_id=self.stage,
                    operation_id=f'formulation:{self.batch}:{revision["revision"]}:{group["group_id"]}', date=revision['date'],
                    source=dict(description=request['description'], location=self.path.relative_to(self.root).as_posix()))
                if revision['base_version'] is None and not self.plans.path.exists():
                    plan_request.update(stage_name=request.get('stage_name', self.stage), content=content)
                    action = 'create'
                else:
                    # First save's other groups inherit its initial snapshot; updates use pinned base.
                    base = revision['base_version'] or 1
                    base_content = self.plans.show(base)['content']
                    patch = deepcopy(content)
                    if revision['base_version'] is not None and 'pending' not in request.get('plan_content', {}):
                        patch['pending'] = list(dict.fromkeys(base_content.get('pending', []) + content['pending']))
                    patch['materials'] = {k: None for k in base_content['materials'] if k not in material_map} | content['materials']
                    plan_request.update(base_version=base, patch=patch)
                    action = 'derive'
                group['plan_operation'] = dict(action=action, request=plan_request)
                self.write(data)
                saved = self.plans.apply(action, plan_request)
                group.update(plan_id=saved['plan_id'], plan_version=saved['version'])
                self.write(data)
            self.plans.export()
            revision['status'] = 'planned'
            data['operations'][operation]['done'] = True
            self.write(data)
            return self.show(revision['revision'])

    def complete(self, request):
        fields(request, ('operation_id', 'confirmation', 'revision', 'groups', 'defaults', 'reports', 'timezone'), '完成确认')
        operation = text(request.get('operation_id'), '稳定操作编号')
        text(request.get('confirmation'), '用户确认原话')
        signature = fingerprint(request)
        # Serialize sample-number allocation across batches as well as interruption recovery.
        with locked(self.root / 'work' / 'formulations-complete.lock'):
            with locked(self.folder / (self.batch + '.lock')):
                data = self.load()
                prior = data['operations'].get(operation)
                if prior:
                    if prior['signature'] != signature or prior['action'] != 'complete':
                        raise ValueError('同一操作编号对应不同输入')
                    if prior.get('done'):
                        return deepcopy(prior['result'])
                else:
                    if any(not op.get('done') for op in data['operations'].values()):
                        raise ValueError('批次有未完成写入，请先恢复原操作')
                    revision_number = request.get('revision', len(data['revisions']))
                    revision = self.show(revision_number)
                    if revision['status'] != 'planned':
                        raise ValueError('批次方案尚未保存完成')
                    groups = {g['group_id']: g for g in revision['groups']}
                    selected = request.get('groups', list(groups))
                    if not isinstance(selected, list) or not selected or len(set(selected)) != len(selected) or set(selected) - set(groups):
                        raise ValueError('完成组号须唯一且属于指定批次版本')
                    reports = request.get('reports', {})
                    if not isinstance(reports, dict) or set(reports) - set(selected):
                        raise ValueError('实际报告包含未选择的组')
                    defaults = request.get('defaults', {})
                    fields(defaults, REPORT_FIELDS, '实际报告')
                    store = Store(self.root)
                    store.refresh()
                    meta = store.all_meta()
                    # Reservations in interrupted operations of other batches must not be reused.
                    for path in self.root.glob('plans/*/*/batches/*.json'):
                        if path.name.endswith(('.export.json', '.qa.json')):
                            continue
                        other = read_json(path)
                        for item in other.get('operations', {}).values():
                            meta.extend(item.get('records', []))
                    records, already, report_inputs = [], [], {}
                    for gid in selected:
                        fields(reports.get(gid, {}), REPORT_FIELDS, '实际报告')
                        report = defaults | reports.get(gid, {})
                        key = f'{revision_number}:{gid}'
                        if key in data['completions']:
                            if report and fingerprint(report) != data['completions'][key].get('report_signature'):
                                raise ValueError('该组已入日报；更正请使用原record_id的日报更正流程')
                            already.append(data['completions'][key])
                            continue
                        record = self.prepare_record(groups[gid], report, revision_number,
                            request['confirmation'], today(request.get('timezone', '+08:00')), meta)
                        records.append(record)
                        report_inputs[gid] = fingerprint(report)
                        meta.append(record)
                    prior = dict(action='complete', signature=signature, done=False,
                                 revision=revision_number, records=records, already=already,
                                 report_inputs=report_inputs, written=[])
                    data['operations'][operation] = prior
                    self.write(data)
                records = prior['records']
                for record in records:
                    # Stable observed operation survives a plan-write/daily-write interruption.
                    patch = record.pop('_observed_patch', None)
                    if patch:
                        observed = self.plans.apply('derive', dict(project_id=self.project, stage_id=self.stage,
                            operation_id='observed:' + record['record_id'], date=record['date'],
                            base_version=int(record['plan_version']), patch=patch, mode='observed',
                            source=dict(record_id=record['record_id'], description=record['today'])))
                        record['plan_version'] = str(observed['version'])
                        self.write(data)
                for day in sorted({r['date'] for r in records}):
                    same_day = [r for r in records if r['date'] == day]
                    if day not in prior['written']:
                        Store(self.root).save(same_day)
                        prior['written'].append(day)
                        self.write(data)
                # Recover even if Word succeeded but index/tracker or reverse links were interrupted.
                store = Store(self.root)
                store.refresh()
                if records:
                    current = store.current_tracker_path()
                    from lab_records import tracker_data
                    current_month = tracker_data(current)['month'] if current else ''
                    store.write_tracker(max([r['date'][:7] for r in records] + [current_month]))
                if records:
                    self.plans.export()
                result = dict(batch_id=self.batch, revision=prior['revision'],
                    records=prior['already'] + [{k: r[k] for k in ('record_id', 'sample_id', 'date', 'state', 'batch_group', 'plan_version')} for r in records],
                    paths=[str(self.root / 'report' / day[:7] / f'日报_{day}.docx') for day in sorted({r['date'] for r in records})])
                for record in records:
                    link = deepcopy(next(r for r in result['records'] if r['record_id'] == record['record_id']))
                    link['report_signature'] = prior['report_inputs'][record['batch_group']]
                    data['completions'][f'{prior["revision"]}:{record["batch_group"]}'] = link
                prior.update(done=True, result=result)
                self.write(data)
                return result

    def prepare_record(self, group, report, revision, confirmation, default_date, meta):
        if 'as_planned' in report and not isinstance(report['as_planned'], bool):
            raise ValueError('as_planned须为布尔值')
        if any(not isinstance(value, str) for key, value in report.items()
               if key not in ('as_planned', 'materials', 'observed_patch')):
            raise ValueError('实际报告的文字字段须为字符串')
        day = report.get('date', default_date)
        date.fromisoformat(day)
        created = report.get('created_date', day)
        date.fromisoformat(created)
        if created > day:
            raise ValueError('创建日期不能晚于实验日期')
        kind = report.get('experiment_type', '合成')
        if kind not in ('合成', '后处理', '测试'):
            raise ValueError('无效实验类型')
        if not re.fullmatch(r'S\d{2,}', report.get('step', 'S01')):
            raise ValueError('步骤须为S01等格式')
        sample = report.get('sample_id')
        if sample:
            from extract_daily_docx import SAMPLE_RE
            if not SAMPLE_RE.fullmatch(sample) or not sample.startswith(self.project + '-'):
                raise ValueError('样品编号格式或项目不一致')
            known = [r for r in meta if r.get('sample_id') == sample]
            if known:
                created = known[0]['created_date']
            elif kind != '合成':
                raise ValueError('后处理或测试须关联已有样品')
        else:
            if kind != '合成':
                raise ValueError('后处理或测试须指定已有样品编号')
            prefix = f'{self.project}-{created.replace("-", "")}-'
            sequences = [int(r['sample_id'][len(prefix):]) for r in meta
                         if r.get('sample_id', '').startswith(prefix) and r['sample_id'][len(prefix):].isdigit()]
            sample = prefix + str(max(sequences, default=0) + 1)
        state = report.get('state')
        if state is None:
            content = self.plans.show(group['plan_version'])['content']
            state = '待测试' if content['tests'] else '已完成'
        if state not in STATES:
            raise ValueError('无效样品状态')
        rows = planned_materials(group)
        actual = report.get('materials', [])
        from lab_quantities import prepare_materials
        if any(row.get('quantity_kind') != 'actual' for row in actual):
            raise ValueError('实际报告的materials须为actual，计划表由批次自动保留')
        prepare_materials(actual)
        details = f'完成确认：{confirmation}\n实际称量：' + ('见实际用量表。' if actual else '未提供，待补。')
        details += '\n原料用量（计划）：' + '；'.join(r['name'] + ' ' + r['original'] for r in rows)
        if actual:
            details += '\n实际用量（用户报告）：' + '；'.join(r['name'] + ' ' + r['original'] for r in actual)
        details += '\n执行条件：' + ('用户确认按配方执行；计划计算值不是称量读数。' if report.get('as_planned') is True else '引用计划配方，实际条件与偏差待补。')
        details += '\n观测与测试数据：未提供部分待补。'
        if 'date' not in report:
            details += '\n实验日期：未单独指定，采用对话时区当天 ' + day + '。'
        if 'created_date' not in report and not report.get('sample_id'):
            details += '\n样品创建日期：未单独指定，暂按实验日期登记。'
        details += '\n' + report.get('details', '')
        record = dict(record_id=str(uuid.uuid4()), date=day, created_date=created,
            project=self.project, sample_id=sample, step=report.get('step', 'S01'),
            experiment_type=kind, state=state, today=report.get('today', '用户确认本组实验已完成。'),
            follow_up=report.get('follow_up', '补充实际称量、执行偏差及观测或测试结果。'), details=details.strip(),
            plan_stage=self.stage, plan_id=group['plan_id'], plan_version=str(group['plan_version']),
            batch_id=self.batch, batch_revision=str(revision), batch_group=group['group_id'], materials=rows + actual)
        for key in ('source_sample', 'source_step', 'context_version'):
            if key in report:
                record[key] = report[key]
        patch = deepcopy(report.get('observed_patch', {}))
        if not isinstance(patch, dict):
            raise ValueError('observed_patch须为条件补丁映射')
        if actual:
            patch.setdefault('materials', {}).update({f'实际报告 {r["operation"]} {r["name"]}': r['original'] for r in actual})
        if patch:
            from lab_plans import merge_content
            merge_content(self.plans.show(group['plan_version'])['content'], patch)
            record['_observed_patch'] = patch
        if bool(record.get('source_sample')) != bool(record.get('source_step')):
            raise ValueError('来源样品和来源步骤须一起提供')
        if '-B' in sample and not record.get('source_sample'):
            raise ValueError('分支样品须指定来源样品及步骤')
        if record.get('source_sample') and not any(r.get('sample_id') == record['source_sample'] and
                r.get('step') == record['source_step'] for r in meta):
            raise ValueError('来源样品步骤尚未登记')
        if (record.get('source_sample'), record.get('source_step')) == (sample, record['step']):
            raise ValueError('记录不能引用自己的当前样品步骤')
        for name in ('today', 'follow_up'):
            text(record[name], name)
        return record

    def export(self, revision, node, node_modules, output=None):
        snapshot = self.show(revision)
        if snapshot['status'] != 'planned':
            raise ValueError('批次未保存完成')
        output = Path(output) if output else self.folder / f'{self.batch}_v{snapshot["revision"]:04d}.xlsx'
        if output.suffix.lower() != '.xlsx':
            raise ValueError('配方文件须使用.xlsx扩展名')
        if output.exists():
            raise ValueError('Excel已存在；为保留手动编辑，请指定新的--output路径')
        # Keep the exact export input for reproducibility; never read Excel as authoritative data.
        input_path = self.folder / f'{self.batch}_v{snapshot["revision"]:04d}.export.json'
        atomic_write(input_path, json_bytes(snapshot))
        env = dict(os.environ, LAB_RD_NODE_MODULES=str(Path(node_modules).resolve()))
        subprocess.run([str(node), '--experimental-loader', (PROGRAM_ROOT / 'scripts/node_loader.mjs').as_uri(),
                        str(PROGRAM_ROOT / 'scripts/build_formulation_workbook.mjs'), str(input_path), str(output)], env=env, check=True)
        return dict(path=str(output.resolve()), qa=str(output.with_suffix('.qa.json').resolve()))


def validate_record_batch(root, record):
    keys = ('batch_id', 'batch_revision', 'batch_group')
    if not any(record.get(k) for k in keys):
        return
    if not all(record.get(k) for k in keys) or not all(record.get(k) for k in ('plan_stage', 'plan_id', 'plan_version')):
        raise ValueError('批次引用须完整，并同时引用方案版本')
    batch = BatchStore(root, record['project'].split()[0], record['plan_stage'], record['batch_id'])
    snapshot = batch.show(int(record['batch_revision']))
    if not any(g['group_id'] == record['batch_group'] for g in snapshot['groups']):
        raise ValueError('批次实验组不存在')


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('preview', 'save'):
        sub.add_parser(command).add_argument('input', type=Path)
    for command in ('list', 'show', 'complete', 'export'):
        p = sub.add_parser(command)
        p.add_argument('--project', required=True)
        p.add_argument('--stage', required=command != 'list')
        if command != 'list':
            p.add_argument('--batch', required=True)
        if command in ('show', 'export'):
            p.add_argument('--revision', type=int)
        if command == 'complete':
            p.add_argument('input', type=Path)
        if command == 'export':
            p.add_argument('--node', required=True, type=Path)
            p.add_argument('--node-modules', required=True, type=Path)
            p.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = data_root(args.root)
    try:
        if args.command in ('preview', 'save'):
            request = read_json(args.input)
            store = BatchStore(root, request['project_id'], request['stage_id'], request['batch_id'])
            result = getattr(store, args.command)(request)
        elif args.command == 'list':
            project = identifier(args.project)
            stages = [root / 'plans' / project / identifier(args.stage)] if args.stage else (root / 'plans' / project).glob('*')
            result = []
            for stage in stages:
                for path in sorted((stage / 'batches').glob('*.json')):
                    if path.name.endswith(('.export.json', '.qa.json')):
                        continue
                    batch_data = read_json(path)
                    if batch_data.get('schema_version') != 1 or batch_data.get('batch_id') != path.stem:
                        raise ValueError('无效批次主文件：' + str(path))
                    result.append(dict(project_id=project, stage_id=stage.name, batch_id=path.stem,
                                       revision=len(batch_data['revisions'])))
        else:
            store = BatchStore(root, args.project, args.stage, args.batch)
            if args.command == 'show':
                result = store.show(args.revision)
            elif args.command == 'complete':
                result = store.complete(read_json(args.input))
            else:
                result = store.export(args.revision, args.node, args.node_modules, args.output)
        if args.command in ('save', 'complete'):
            from project_context import route_status
            result['route_check'] = route_status(root, store.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
