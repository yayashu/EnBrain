# -*- coding: utf-8 -*-
"""审计 A：未声明标识符（"点开就崩"的真凶）  /  审计 B：内联事件处理器指向的函数是否存在（"点了没反应"）

背景（v5.166）：岗位清单页 `renderKbOnboard()` 用了 `kbOnboardPost`，
全库只声明了 `onboardPost`（同一概念两个名字）—— **语法 ✅ 括号 ✅ 死代码审计 ✅ 全过，点开即 ReferenceError**。
此前的审计只查"函数定义了没人调用"（死代码），不查"用了却没声明"，也不查"按钮指向的函数不存在"，两个盲区都在这里补上。

方法：用 esprima（项目已有依赖，apply.py 同款）解析真 AST，按"绑定处 / 引用处"区分标识符，
      只报"被引用但全库无任何绑定处"的名字（避开字符串、注释、属性名，消除误报）。
"""
import io
import re
import sys

import esprima

sys.stdout.reconfigure(encoding='utf-8')
PROTO = 'prototype.html'

GLOBALS = set("""undefined null true false NaN Infinity this arguments window document globalThis
console Math JSON Date RegExp Error TypeError RangeError Promise Map Set WeakMap WeakSet Symbol BigInt
Array Object String Number Boolean Function Intl Proxy Reflect
parseInt parseFloat isNaN isFinite encodeURI encodeURIComponent decodeURIComponent escape unescape
setTimeout setInterval clearTimeout clearInterval queueMicrotask requestAnimationFrame cancelAnimationFrame
alert confirm prompt fetch Blob File FileReader FormData URL URLSearchParams XMLHttpRequest
localStorage sessionStorage navigator location history screen performance crypto structuredClone
event CustomEvent MouseEvent KeyboardEvent Event Node Element HTMLElement Image Audio
AbortController Headers Request Response IntersectionObserver ResizeObserver MutationObserver
getComputedStyle btoa atob FileList DataTransfer DOMParser TextEncoder TextDecoder
echarts describe fail it test expect requireJS define
__dirname __filename require module exports process global""".split())

BINDING_FIELDS = {'id', 'param', 'params', 'label', 'key', 'local', 'imported', 'exported'}


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
        if k in ('type', 'loc', 'range', 'raw', 'regex', 'comments', 'tokens'):
            continue
        if isinstance(v, list) or (v is not None and hasattr(v, 'type')):
            walk(v, node, k, out)
    return out


def analyse_script(js):
    tree = esprima.parseScript(js, {'tolerant': True})
    nodes = walk(tree)
    declared, refs = set(), []

    def bind_name(p):
        """把模式（Identifier / 解构）里的绑定名收集起来"""
        if p is None or not hasattr(p, 'type'):
            return
        t = p.type
        if t == 'Identifier':
            declared.add(p.name)
        elif t == 'ObjectPattern':
            for pr in p.properties:
                bind_name(getattr(pr, 'value', None) or getattr(pr, 'argument', None))
        elif t == 'ArrayPattern':
            for el in p.elements:
                bind_name(el)
        elif t == 'AssignmentPattern':
            bind_name(p.left)
        elif t == 'RestElement':
            bind_name(p.argument)

    for n, p, f in nodes:
        if n.type == 'FunctionDeclaration' or n.type == 'FunctionExpression' or n.type == 'ArrowFunctionExpression':
            if getattr(n, 'id', None):
                bind_name(n.id)
            for prm in getattr(n, 'params', []) or []:
                bind_name(prm)
        elif n.type == 'VariableDeclarator':
            bind_name(n.id)
        elif n.type == 'CatchClause':
            bind_name(getattr(n, 'param', None))
        elif n.type == 'ClassDeclaration' and getattr(n, 'id', None):
            bind_name(n.id)

    for n, p, f in nodes:
        if n.type != 'Identifier':
            continue
        # 绑定位置（声明处）不算引用
        if p is not None and p.type == 'FunctionDeclaration' and f == 'id':
            continue
        if p is not None and p.type in ('FunctionExpression', 'ArrowFunctionExpression') and f == 'id':
            continue
        if p is not None and p.type == 'VariableDeclarator' and f == 'id':
            continue
        if p is not None and p.type == 'FunctionDeclaration' and f == 'params':
            continue
        if p is not None and p.type in ('FunctionExpression', 'ArrowFunctionExpression') and f == 'params':
            continue
        if p is not None and p.type == 'CatchClause' and f == 'param':
            continue
        # 属性名 / 成员属性 / 标签 不算引用
        if p is not None and p.type == 'MemberExpression' and f == 'property' and not p.computed:
            continue
        if p is not None and p.type == 'Property' and f == 'key' and not getattr(p, 'computed', False):
            continue
        if p is not None and p.type in ('LabeledStatement', 'BreakStatement', 'ContinueStatement') and f == 'label':
            continue
        refs.append(n)

    suspects = {}
    for n in refs:
        nm = n.name
        if nm in declared or nm in GLOBALS:
            continue
        suspects.setdefault(nm, []).append(getattr(n, 'loc', None))

    return declared, refs, suspects


def main():
    src = io.open(PROTO, encoding='utf-8').read()
    blocks = re.findall(r'<script>(.*?)</script>', src, re.S)
    js = max(blocks, key=len)
    declared, refs, suspects = analyse_script(js)
    print('=== 审计 A：未声明标识符（AST · 作用域感知）===')
    print('绑定名字 %d 个 · 引用标识符 %d 个' % (len(declared), len(refs)))
    if not suspects:
        print('✅ 未发现"被引用但全库无任何绑定处"的标识符')
    else:
        print('❌ 嫌疑 %d 个 —— 进对应页面/点对应按钮即抛 ReferenceError：' % len(suspects))
        for nm in sorted(suspects):
            locs = suspects[nm]
            s = ', '.join('L%d' % l.start.line for l in locs[:6] if l) or '（无位置）'
            print('   %-24s 引用 %d 处：%s' % (nm, len(locs), s))

    print()
    print('=== 审计 B：内联事件处理器指向的函数是否存在 ===')
    handlers = set(re.findall(r'on(?:click|change|input|keyup|keydown|submit)\s*=\s*["\']([^"\']+)["\']', src))
    called = set()
    for h in handlers:
        for m in re.finditer(r'([A-Za-z_$][\w$]*)\s*\(', h):
            called.add(m.group(1))
    METHOD_HANDLERS = set('getElementById querySelector querySelectorAll print stopPropagation preventDefault focus blur'.split())
    KEYWORD_HANDLERS = set('if else for while switch return typeof new delete void'.split())
    missing = sorted(c for c in called
                     if c not in GLOBALS and c not in METHOD_HANDLERS and c not in KEYWORD_HANDLERS
                     and not re.search(r'function\s+' + re.escape(c) + r'\s*\(', js)
                     and not re.search(r'(?:const|let|var)\s+' + re.escape(c) + r'\b', js))
    print('内联处理器 %d 个 · 其中调用的函数 %d 个' % (len(handlers), len(called)))
    if missing:
        print('❌ 指向了不存在的函数 %d 个（按钮点了没反应）：' % len(missing))
        for c in missing:
            print('   %s' % c)
    else:
        print('✅ 全部内联处理器指向的函数都存在')
    return 1 if (suspects or missing) else 0


if __name__ == '__main__':
    main()
