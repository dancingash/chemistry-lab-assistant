"""Behavior checks isolated from real projects. --demo-root DIR creates reviewable synthetic Word."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from docx import Document
from extract_daily_docx import extract_docx
from lab_plans import PlanStore, PlanConflict, atomic_write, digest, validate_record_plan
from lab_records import Store


def initial():
    return {
        'purpose': '比较接枝条件对材料性能的影响。',
        'materials': {'树脂': '5.00 g（计划用量）', 'PEG': '10.00 g（计划用量）'},
        'operations': {'1 溶胀': '按既定溶剂体系溶胀，记录实际投料。',
                       '2 反应': '按下表设定温度和时间进行反应。',
                       '3 后处理': '洗涤并干燥，具体操作待补。'},
        'conditions': {'反应温度': '60 ℃', '反应时间': '4 h', '溶剂体积': '50 mL'},
        'tests': {'羟基含量': '方法待验证，记录 mmol/g', '外观': '记录颜色和形貌'},
        'pending': ['洗涤条件及干燥条件', '羟基含量方法确认'],
    }


def request(operation, **extra):
    return dict(project_id='DEMO', stage_id='peg', operation_id=operation, date='2026-09-20', **extra)


def daily(rid='run-1', version='1'):
    return dict(record_id=rid, date='2026-09-20', project='DEMO 示例项目',
                sample_id='DEMO-20260920-1', created_date='2026-09-20', step='S01',
                experiment_type='合成', state='合成中', today='已开始反应，实际反应时间调整为 6 h。',
                details='操作条件：实际反应时间 6 h。其余条件引用方案，实测投料待补。',
                follow_up='完成后处理并测试。', plan_stage='peg', plan_id='DEMO:peg', plan_version=version)


def create_plan(root):
    plan = PlanStore(root, 'DEMO', 'peg')
    plan.apply('create', request('initial', stage_name='PEG 接枝', content=initial(),
                               source={'description': '用于软件验证的示例条件'}))
    return plan


class PlansTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan = create_plan(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def best(self, number=1, op='choose-best'):
        return self.plan.apply('set-best', request(op, version=number, instruction=f'将第 {number} 版标为最优'))

    def derive(self, op, patch_content, base='best', **extras):
        return self.plan.apply('derive', request(op, base_version=base, patch=patch_content, **extras))

    def test_best_is_explicit_and_two_adjustments_pin_same_baseline(self):
        with self.assertRaisesRegex(PlanConflict, '尚未指定'):
            self.plan.show()
        self.best()
        self.derive('hotter', {'conditions': {'反应温度': '80 ℃'}})
        self.derive('longer', {'conditions': {'反应时间': '6 h'}})
        first = self.plan.show(2)
        second = self.plan.show(3)
        self.assertEqual(first['base_version'], 1)
        self.assertEqual(first['content']['conditions'], {'反应温度': '80 ℃', '反应时间': '4 h', '溶剂体积': '50 mL'})
        self.assertEqual(second['content']['conditions'], {'反应温度': '60 ℃', '反应时间': '6 h', '溶剂体积': '50 mL'})
        self.assertEqual(first['content']['materials'], initial()['materials'])
        self.assertEqual(self.plan.show()['version'], 1)
        self.assertFalse((self.root / 'report').exists())

    def test_retry_after_best_switch_returns_original_resolution(self):
        self.best()
        payload = request('hotter', base_version='best', patch={'conditions': {'反应温度': '80 ℃'}})
        first = self.plan.apply('derive', payload)
        self.best(2, 'choose-new-best')
        self.assertEqual(self.plan.apply('derive', payload), first)
        self.assertEqual(len(self.plan.load()['versions']), 2)
        changed = deepcopy(payload); changed['patch']['conditions']['反应温度'] = '90 ℃'
        with self.assertRaisesRegex(PlanConflict, '同一操作标识'):
            self.plan.apply('derive', changed)
        self.derive('now-longer', {'conditions': {'反应时间': '6 h'}})
        self.assertEqual(self.plan.show(3)['base_version'], 2)

    def test_no_change_and_identical_variant_reuse_snapshot(self):
        self.best()
        unchanged = self.derive('same', {'conditions': {'反应温度': '60 ℃'}})
        self.assertFalse(unchanged['created']); self.assertEqual(unchanged['version'], 1)
        self.derive('hotter', {'conditions': {'反应温度': '80 ℃'}})
        reused = self.derive('same-hotter', {'conditions': {'反应温度': '80 ℃'}})
        self.assertFalse(reused['created']); self.assertEqual(reused['version'], 2)
        self.assertEqual(len(self.plan.load()['versions']), 2)

    def test_operation_order_is_a_real_change_and_partial_order_is_rejected(self):
        self.best()
        order = ['1 溶胀', '3 后处理', '2 反应']
        # Synthetic permutation tests data fidelity, not a proposed laboratory sequence.
        result = self.derive('reorder', {}, operation_order=order)
        self.assertTrue(result['created'])
        self.assertEqual(list(self.plan.show(2)['content']['operations']), order)
        self.assertEqual(self.plan.show(2)['changes'][0]['field'], ['operation_order'])
        with self.assertRaisesRegex(PlanConflict, 'operation_order'):
            self.derive('bad-order', {}, operation_order=['1 溶胀'])

    def test_failed_atomic_plan_replace_preserves_previous_best_and_versions(self):
        self.best()
        original = self.plan.path.read_bytes()
        with patch('lab_plans.os.replace', side_effect=OSError('file busy')):
            with self.assertRaises(OSError):
                self.derive('recoverable', {'conditions': {'反应温度': '80 ℃'}})
        self.assertEqual(self.plan.path.read_bytes(), original)
        self.assertFalse((self.plan.folder / '.write.lock').exists())
        result = self.derive('recoverable', {'conditions': {'反应温度': '80 ℃'}})
        self.assertEqual(result['version'], 2)
        self.assertEqual(self.plan.show()['version'], 1)

    def test_stage_isolation_and_duplicate_stage_name(self):
        self.best()
        other = PlanStore(self.root, 'DEMO', 'precursor')
        other.apply('create', {
            **request('create-other', stage_name='前体制备', content=initial()), 'stage_id': 'precursor'})
        with self.assertRaisesRegex(PlanConflict, '尚未指定'):
            other.show()
        with self.assertRaisesRegex(PlanConflict, '已登记'):
            PlanStore(self.root, 'DEMO', 'peg2').apply('create', {
                **request('duplicate', stage_name='PEG 接枝', content=initial()), 'stage_id': 'peg2'})
        self.assertEqual(self.plan.show()['version'], 1)

    def test_invalid_patch_and_path_cannot_modify_store(self):
        self.best()
        before = self.plan.path.read_bytes()
        for changes in ({'temperature': '80 ℃'}, {'conditions': {'反应温度': 80}},
                        {'conditions': {'不存在的条件': None}}):
            with self.assertRaises(PlanConflict):
                self.derive('invalid', changes)
        self.assertEqual(self.plan.path.read_bytes(), before)
        for stage in ('../outside', 'CON', 'a/b', 'C:bad'):
            with self.assertRaises(PlanConflict):
                PlanStore(self.root, 'DEMO', stage)
        removed = self.derive('remove', {'conditions': {'溶剂体积': None}})
        self.assertNotIn('溶剂体积', self.plan.show(removed['version'])['content']['conditions'])
        self.assertIn('溶剂体积', self.plan.show(1)['content']['conditions'])

    def test_daily_roundtrip_rebuild_correction_and_unchanged_old_reference(self):
        self.best()
        result = self.derive('actual-time', {'conditions': {'反应时间': '6 h'}}, mode='observed',
                             source={'record_id': 'run-1', 'sample_id': 'DEMO-20260920-1'})
        store = Store(self.root)
        path = store.save([daily(version=str(result['version']))])
        parsed = extract_docx(path)['records'][0]
        self.assertEqual((parsed['plan_stage'], parsed['plan_id'], parsed['plan_version']), ('peg', 'DEMO:peg', '2'))
        before = path.read_bytes()
        self.best(2, 'choose-actual')
        self.derive('hotter', {'conditions': {'反应温度': '80 ℃'}})
        self.best(3, 'choose-third')
        self.assertEqual(path.read_bytes(), before)
        store.index_path.unlink()
        rebuilt = Store(self.root); rebuilt.refresh()
        self.assertEqual(rebuilt.query(sample='DEMO-20260920-1')[0]['plan_version'], '2')
        self.assertEqual(self.plan.show(2)['record_links'][0]['record_id'], 'run-1')
        corrected = daily(version='1')
        corrected['today'] = '反应按原定条件开始。'
        corrected['details'] = '操作条件：已确认反应时间仍为 4 h。'
        rebuilt.save([corrected])
        self.assertEqual(self.plan.show(2)['record_links'], [])
        self.assertEqual(len(self.plan.show(1)['record_links']), 1)

    def test_reverse_link_failure_recovers_without_new_version_or_record(self):
        self.best()
        store = Store(self.root)
        original = __import__('lab_plans').sync_record_links
        def fail_when_record_exists(root, records):
            if records:
                raise OSError('interrupted after daily save')
            return original(root, records)
        with patch('lab_plans.sync_record_links', side_effect=fail_when_record_exists):
            with self.assertRaises(OSError):
                store.save([daily()])
        recovered = Store(self.root); recovered.save([daily()])
        self.assertEqual(len(recovered.query(start='2026-09-20')), 1)
        self.assertEqual(len(self.plan.load()['versions']), 1)
        self.assertEqual(len(self.plan.show(1)['record_links']), 1)

    def test_reference_validation_and_observed_requires_daily_source(self):
        for replacement in ({'plan_version': 'best'}, {'plan_version': '99'}, {'plan_stage': ''},
                            {'project': 'OTHER 别的项目'}, {'plan_stage': 'other'}):
            record = daily(); record.update(replacement)
            with self.assertRaises(PlanConflict):
                validate_record_plan(self.root, record)
        with self.assertRaisesRegex(PlanConflict, 'record_id'):
            self.derive('invalid-actual', {}, base=1, mode='observed')

    def test_hand_edits_block_whole_export_and_review_preserves_bytes(self):
        self.best(); paths = self.plan.export()
        overview = Path(paths[0]); version = self.plan.folder / 'SOP.docx'
        original_overview = overview.read_bytes()
        doc = Document(version); doc.add_paragraph('用户手写补充：干燥方式待确认。'); doc.save(version)
        manual_bytes = version.read_bytes()
        with self.assertRaisesRegex(PlanConflict, '手动修改'):
            self.plan.export()
        self.assertEqual(overview.read_bytes(), original_overview)
        self.assertEqual(version.read_bytes(), manual_bytes)
        self.derive('reconcile', {'pending': [*initial()['pending'], '用户手写补充：干燥方式待确认。']})
        self.plan.export({'SOP.docx': digest(manual_bytes)})
        backup = self.plan.folder / 'manual_edits' / (digest(manual_bytes) + '.docx')
        self.assertEqual(backup.read_bytes(), manual_bytes)
        self.assertIn('用户手写补充：干燥方式待确认。', self.plan.show(2)['content']['pending'])

    def test_export_recovers_interrupted_replacement_and_final_manifest(self):
        self.best(); self.plan.export()
        self.derive('hotter', {'conditions': {'反应温度': '80 ℃'}})
        failed = False
        def fail_after_docx_replace(path, payload):
            nonlocal failed
            atomic_write(path, payload)
            if path.suffix == '.docx' and not failed:
                failed = True
                raise OSError('interrupted after replacing Word')
        with patch('lab_plans.atomic_write', side_effect=fail_after_docx_replace):
            with self.assertRaises(OSError):
                self.plan.export()
        paths = self.plan.export()
        for path in paths:
            relative = Path(path).relative_to(self.plan.folder).as_posix()
            self.assertEqual(self.plan.load()['exports'][relative]['sha256'], digest(Path(path).read_bytes()))


def demo(root):
    root = Path(root).resolve()
    if (root / 'plans').exists() or (root / 'report').exists():
        raise ValueError('Demo root must not already contain plans or reports')
    plan = create_plan(root)
    plan.apply('set-best', request('best', version=1, instruction='将第 1 版标为当前最优方案'))
    plan.apply('derive', request('temperature', base_version=1, patch={'conditions': {'反应温度': '80 ℃'}}))
    result = plan.apply('derive', request('time', base_version=1, patch={'conditions': {'反应时间': '6 h'}},
                                        mode='observed', source={'record_id': 'run-1', 'sample_id': 'DEMO-20260920-1'}))
    daily_path = Store(root).save([daily(version=str(result['version']))])
    paths = plan.export()
    print(json.dumps({'plans': paths, 'daily': str(daily_path)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) == 3 and sys.argv[1] == '--demo-root':
        demo(sys.argv[2])
    else:
        unittest.main()
