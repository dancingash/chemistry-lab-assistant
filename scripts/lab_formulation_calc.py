"""Deterministic, traceable formulation arithmetic. No chemical constants are built in."""
from copy import deepcopy
from decimal import Decimal, localcontext
from itertools import product

from lab_quantities import UNITS, PROPERTIES, number


class Missing(ValueError):
    pass


def fields(value, allowed, label):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError('未知或无效' + label + '字段')


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + '须为非空文本')
    return value


class Calculation:
    def __init__(self, recipe, source):
        fields(recipe, ('materials', 'calculations'), '配方')
        self.materials = {}
        for material in recipe.get('materials', []):
            fields(material, ('id', 'name', 'role', 'material_type', 'component', 'formula', 'properties'), '材料')
            mid = text(material.get('id'), '材料编号')
            if mid in self.materials:
                raise ValueError('重复材料编号：' + mid)
            text(material.get('name'), '材料名称')
            if any(m['name'] == material['name'] for m in self.materials.values()):
                raise ValueError('原料名称须唯一')
            if material.get('material_type', 'unknown') not in ('pure', 'solution', 'dispersion', 'mixture', 'unknown'):
                raise ValueError('无效材料类型')
            self.materials[mid] = deepcopy(material)
            for optional in ('role', 'component', 'formula'):
                if optional in material:
                    text(material[optional], optional)
            properties = material.get('properties', {})
            units = {**PROPERTIES, 'solids': {'fraction': '1', '%': '.01'},
                     'functionality': {'1': '1'}, 'equivalent_weight': {'g/eq': '1'}}
            fields(properties, units, '材料性质')
            for name, prop in properties.items():
                fields(prop, ('value', 'unit', 'source'), '性质参数')
                text(prop.get('source'), name + '来源')
                if prop.get('unit') not in units[name]:
                    raise ValueError(name + '单位不兼容')
                value = number(prop.get('value')) * Decimal(units[name][prop['unit']])
                if (value == 0 and name != 'solids') or (name in ('solids', 'purity') and value > 1):
                    raise ValueError('无效材料性质：' + name)
        if not self.materials:
            raise ValueError('至少提供一种材料')
        self.nodes, self.outputs, self.pending = [], {}, []
        self.source = source

    def node(self, label, value=None, unit='', source='', op=None, args=()):
        if op:
            values = [Decimal(self.nodes[i]['value']) for i in args]
            if op == 'sum':
                value = sum(values, Decimal(0))
            elif op == 'mul':
                value = values[0] * values[1]
            elif op == 'div':
                if values[1] == 0:
                    raise ValueError(label + '：分母不能为零')
                value = values[0] / values[1]
            elif op == 'sub':
                value = values[0] - values[1]
            if value < 0:
                raise ValueError(label + '：约束无法满足，计算量为负')
        else:
            value = number(str(value) if isinstance(value, Decimal) else value)
        self.nodes.append(dict(label=label, value=str(value), unit=unit, source=source,
                               op=op, args=list(args)))
        return len(self.nodes) - 1

    def scalar(self, label, value, unit='fraction', source=None):
        return self.node(label, value, unit, source or self.source)

    def parameter(self, label, item, units, canonical):
        fields(item, ('value', 'unit', 'source'), '参数')
        if item.get('unit') not in units:
            raise ValueError(label + '：单位不兼容')
        text(item.get('source'), label + '来源')
        original = self.node(label, item.get('value'), item['unit'], item['source'])
        factor = Decimal(units[item['unit']])
        if factor == 1:
            return original
        conversion = self.scalar('单位换算系数', factor, canonical + '/' + item['unit'], '单位定义')
        return self.node(label + '（统一单位）', unit=canonical, op='mul', args=(original, conversion))

    def quantity(self, label, item, kind=None):
        if kind is None:
            kind = next((k for k, units in UNITS.items() if item.get('unit') in units), None)
        if kind not in UNITS:
            raise ValueError(label + '：须为质量、体积或物质的量')
        return kind, self.parameter(label, item, UNITS[kind], {'mass': 'g', 'volume': 'mL', 'amount': 'mmol'}[kind])

    def fraction(self, label, item):
        node = self.parameter(label, item, {'fraction': '1', '%': '.01'}, 'fraction')
        if Decimal(self.nodes[node]['value']) > 1:
            raise ValueError(label + '不能超过100%')
        return node

    def property(self, mid, name):
        if mid not in self.materials:
            raise ValueError('未知材料：' + mid)
        material = self.materials[mid]
        prop = material.get('properties', {}).get(name)
        if prop is None:
            if name == 'purity' and material.get('material_type') == 'pure':
                return self.scalar(material['name'] + '名义纯度', 1, source='明确声明为纯物质，未报告纯度，按名义纯度1计算')
            raise Missing(material['name'] + '缺少 ' + name + ' 及来源')
        units = {**PROPERTIES, 'solids': {'fraction': '1', '%': '.01'},
                 'functionality': {'1': '1'}, 'equivalent_weight': {'g/eq': '1'}}
        if name not in units:
            raise ValueError('未知性质：' + name)
        node = self.parameter(material['name'] + ' ' + name, prop, units[name], next(iter(units[name])))
        value = Decimal(self.nodes[node]['value'])
        if name in ('purity', 'solids') and value > 1:
            raise ValueError(name + '不能超过100%')
        if value == 0 and name != 'solids':
            raise ValueError(name + '必须大于零')
        return node

    def arithmetic(self, label, op, a, b, unit):
        return self.node(label, op=op, args=(a, b), unit=unit)

    def assign(self, mid, kind, node, basis='material'):
        if mid not in self.materials:
            raise ValueError('未知材料：' + mid)
        if mid in self.outputs:
            raise ValueError('重复指定材料用量：' + mid + '；请合并约束而非覆盖')
        if kind == 'amount' and self.materials[mid].get('material_type') == 'solution':
            if not self.materials[mid].get('component'):
                raise Missing(self.materials[mid]['name'] + '溶液组分身份待补')
            basis = 'component'
        self.outputs[mid] = dict(kind=kind, node=node, basis=basis)

    def output_as(self, mid, kind):
        if mid not in self.outputs:
            raise Missing(self.materials[mid]['name'] + '前置用量待补')
        out = self.outputs[mid]
        if out['kind'] == kind:
            return out['node']
        if {out['kind'], kind} == {'mass', 'volume'}:
            density = self.property(mid, 'density')
            return self.arithmetic('按整体密度换算', 'mul' if kind == 'mass' else 'div', out['node'], density,
                                   'g' if kind == 'mass' else 'mL')
        raise Missing(self.materials[mid]['name'] + '用量与所需计量基准不兼容')

    def moles(self, mid):
        material = self.materials[mid]
        out = self.outputs[mid]
        if material.get('material_type') not in ('pure', 'solution'):
            raise Missing(material['name'] + '尚无明确摩尔计量基准')
        if material.get('material_type') == 'solution' and not material.get('component'):
            raise Missing(material['name'] + '溶液组分身份待补')
        if out['kind'] == 'amount':
            return out['node']
        if material.get('material_type') == 'solution':
            volume = self.output_as(mid, 'volume')
            return self.arithmetic('n=cV（指定溶质）', 'mul', volume, self.property(mid, 'molarity'), 'mmol')
        mass = self.output_as(mid, 'mass')
        effective = self.arithmetic('有效纯物质质量', 'mul', mass, self.property(mid, 'purity'), 'g')
        mol = self.arithmetic('n=m/M', 'div', effective, self.property(mid, 'molar_mass'), 'mol')
        return self.arithmetic('mol转mmol', 'mul', mol, self.scalar('mol转mmol', 1000, source='单位定义'), 'mmol')

    def from_moles(self, mid, amount):
        material = self.materials[mid]
        if Decimal(self.nodes[amount]['value']) == 0 and material.get('material_type') in ('pure', 'solution'):
            kind, unit = ('mass', 'g') if material['material_type'] == 'pure' else ('volume', 'mL')
            return kind, self.scalar('零添加对照', 0, unit)
        if material.get('material_type') == 'solution':
            if not material.get('component'):
                raise Missing(material['name'] + '溶液组分身份待补')
            return 'volume', self.arithmetic('V=n/c（指定溶质）', 'div', amount, self.property(mid, 'molarity'), 'mL')
        if material.get('material_type') != 'pure':
            raise Missing(material['name'] + '尚无明确摩尔计量基准')
        mass = self.arithmetic('m=nM', 'mul', amount, self.property(mid, 'molar_mass'), 'mg')
        mass = self.arithmetic('mg转g', 'div', mass, self.scalar('g转mg', 1000, source='单位定义'), 'g')
        return 'mass', self.arithmetic('纯度修正投料', 'div', mass, self.property(mid, 'purity'), 'g')

    def execute(self, calc):
        mode = calc.get('mode')
        schemas = {
            'fixed': ('material', 'quantity'), 'mass_ratio': ('total', 'ratios', 'basis', 'content_property'),
            'mass_fraction': ('total', 'fractions', 'basis', 'content_property'),
            'solids': ('total', 'fraction', 'ratios', 'solvent', 'total_basis'),
            'molar_ratio': ('reference', 'ratios'), 'equivalents': ('reference', 'ratios'),
            'dilution': ('material', 'stock', 'target', 'final_volume'),
            'scale': ('quantities', 'factor', 'target_total'), 'make_up': ('material', 'total', 'members'),
        }
        if mode not in schemas:
            raise ValueError('未知计算模式：' + str(mode))
        fields(calc, ('mode', *schemas[mode]), '计算')
        if mode == 'fixed':
            kind, node = self.quantity(calc['material'] + '指定用量', calc['quantity'])
            self.assign(calc['material'], kind, node)
        elif mode in ('mass_ratio', 'solids'):
            total_label = ('干物质总质量' if mode == 'solids' and calc.get('total_basis') == 'dry' else
                           '有效成分总质量' if mode == 'mass_ratio' and calc.get('basis') == 'component' else '配方总质量')
            _, total = self.quantity(total_label, calc['total'], 'mass')
            ratios = calc['ratios']
            if not ratios or set(ratios) - set(self.materials):
                raise ValueError('比例材料缺失或未知')
            weights = {mid: self.scalar(mid + '比例', value, '1') for mid, value in ratios.items()}
            denominator = self.node('比例合计', op='sum', args=tuple(weights.values()), unit='1')
            if Decimal(self.nodes[denominator]['value']) == 0:
                raise ValueError('比例不能全部为零')
            target = total
            if mode == 'solids':
                fraction = self.fraction('目标固含量', calc['fraction'])
                if calc.get('total_basis', 'wet') not in ('wet', 'dry'):
                    raise ValueError('total_basis须为wet或dry')
                if calc.get('total_basis') == 'dry':
                    target = total
                    total = self.arithmetic('由干物质量反算配方总质量', 'div', target, fraction, 'g')
                else:
                    target = self.arithmetic('目标干物质总量', 'mul', total, fraction, 'g')
            elif calc.get('basis', 'material') not in ('material', 'component'):
                raise ValueError('basis须为material或component')
            for mid, weight in weights.items():
                weighted = self.arithmetic(mid + '总质量乘比例', 'mul', target, weight, 'g')
                mass = self.arithmetic(mid + '分配质量', 'div', weighted, denominator, 'g')
                try:
                    if mode == 'solids':
                        mass = self.arithmetic('按原料固含量反算湿投料', 'div', mass, self.property(mid, 'solids'), 'g')
                    elif calc.get('basis') == 'component':
                        prop = calc.get('content_property')
                        if prop not in ('solids', 'purity'):
                            raise ValueError('有效成分基准须指定solids或purity')
                        mass = self.arithmetic('按有效成分比例反算整体投料', 'div', mass, self.property(mid, prop), 'g')
                    self.assign(mid, 'mass', mass)
                except Missing as exc:
                    self.pending.append(str(exc))
            if mode == 'solids':
                solvent = calc['solvent']
                if Decimal(self.nodes[self.property(solvent, 'solids')]['value']) != 0:
                    raise ValueError('补足溶剂须明确固含量为零；非零时不能按本模式补足')
                self.make_up(solvent, 'mass', total, list(ratios))
        elif mode == 'mass_fraction':
            _, total = self.quantity('配方总质量', calc['total'], 'mass')
            if calc.get('basis', 'material') not in ('material', 'component'):
                raise ValueError('basis须为material或component')
            fractions = {mid: self.fraction(mid + '质量分数', value) for mid, value in calc['fractions'].items()}
            if sum(Decimal(self.nodes[n]['value']) for n in fractions.values()) > 1:
                raise ValueError('质量分数合计超过100%')
            for mid, fraction in fractions.items():
                try:
                    mass = self.arithmetic(mid + '目标质量', 'mul', total, fraction, 'g')
                    if calc.get('basis') == 'component':
                        prop = calc.get('content_property')
                        if prop not in ('solids', 'purity'):
                            raise ValueError('有效成分基准须指定 solids 或 purity')
                        mass = self.arithmetic('有效成分折算整体投料', 'div', mass, self.property(mid, prop), 'g')
                    self.assign(mid, 'mass', mass)
                except Missing as exc:
                    self.pending.append(str(exc))
            assigned = [self.outputs[mid]['node'] for mid in fractions if mid in self.outputs]
            if sum(Decimal(self.nodes[n]['value']) for n in assigned) > Decimal(self.nodes[total]['value']):
                raise ValueError('有效成分折算后的原料投料量超过配方总质量')
        elif mode in ('molar_ratio', 'equivalents'):
            ref, ratios = calc['reference'], calc['ratios']
            if ref not in self.outputs or ref not in ratios or number(ratios[ref]) == 0:
                raise ValueError('须先指定基准原料用量及非零基准比例')
            ref_ratio = self.scalar('基准比例', ratios[ref], '1')
            if mode == 'equivalents':
                amount = self.equivalents(ref)
            else:
                amount = self.moles(ref)
            for mid, value in ratios.items():
                if mid == ref:
                    continue
                try:
                    target = self.arithmetic('按比例分配', 'mul', amount,
                        self.arithmetic(mid + '相对比例', 'div', self.scalar(mid + '比例', value, '1'), ref_ratio, '1'), 'mmol')
                    kind, node = self.from_equivalents(mid, target) if mode == 'equivalents' else self.from_moles(mid, target)
                    self.assign(mid, kind, node)
                except Missing as exc:
                    self.pending.append(str(exc))
        elif mode == 'dilution':
            stock_unit = calc['stock'].get('unit')
            family = next((name for name in ('molarity', 'mass_concentration') if stock_unit in PROPERTIES[name]), None)
            if family is None or calc['target'].get('unit') not in PROPERTIES[family]:
                raise ValueError('稀释浓度须为同类摩尔浓度或质量浓度')
            material = self.materials[calc['material']]
            if material.get('material_type') != 'solution' or not material.get('component'):
                raise ValueError('稀释须指定溶液及溶质身份')
            stock = self.parameter('母液浓度', calc['stock'], PROPERTIES[family], next(iter(PROPERTIES[family])))
            target = self.parameter('目标浓度', calc['target'], PROPERTIES[family], next(iter(PROPERTIES[family])))
            if Decimal(self.nodes[target]['value']) > Decimal(self.nodes[stock]['value']):
                raise ValueError('稀释的目标浓度不得高于母液浓度')
            _, volume = self.quantity('定容后总体积', calc['final_volume'], 'volume')
            ratio = self.arithmetic('浓度比', 'div', target, stock, 'fraction')
            self.assign(calc['material'], 'volume', self.arithmetic('所需母液体积', 'mul', volume, ratio, 'mL'))
            self.pending.append('按最终体积定容；溶剂加入体积不能由体积可加性推定')
        elif mode == 'scale':
            if ('factor' in calc) == ('target_total' in calc):
                raise ValueError('缩放须指定factor或target_total其中一个')
            inputs = {mid: self.quantity(mid + '原配方用量', quantity) for mid, quantity in calc['quantities'].items()}
            if not inputs:
                raise ValueError('原配方用量不能为空')
            if 'factor' in calc:
                factor = self.parameter('缩放倍数', calc['factor'], {'1': '1'}, '1')
            else:
                _, target = self.quantity('缩放后配方总质量', calc['target_total'], 'mass')
                masses = []
                for mid, (kind, node) in inputs.items():
                    if kind == 'volume':
                        node = self.arithmetic('原料体积转整体质量', 'mul', node, self.property(mid, 'density'), 'g')
                    elif kind != 'mass':
                        raise ValueError('按总质量缩放须提供原料质量或具有密度依据的体积')
                    masses.append(node)
                total = self.node('原配方总质量', op='sum', args=tuple(masses), unit='g')
                factor = self.arithmetic('目标总量除原配方总量', 'div', target, total, '1')
            for mid, (kind, node) in inputs.items():
                self.assign(mid, kind, self.arithmetic(mid + '缩放用量', 'mul', node, factor, self.nodes[node]['unit']))
        elif mode == 'make_up':
            kind, total = self.quantity('补足后的总量', calc['total'])
            if kind not in ('mass', 'volume'):
                raise ValueError('补足总量须为质量或体积')
            if kind == 'volume':
                raise ValueError('不能假定混合体积可加；请使用dilution按最终体积定容')
            self.make_up(calc['material'], kind, total, calc['members'])

    def make_up(self, solvent, kind, total, members):
        if solvent in members or len(set(members)) != len(members):
            raise ValueError('补足材料不可包含在成员中，成员不可重复')
        used = self.node('已分配质量合计', op='sum', args=tuple(self.output_as(mid, kind) for mid in members), unit='g')
        self.assign(solvent, kind, self.arithmetic('溶剂补足质量', 'sub', total, used, 'g'))

    def equivalents(self, mid):
        material = self.materials[mid]
        if 'equivalent_weight' in material.get('properties', {}):
            mass = self.output_as(mid, 'mass')
            if material.get('material_type') == 'pure':
                mass = self.arithmetic('当量有效质量', 'mul', mass, self.property(mid, 'purity'), 'g')
            eq = self.arithmetic('当量=质量/当量质量', 'div', mass, self.property(mid, 'equivalent_weight'), 'eq')
            return self.arithmetic('eq转meq', 'mul', eq, self.scalar('eq转meq', 1000, source='单位定义'), 'meq')
        return self.arithmetic('当量=n×官能度', 'mul', self.moles(mid), self.property(mid, 'functionality'), 'meq')

    def from_equivalents(self, mid, amount):
        material = self.materials[mid]
        if Decimal(self.nodes[amount]['value']) == 0:
            return self.from_moles(mid, amount)
        if 'equivalent_weight' in material.get('properties', {}):
            mass = self.arithmetic('m=当量×当量质量', 'mul', amount, self.property(mid, 'equivalent_weight'), 'mg')
            mass = self.arithmetic('mg转g', 'div', mass, self.scalar('g转mg', 1000, source='单位定义'), 'g')
            if material.get('material_type') == 'pure':
                mass = self.arithmetic('纯度修正投料', 'div', mass, self.property(mid, 'purity'), 'g')
            return 'mass', mass
        amount = self.arithmetic('n=当量/官能度', 'div', amount, self.property(mid, 'functionality'), 'mmol')
        return self.from_moles(mid, amount)

    def run(self, recipe):
        if not isinstance(recipe.get('calculations'), list) or not recipe['calculations']:
            raise ValueError('calculations须为非空列表')
        for calc in recipe.get('calculations', []):
            try:
                self.execute(calc)
            except Missing as exc:
                self.pending.append(str(exc))
        for mid, material in self.materials.items():
            if mid not in self.outputs:
                self.pending.append(material['name'] + '投料量待补')
        return dict(nodes=self.nodes, outputs=self.outputs, pending=list(dict.fromkeys(self.pending)),
                    materials=list(self.materials.values()))


def calculate(recipe, source):
    with localcontext() as ctx:
        ctx.prec = 36
        return Calculation(recipe, source).run(recipe)


def expand(spec):
    """Only explicit zip/product expansion. Paths address existing recipe leaves."""
    variables = spec.get('variables', [])
    repeats = spec.get('repeats', 1)
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError('repeats须为正整数')
    mode = spec.get('combination')
    if len(variables) > 1 and mode not in ('zip', 'product'):
        raise ValueError('多变量须明确combination为zip或product')
    if mode not in (None, 'zip', 'product'):
        raise ValueError('combination须为zip或product')
    paths, names = set(), set()
    for variable in variables:
        fields(variable, ('name', 'path', 'values'), '梯度')
        text(variable.get('name'), '变量名')
        if variable['name'] in names:
            raise ValueError('变量名须唯一')
        names.add(variable['name'])
        path = variable.get('path')
        if (not isinstance(path, list) or not path or
                any(isinstance(k, bool) or not isinstance(k, (str, int)) or (isinstance(k, int) and k < 0) for k in path) or tuple(path) in paths):
            raise ValueError('梯度路径须唯一且非空')
        paths.add(tuple(path))
        if not isinstance(variable.get('values'), list) or not variable['values']:
            raise ValueError('梯度水平须为非空列表')
    levels = [v['values'] for v in variables]
    if mode == 'zip' and len({len(level) for level in levels}) > 1:
        raise ValueError('逐组对应的梯度长度必须相等')
    combinations = list(zip(*levels)) if mode == 'zip' and levels else list(product(*levels))
    groups = []
    for index, values in enumerate(combinations, 1):
        recipe = deepcopy(spec['recipe'])
        gradient = {}
        for variable, value in zip(variables, values):
            target = recipe
            try:
                for key in variable['path'][:-1]:
                    target = target[key]
                target[variable['path'][-1]]  # paths may not create new keys
                target[variable['path'][-1]] = deepcopy(value)
            except (KeyError, IndexError, TypeError) as exc:
                raise ValueError('梯度路径不存在') from exc
            gradient[variable['name']] = value
        result = calculate(recipe, spec['description'])
        for repeat in range(1, repeats + 1):
            groups.append(dict(group_id=f'G{index:03d}-R{repeat:02d}', gradient=gradient,
                               repeat=repeat, recipe=recipe, result=deepcopy(result)))
    return groups
