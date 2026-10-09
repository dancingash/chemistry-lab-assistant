"""Traceable material quantities; no chemical constants or inferred compositions."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json

UNITS = {
    'mass': {'g': '1', 'mg': '.001', 'kg': '1000', 'ug': '.000001', 'μg': '.000001', 'µg': '.000001'},
    'volume': {'mL': '1', 'ml': '1', 'L': '1000', 'uL': '.001', 'μL': '.001', 'µL': '.001'},
    'amount': {'mmol': '1', 'mol': '1000', 'umol': '.001', 'μmol': '.001', 'µmol': '.001'},
}
PROPERTIES = {'molar_mass': {'g/mol': '1'}, 'density': {'g/mL': '1', 'g/ml': '1', 'g/L': '.001'},
              'purity': {'fraction': '1', '%': '.01'},
              'molarity': {'mol/L': '1', 'mmol/mL': '1', 'mmol/L': '.001'},
              'mass_concentration': {'g/mL': '1', 'g/L': '.001', 'mg/mL': '.001'}}
DISPLAY = {'mass': 'g', 'volume': 'mL', 'amount': 'mmol'}
KINDS = {'pure', 'solution', 'dispersion', 'mixture', 'unknown'}
LABELS = {'material': '整体', 'component': '指定组分'}


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError('用量须为有限非负数，原始精度可用字符串保留')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('用量不是数值') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('用量须为有限非负数')
    return result


def format_number(value):
    return format(value, '.8g')


def quantities_hash(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def prepare_materials(rows):
    if not isinstance(rows, list):
        raise ValueError('materials 须为逐项用药列表')
    result = []
    for row in rows:
        if not isinstance(row, dict) or set(row) - {'operation', 'name', 'formula', 'role', 'material_type',
                'quantity_kind', 'original', 'measurements', 'properties', 'component', 'sample_id',
                'sample_step', 'source_record_id', 'note'}:
            raise ValueError('未知用药字段；计算结果由工具生成，不作为原始输入')
        for key in ('operation', 'name', 'role', 'original'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError('用药缺少 ' + key)
        for key in ('formula', 'component', 'sample_id', 'sample_step', 'source_record_id', 'note'):
            if key in row and not isinstance(row[key], str):
                raise ValueError(key + ' 须为文本')
        if row.get('quantity_kind') not in ('actual', 'planned') or row.get('material_type') not in KINDS:
            raise ValueError('区分 actual/planned 和 pure/solution/dispersion/mixture/unknown')
        item = deepcopy(row)
        readings = item.setdefault('measurements', [])
        if not isinstance(readings, list):
            raise ValueError('measurements 须为列表')
        canonical = {}
        chains = {}
        for reading in readings:
            if not isinstance(reading, dict) or set(reading) - {'kind', 'value', 'unit', 'basis', 'source'}:
                raise ValueError('未知测量字段')
            kind, unit = reading.get('kind'), reading.get('unit')
            if kind not in UNITS or unit not in UNITS[kind]:
                raise ValueError('量纲与单位不兼容：' + str(kind) + '/' + str(unit))
            basis = reading.get('basis', 'material')
            if basis not in LABELS or not isinstance(reading.get('source'), str) or not reading['source'].strip():
                raise ValueError('测量须注明整体/组分计量基准和来源')
            key = (kind, basis)
            value = number(reading.get('value')) * Decimal(UNITS[kind][unit])
            if key in canonical and canonical[key] != value:
                raise ValueError('同一用药的同一计量基准存在不同原始数值')
            canonical[key] = value
            chains[key] = [f"原始 {reading['value']} {unit}；{reading['source']}"]
        props = item.setdefault('properties', {})
        if not isinstance(props, dict) or set(props) - set(PROPERTIES):
            raise ValueError('未知换算性质')
        constants = {}
        for key, prop in props.items():
            if (not isinstance(prop, dict) or set(prop) - {'value', 'unit', 'source'}
                    or not isinstance(prop.get('source'), str) or not prop['source'].strip()):
                raise ValueError('换算依据须有 value、unit、source')
            if prop.get('unit') not in PROPERTIES[key]:
                raise ValueError('换算性质单位不兼容：' + key)
            value = number(prop.get('value')) * Decimal(PROPERTIES[key][prop['unit']])
            if value <= 0 or (key == 'purity' and value > 1):
                raise ValueError('性质须大于零；纯度不得超过 100%')
            constants[key] = value
        item['calculated'], item['pending'], item['conflicts'] = [], [], []
        original_keys = set(canonical)
        edges = []
        def edge(a, b, factor, property_names, formula):
            evidence = [f"{k}={props[k]['value']} {props[k]['unit']}；{props[k]['source']}" for k in property_names]
            edges.extend([(a, b, factor, evidence + [formula]), (b, a, 1 / factor, evidence + ['反向：' + formula])])
        if 'density' in constants:
            edge(('volume', 'material'), ('mass', 'material'), constants['density'], ['density'], 'm=ρV')
        if item['material_type'] == 'pure' and 'molar_mass' in constants:
            purity = constants.get('purity', Decimal(1))
            evidence = ['molar_mass'] + (['purity'] if 'purity' in props else [])
            edge(('mass', 'material'), ('amount', 'material'), purity * 1000 / constants['molar_mass'],
                 evidence, 'n=mp/M；未给纯度时仅对明确声明的纯物质按 p=1 计算')
        component_known = bool(item.get('component'))
        if item['material_type'] in ('solution', 'dispersion'):
            if 'mass_concentration' in constants and component_known:
                edge(('volume', 'material'), ('mass', 'component'), constants['mass_concentration'],
                     ['mass_concentration'], 'm(组分)=质量浓度×整体体积')
            if item['material_type'] == 'solution' and component_known:
                if 'molarity' in constants:
                    edge(('volume', 'material'), ('amount', 'component'), constants['molarity'],
                         ['molarity'], 'n(组分)=cV')
                if 'molar_mass' in constants:
                    edge(('mass', 'component'), ('amount', 'component'), 1000 / constants['molar_mass'],
                         ['molar_mass'], 'n(组分)=m(组分)/M')
        for _ in range(6):
            changed = False
            for a, b, factor, evidence in edges:
                if a not in canonical:
                    continue
                value = canonical[a] * factor
                if b in canonical:
                    # Permit rounding to 0.5% when independent observations are supplied.
                    tolerance = max(abs(value), abs(canonical[b])) * Decimal('.005')
                    if abs(value - canonical[b]) > tolerance:
                        message = f'{b[0]}({LABELS[b[1]]})：原有 {format_number(canonical[b])}，换算 {format_number(value)} {DISPLAY[b[0]]}'
                        if message not in item['conflicts']:
                            item['conflicts'].append(message)
                else:
                    canonical[b] = value
                    chains[b] = chains[a] + evidence
                    changed = True
            if not changed:
                break
        if item['conflicts']:
            item['pending'].append('原始数值与换算依据冲突，保留原始值并待用户核对；不输出衍生结果')
        else:
            for key in canonical.keys() - original_keys:
                item['calculated'].append({'kind': key[0], 'basis': key[1], 'value': format_number(canonical[key]),
                                          'unit': DISPLAY[key[0]], 'source': list(dict.fromkeys(chains[key]))})
            item['calculated'].sort(key=lambda q: (q['basis'], q['kind']))
        if not readings:
            item['pending'].append('原始记录尚无可解析的数值和单位')
        if item['material_type'] == 'pure' and 'molar_mass' not in constants:
            item['pending'].append('摩尔质量及来源待补，无法换算质量与摩尔量')
        if ('volume', 'material') not in canonical and 'density' not in constants:
            item['pending'].append('密度及适用条件待补，无法换算整体质量与体积')
        if item['material_type'] in ('solution', 'dispersion'):
            if not component_known:
                item['pending'].append('组分身份待补，整体质量不等于溶质或分散物质量')
            if 'molarity' not in constants and 'mass_concentration' not in constants:
                item['pending'].append('浓度及计量基准待补')
        if item['material_type'] in ('dispersion', 'mixture', 'unknown'):
            item['pending'].append('未定义摩尔计量基准，不推算材料摩尔量')
        result.append(item)
    return result


def raw_materials(rows):
    return [{k: deepcopy(v) for k, v in row.items() if k not in ('calculated', 'pending', 'conflicts')} for row in rows]


def table_matrix(rows):
    matrix = [['步骤／材料', '用途／状态', '原始用量', '计算值', '依据／待补']]
    for item in rows:
        calculated = '\n'.join(f"{q['value']} {q['unit']}（{LABELS[q['basis']]}，计算值）" for q in item['calculated']) or '—'
        evidence = list(dict.fromkeys(s for q in item['calculated'] for s in q['source']))
        evidence += [f"{k}={v['value']} {v['unit']}；{v['source']}" for k, v in item['properties'].items()]
        evidence += item['conflicts'] + item['pending']
        for reading in item['measurements']:
            evidence.append('原始来源：' + str(reading['source']))
        material = item['operation'] + '\n' + item['name']
        if item.get('formula'):
            material += ' ' + item['formula']
        if item.get('sample_id'):
            material += '\n' + item['sample_id'] + ' ' + item.get('sample_step', '')
        matrix.append([material, item['role'] + '\n' + ('实际' if item['quantity_kind'] == 'actual' else '计划'),
                       item['original'], calculated, '\n'.join(dict.fromkeys(evidence)) or '无新增换算'])
    return matrix
