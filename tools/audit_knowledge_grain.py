# -*- coding: utf-8 -*-
"""审计：知识条目粒度与一致性（回答"拆分是否准确 / 会不会产生大量条目 / 能不能靠勾选"）

背景（v5.168）：用户提问 —— ①知识条目拆分是否准确？②不准确会基于文档产生大量条目，让用户勾选是否可行？③大量条目下页面能否承载？
本工具只回答第①问里**可客观验证**的部分，用 esprima 真 AST 读取数据结构（不做正则猜测）：
  A. 归一化后的**完全重复**（同一件事拆成两条）
  B. **包含关系**（"标题" vs "标题+限定条件"两种写法）
  C. 各层条目数与信息量（判断"一条 = 一个可独立回答的问题"是否成立）
  D. **岗位清单条目 → 知识条目匹配率**（匹配不上 → 界面显示"待补知识"）
  E. **赋能包是否由清单派生**（单一真源校验 · v5.197：比对两份内容只能发现"当前"差集，断言派生关系才能防"下一次"新增）
"""
import io
import re
import sys

import esprima

sys.stdout.reconfigure(encoding='utf-8')
PROTO = 'prototype.html'


def str_of(node):
    return node.value if node is not None and getattr(node, 'type', '') == 'Literal' else ''


def obj_props(node):
    """ObjectExpression → {key: node}（键可能是标识符，也可能是带引号的字符串字面量，如 {'客服专员':{...}}）"""
    out = {}
    if getattr(node, 'type', '') != 'ObjectExpression':
        return out
    for p in node.properties:
        if getattr(p, 'type', '') != 'Property':
            continue
        kt = getattr(p.key, 'type', '')
        if kt == 'Identifier':
            out[p.key.name] = p.value
        elif kt == 'Literal':
            out[str(p.key.value)] = p.value
    return out


def get_array_item_names(arr_node, fields=('name', 'n')):
    """ArrayExpression → [{field: value}]"""
    out = []
    if getattr(arr_node, 'type', '') != 'ArrayExpression':
        return out
    for el in arr_node.elements:
        if getattr(el, 'type', '') == 'ObjectExpression':
            pr = obj_props(el)
            rec = {}
            for f in fields:
                if f in pr:
                    rec[f] = str_of(pr[f])
            for extra in ('val', 'src', 'k', 'lv'):
                if extra in pr:
                    rec[extra] = str_of(pr[extra])
            if rec:
                out.append(rec)
    return out


def find_var(tree, name):
    for node, parent, field in walk(tree):
        if node.type == 'VariableDeclarator' and getattr(node.id, 'name', '') == name:
            return node.init
    return None


def walk(node, parent=None, field=None, out=None):
    if out is None:
        out = []
    if isinstance(node, list):
        for it in node:
            walk(it, parent, field, out)
        return out
    if node is None or not hasattr(node, 'type'):
        return out
    out.append((node, parent, field))
    for k, v in vars(node).items():
        if k in ('type', 'loc', 'range', 'raw', 'regex'):
            continue
        if isinstance(v, list) or (v is not None and hasattr(v, 'type')):
            walk(v, node, k, out)
    return out


def norm(s):
    s = re.sub(r'[（(][^）)]*[）)]', '', s or '')
    return re.sub(r'[·．\.\-\s/、,，:：]', '', s)


def main():
    js = max(re.findall(r'<script>(.*?)</script>', io.open(PROTO, encoding='utf-8').read(), re.S), key=len)
    tree = esprima.parseScript(js)

    # —— 知识分层 ——
    aud = obj_props(find_var(tree, 'AUDIT'))
    kn = obj_props(aud.get('knowledge')) if 'knowledge' in aud else {}
    levels = {}
    for k, v in kn.items():
        if re.match(r'^K\d$', k):
            levels[k] = get_array_item_names(v)
    allitems = [(k, it) for k in sorted(levels) for it in levels[k]]

    print('=== C. 各层条目数与信息量（判断拆分粒度）===')
    for k in sorted(levels):
        items = levels[k]
        if not items:
            continue
        avg = sum(len(x.get('val', '')) for x in items) / len(items)
        short = [x for x in items if len(x.get('val', '')) < 14]
        print('  %s：%2d 条 · val 平均 %4.1f 字 · 过短(<14字) %d 条' % (k, len(items), avg, len(short)))
    print('  合计 %d 条（演示态）' % len(allitems))

    print()
    print('=== A. 归一化后完全重复 ===')
    seen, dup = {}, 0
    for k, x in allitems:
        nm = x.get('name', '')
        if not nm:
            continue
        n2 = norm(nm)
        if n2 in seen:
            print('  ⚠ %s「%s」≡ %s「%s」' % (seen[n2][0], seen[n2][1], k, nm))
            dup += 1
        else:
            seen[n2] = (k, nm)
    print('  ✅ 无完全重复' if not dup else '  共 %d 组 → 同一件事被拆成两条，界面会重复出现' % dup)

    print()
    print('=== B. 包含关系（"标题" vs "标题+限定"两种写法）===')
    cont = 0
    for k1, a in allitems:
        na = norm(a.get('name', ''))
        if not na:
            continue
        for k2, b in allitems:
            if a is b or k1 != k2:
                continue
            nb = norm(b.get('name', ''))
            if nb and na != nb and na in nb:
                print('  ⚠ %s「%s」⊂ %s「%s」' % (k1, a.get('name'), k2, b.get('name')))
                cont += 1
                break
    print('  ✅ 无包含关系' if not cont else '  共 %d 条存在包含关系（建议归并，或明确为"条目 + 限定条件"）' % cont)

    # —— 清单 ——
    org = obj_props(find_var(tree, 'ONBOARD_REQUIRED'))
    docs = obj_props(find_var(tree, 'AUDIT'))
    docids = set()

    def _collect_docids(node):
        if getattr(node, 'type', '') != 'ArrayExpression':
            return
        for d in (node.elements or []):
            pr = obj_props(d)
            if 'id' in pr:
                docids.add(str_of(pr['id']))

    if 'docs' in docs:
        _collect_docids(docs['docs'])
    # v5.198 修：文档库的真源是**后置赋值** `AUDIT.docs = [...]`（AUDIT 字面量里没有 docs 字段）；
    # 此前只读字面量 → docids 恒为空 → **所有清单条目的文档 id 都被误判"悬空"**（审计喊狼来了，比不报更坏）。
    for node, parent, field in walk(tree):
        if getattr(node, 'type', '') != 'AssignmentExpression':
            continue
        left = getattr(node, 'left', None)
        if getattr(left, 'type', '') != 'MemberExpression':
            continue
        if getattr(getattr(left, 'object', None), 'name', '') == 'AUDIT' \
           and getattr(getattr(left, 'property', None), 'name', '') == 'docs':
            _collect_docids(node.right)
    entries = []      # v5.169 降级后：条目 = {t, doc, sec}
    for post, v in org.items():
        pr = obj_props(v)
        for kind in ('r', 'n'):
            if kind in pr:
                for it in get_array_item_names(pr[kind], ('t', 'doc', 'sec', 'mod')):
                    it['post'] = post
                    it['kind'] = kind
                    entries.append(it)
    listnames = [e.get('t', '') for e in entries]

    print()
    print('=== D. 岗位清单条目 → 文档锚点覆盖率（v5.169 降级后的校验对象）===')
    linked = [e for e in entries if e.get('doc')]
    missing = [e for e in entries if not e.get('doc')]
    anchored = [e for e in linked if (e.get('sec') or '').strip()]
    dangling = [e for e in linked if e['doc'] not in docids]
    print('  清单条目共 %d 条：已挂文档 %d · **待补文档 %d** · 其中带章节锚点 %d / %d'
          % (len(entries), len(linked), len(missing), len(anchored), len(linked)))
    for e in missing:
        print('    ⚠ 待补文档：%s（%s · %s）应来自 %s' % (e.get('t', ''), e.get('post', ''), e.get('kind', ''), e.get('sec', '') or '未标注'))
    if dangling:
        for e in dangling:
            print('    ❌ 指向不存在的文档 id：%s → %s' % (e.get('t', ''), e.get('doc', '')))
    else:
        print('  ✅ 所有已挂文档的 id 都能在文档库中找到（无悬空引用）')

    # —— 赋能包（v5.197：派生视图校验）——
    em_node = find_var(tree, 'ENABLE_MODULES')
    # 派生 = init 不是对象字面量，或只是空占位 `{}`；非空对象字面量 = 独立维护的第二套内容
    derived = (getattr(em_node, 'type', '') != 'ObjectExpression') or (len(getattr(em_node, 'properties', []) or []) == 0)
    plan = obj_props(find_var(tree, 'PACK_PLAN'))
    exps = {}
    en = find_var(tree, 'EXPERIENCES')
    if getattr(en, 'type', '') == 'ArrayExpression':
        for x in get_array_item_names(en, ('id', 'post', 'status')):
            if x.get('id'):
                exps[x['id']] = x

    print()
    print('=== E. 赋能包 = 清单的派生视图（单一真源校验）===')
    print('  ① ENABLE_MODULES 是否派生：%s（init = %s · 非空字面量字段 %d）'
          % ('✅ 是（占位赋值，内容运行时由清单 + 经验池生成）' if derived else '❌ 否 —— 它是独立维护的第二套内容（双重真源复发）',
             getattr(em_node, 'type', '?'), len(getattr(em_node, 'properties', []) or [])))
    bad = 0
    for post in plan:
        mods = []
        v = plan[post]
        if getattr(v, 'type', '') == 'ArrayExpression':
            for mod in (v.elements or []):
                pr = obj_props(mod)
                refs = []
                if getattr(pr.get('exp'), 'type', '') == 'ArrayExpression':
                    refs = [str_of(x) for x in (pr['exp'].elements or [])]
                mods.append((str_of(pr.get('id')), refs, str_of(pr.get('title'))))
        ids = [m[0] for m in mods]
        cfg = obj_props(org.get(post)) if post in org else {}
        es = []
        for kind in ('r', 'n'):
            if kind in cfg:
                for it in get_array_item_names(cfg[kind], ('t', 'doc', 'sec', 'mod')):
                    it['kind'] = kind
                    es.append(it)
        dangling = [e for e in es if (e.get('mod') or '') and e['mod'] not in ids]
        uncovered = [e for e in es if not e.get('mod')]
        print('  %s：模块 %d · 清单条目 %d（已编排 %d · 未覆盖 %d · 悬空 %d）'
              % (post, len(mods), len(es), len(es) - len(uncovered) - len(dangling), len(uncovered), len(dangling)))
        for e in dangling:
            print('    ❌ mod 指向不存在的模块：%s → %s（员工侧会静默丢失该条目）' % (e.get('t', ''), e.get('mod')))
            bad += 1
        for e in uncovered:
            print('    ⚠ 未覆盖（不进员工学习路径 · 主管侧应可见并可编排）：%s' % e.get('t', ''))
        for mid, refs, title in mods:
            src_n = len([e for e in es if e.get('mod') == mid]) + len(refs)
            if not src_n:
                print('    ❌ 模块「%s · %s」没有任何来源（清单条目 / 已确认经验）' % (mid, title))
                bad += 1
            for r in refs:
                x = exps.get(r)
                if not x:
                    print('    ❌ 模块 %s 引用的经验 id 不存在：%s' % (mid, r))
                    bad += 1
                elif x.get('status') != '已确认':
                    print('    ❌ 模块 %s 引用了未确认经验：%s（状态「%s」不得入包）' % (mid, r, x.get('status')))
                    bad += 1
    print('  ✅ 派生关系与出处全部成立（悬空 0 · 未确认经验 0 · 空模块 0）' if not bad
          else '  共 %d 处问题 —— 真源唯一被破坏，必须收口' % bad)
    return 0


if __name__ == '__main__':
    sys.exit(main())
