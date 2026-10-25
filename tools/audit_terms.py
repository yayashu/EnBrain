# -*- coding: utf-8 -*-
"""术语一致性体检（只读）——**一个东西一个名字**（依《方法论》§9.13）
做法：**只查"禁用变体"**（canonical 是唯一正名）——不做自动"一名多写"猜测，
      因为在同一文档里"三名并存"未必是错（如"落差"vs"落差识别"），
      而**变体一旦出现就一定是错** ✓（确定性判据，误报为 0）。
用法：python tools/audit_terms.py [文件...]
"""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
print('脚本开始 · 术语体检')

DOCS = sys.argv[1:] or ['docs/谋全局EnBrain-需求说明书（对外版）.md']

# (正名, [禁用变体...], 说明)
RULES = [
    ('事实底座', ['知识底座', '数据底座'], '真源 PRD 用「事实底座」'),
    ('六层知识', ['知识六层', '六层系统知识'], '真源 PRD 用「六层知识」'),
    ('可对账的硬节省', ['可对账的节省'], '文档既有写法为「可对账的硬节省」'),
    ('文档就绪度评估', ['就绪度诊断'], '真源与可研用「文档就绪度评估」'),
    ('报告四模式', ['四模式报告'], '术语表正名为「报告四模式」'),
    ('全量文档学习', ['全量学完'], '真源 PRD 用「全量文档学习」'),
    ('Enterprise Brain', ['Enterprise Optimization Brain'], '真源英文名为 Enterprise Brain'),
    ('重复建设归并 · 主数据治理', ['数据冗余与孤岛', '流程瓶颈作软三类'], '软三类口径以真源为准'),
    ('事实底座', ['事实层'], '注意：仅当"事实层"指代底座时才算错（架构分层名正当），故本行只报数、不判定'),
]

tot = 0
for doc in DOCS:
    t = io.open(doc, encoding='utf-8').read()
    L = t.split('\n')
    out = []
    for canon, bads, note in RULES:
        for b in bads:
            n = t.count(b)
            if not n:
                continue
            soft = (b == '事实层')
            out.append((canon, b, n, note, soft))
            if not soft:
                tot += n
    print('\n■ %s' % doc.split('/')[-1])
    if not out:
        print('   ✅ 未发现禁用变体')
    for canon, b, n, note, soft in out:
        print('   %s「%s」×%d → 正名「%s」｜%s' % ('ℹ 只报数：' if soft else '⚠ ', b, n, canon, note))
        if not soft:
            for i, l in enumerate(L):
                if b in l:
                    print('        L%-4d %s' % (i + 1, l.strip()[:96]))

print('\nSUMMARY 术语体检 禁用变体命中=%d 处' % tot)
