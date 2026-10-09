"""Version shared project references without rewriting historical report conclusions."""
from __future__ import annotations
from lab_config import data_root
import argparse
import hashlib
import json
from datetime import date, datetime
import os
from pathlib import Path
import re
import tempfile
import sys
import yaml

GENERATED = ('context_version', 'effective_date', 'updated_at', 'context_change')


def changes(old, new, prefix=''):
    result = []
    if isinstance(old, dict) and isinstance(new, dict):
        for key in dict.fromkeys([*old, *new]):
            if not prefix and key in GENERATED:
                continue
            field = prefix + key
            if key not in old or key not in new:
                result.append({'field': field, 'before': old.get(key), 'after': new.get(key)})
            else:
                result.extend(changes(old[key], new[key], field + '.'))
    elif old != new:
        result.append({'field': prefix.rstrip('.'), 'before': old, 'after': new})
    return result


def preview(root, candidate):
    data = yaml.safe_load(Path(candidate).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', str(data.get('project_id', ''))):
        raise ValueError('Invalid project_id')
    target = Path(root) / 'references' / (data['project_id'] + '.yaml')
    old = yaml.safe_load(target.read_text(encoding='utf-8-sig')) if target.exists() else {}
    digest = hashlib.sha256(json.dumps([old, data], ensure_ascii=False, sort_keys=True,
                                      default=str, allow_nan=False).encode()).hexdigest()
    old_sources = old.get('reference_sources', [])
    literature = any(s.get('source_type') == 'literature' and s not in old_sources
                     for s in data.get('reference_sources', []))
    return {'project_id': data['project_id'], 'review_digest': digest,
            'changes': changes(old, data), 'literature_confirmation_required': literature}


def route_status(root, project, acknowledge=False, question_id=None):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', project):
        raise ValueError('Invalid project_id')
    path = Path(root) / 'references' / (project + '.yaml')
    data = yaml.safe_load(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    route = data.get('technical_route', {})
    stages = route.get('stages', []) if isinstance(route, dict) else []
    required = ('id', 'name', 'purpose', 'method', 'variables', 'inputs', 'outputs', 'metrics', 'decision', 'next')
    def known(value):
        if isinstance(value, str):
            return bool(value.strip()) and not any(word in value for word in ('待补', '待建立', '待确认', '待确定'))
        if isinstance(value, dict):
            return bool(value) and all(known(v) for v in value.values())
        if isinstance(value, list):
            return bool(value) and all(known(v) for v in value)
        return value is not None
    complete = bool(stages) and all(isinstance(s, dict) and all(known(s.get(k)) for k in required) for s in stages)
    confirmed = complete and route.get('status') == 'confirmed'
    evidence = {k: data.get(k) for k in ('project_route', 'project_background', 'technical_route', 'targets')}
    signature = hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    communication = Path(root) / 'work' / 'project-context' / (project + '-route-question.json')
    asked = json.loads(communication.read_text(encoding='utf-8')) if communication.exists() else {}
    if acknowledge:
        if question_id != signature:
            raise ValueError('路线内容已变化，须重新检查问题摘要')
        communication.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=communication.parent, suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'question_id': signature, 'asked_at': datetime.now().astimezone().isoformat()}, stream)
            os.replace(name, communication)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    return {'project_id': project, 'status': 'confirmed' if confirmed else '路线待建立',
            'needs_communication': not confirmed and asked.get('question_id') != signature and not acknowledge,
            'question_id': signature, 'existing_route': data.get('project_route'),
            'questions': [] if confirmed else ['项目要解决什么问题、目标指标是什么？',
                '当前处于哪个阶段，计划采用哪些方法及关键变量？', '各阶段输入输出、验证指标和下一步判断是什么？']}


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.yaml')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            yaml.safe_dump(data, stream, allow_unicode=True, sort_keys=False)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def missing_keys(old, new, prefix=''):
    result = []
    if isinstance(old, dict) and isinstance(new, dict):
        for key, value in old.items():
            if key not in new:
                result.append(prefix + key)
            else:
                result.extend(missing_keys(value, new[key], prefix + key + '.'))
    return result


def update(root, candidate, effective_date, allow_remove=False, *, literature=False, review_digest=None, confirmation=None):
    date.fromisoformat(effective_date)
    review = preview(root, candidate)
    if literature or review['literature_confirmation_required']:
        if not isinstance(confirmation, str) or not confirmation.strip() or review_digest != review['review_digest']:
            raise ValueError('文献背景/路线变更须先 preview 展示差异，再提供用户确认原话和匹配的 review_digest')
    data = yaml.safe_load(Path(candidate).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', str(data.get('project_id', ''))):
        raise ValueError('Invalid project_id')
    for key in ('project_name', 'status', 'project_route', 'targets', 'chart_groups'):
        if key not in data:
            raise ValueError('Missing ' + key)
    for target in data['targets'].values():
        if target['type'] not in ('min', 'max', 'range', 'qualitative'):
            raise ValueError('Invalid target type')
        keys = {'min': ('value', 'unit'), 'max': ('value', 'unit'),
                'range': ('min', 'max', 'unit'), 'qualitative': ('requirement',)}[target['type']]
        if any(k not in target for k in keys):
            raise ValueError('Incomplete target; retain missing values explicitly as null/pending')
        if target['type'] == 'range' and isinstance(target['min'], (int, float)) and isinstance(target['max'], (int, float)) and target['min'] > target['max']:
            raise ValueError('Target minimum exceeds maximum')
    for source in data.get('reference_sources', []):
        if not all(source.get(k) for k in ('title', 'location', 'purpose')):
            raise ValueError('Reference requires title, location and purpose')
        if source.get('source_type') == 'literature' and source.get('status', 'available') == 'available' and not source.get('locator'):
            raise ValueError('已读取文献须保留页码、章节或表图位置；未读取来源标为 pending')
    target = Path(root) / 'references' / (data['project_id'] + '.yaml')
    version = 1
    if target.exists():
        old = yaml.safe_load(target.read_text(encoding='utf-8-sig'))
        old_version = int(old.get('context_version', 1))
        # Generated metadata may be omitted in a candidate; custom fields may not.
        missing = [k for k in missing_keys(old, data) if k.split('.')[0] not in GENERATED]
        if missing and not allow_remove:
            raise ValueError('Candidate removes existing fields: ' + ', '.join(missing))
        history = target.parent / 'history' / data['project_id'] / f'v{old_version:04d}.yaml'
        old_snapshot = dict(old, context_version=old_version)
        if history.exists():
            if yaml.safe_load(history.read_text(encoding='utf-8')) != old_snapshot:
                raise ValueError('Historical version already exists with different content')
        else:
            write_yaml(history, old_snapshot)
        version = old_version + 1
    data.update(context_version=version, effective_date=effective_date,
                updated_at=datetime.now().astimezone().isoformat(timespec='seconds'))
    data.setdefault('reference_sources', [])
    if literature or review['literature_confirmation_required']:
        data['context_change'] = {'origin': 'literature', 'review_digest': review_digest,
                                  'confirmation': confirmation, 'changes': review['changes']}
    write_yaml(target, data)
    return target


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=None)
    parser.add_argument('command', choices=['update', 'preview', 'route'])
    parser.add_argument('candidate', type=Path, nargs='?')
    parser.add_argument('--effective-date')
    parser.add_argument('--allow-remove', action='store_true')
    parser.add_argument('--literature', action='store_true')
    parser.add_argument('--review-digest')
    parser.add_argument('--confirmation')
    parser.add_argument('--project')
    parser.add_argument('--acknowledge', action='store_true')
    parser.add_argument('--question-id')
    args = parser.parse_args()
    args.root = data_root(args.root)
    if args.command == 'route':
        if not args.project:
            parser.error('route requires --project')
        print(json.dumps(route_status(args.root, args.project, args.acknowledge, args.question_id), ensure_ascii=False, indent=2))
    elif not args.candidate:
        parser.error('candidate is required')
    elif args.command == 'preview':
        print(json.dumps(preview(args.root, args.candidate), ensure_ascii=False, indent=2))
    else:
        if not args.effective_date:
            parser.error('update requires --effective-date')
        print(update(args.root, args.candidate, args.effective_date, args.allow_remove,
                     literature=args.literature, review_digest=args.review_digest, confirmation=args.confirmation))


if __name__ == '__main__':
    main()
