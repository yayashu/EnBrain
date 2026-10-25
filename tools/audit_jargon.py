# -*- coding: utf-8 -*-
"""审计：对外材料里"代号首现是否有解码"（依据方法论 §9.16，v5.201 起沉淀）

判据：**读者读到这个词 / 这个记号时，解释在哪？**
      解释若在后面几屏、甚至别的章，该处即须**自带一句大白话**（或用指针"见 §x"）。

做法：① 按章扫描目标文件，取各"代号族"的**首次出现**，检查该处（含前后 2 行）是否含解码关键词；
      ② 另检测**未登记的新代号**（形如 F16 / P40 / D5 的内部编号）——内部编号长得像"普通编号"，
        最容易漏网（实证 v5.202：可研附录 D 里裸写"B1 门槛"，B1 是内部交付准备件编号）。

用法：python tools/audit_jargon.py [目标文件] [--strict]
      默认目标 = docs/谋全局EnBrain-需求说明书（对外版）.md
说明：只列候选，不改文件；⚠ = 首现无解码，需补一句解释或改为指针。
      **默认恒返回 0（只列候选，判定权在人）**；**加 `--strict` 时"首现无解码"以退出码 1 报出**——
      供 `tools/verify.py` 作为卡口调用（依据方法论 §7.1：提醒会漂移，只有卡口可靠）。
      "未登记的新代号"**只报不阻塞**（它可能是普通编号，需人判定）。
"""
import io
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
TARGET = ARGS[0] if ARGS else 'docs/谋全局EnBrain-需求说明书（对外版）.md'

# 族名 · 代号模式 · 解码关键词（首现处或其上下 2 行应命中）
FAMILIES = [
    ('K 知识层', r'K[1-6](?![\d])', r'六层|六类|系统层|功能层|流程层|数据结构|集成层|规则层'),
    ('E 诊断步骤', r'E[1-6](?![\d])', r'六步|作业流程'),
    ('B 交付准备件', r'B[1-5](?![\d])', r'《|评估表|SOP|模板|门槛'),
    ('P 优先级', r'P[0-9](?![\d])', r'优先级'),
    ('中文代号', r'硬三类|三态|PQS|ALI|报告四模式', r'（[^）]{2,}|＝|闲置系统|成立并落地|专业'),
]
KNOWN_RE = re.compile('|'.join('(?:%s)' % p for _, p, _ in FAMILIES))
NEWCODE_RE = re.compile(r'(?<![A-Za-z\u4e00-\u9fff])([A-Z]{1,2}[0-9]{1,2}(?:\.[0-9]+)?)(?![\d])')
WHITELIST = re.compile(r'^(V\d|X\d|AI|IT|OA|CIO|ERP|MES|WMS|CRM|SRM|KPI|ROI|PDF|SaaS|MVP)$')


def main():
    strict = '--strict' in sys.argv
    t = io.open(TARGET, encoding='utf-8').read()
    L = t.split('\n')
    sec, cur = [], '（题头）'
    for l in L:
        m = re.match(r'^(#{2,3})\s+(.+)$', l)
        if m:
            cur = m.group(2).strip()
        sec.append(cur)

    print('审计代号首现解码：%s（%d 行）' % (TARGET, len(L)))
    print()
    bad = 0
    for name, pat, dec in FAMILIES:
        rx = re.compile(pat)

        def is_own_label(l, _p=pat):
            """v5.203 修误报：**标题行以该编号开头** = 这份材料自己的编号体系（如路演版的
            "## P1 · 开场"），它自带上下文、不是"未解码的代号"，不计入首现。"""
            return re.match(r'^#{1,6}\s+' + _p + r'\s*[·:：.\-）)]', l) is not None

        hits = [i for i, l in enumerate(L) if rx.search(l) and not is_own_label(l)]
        if not hits:
            print('  %-10s 未出现 ✅' % name)
            continue
        i0 = hits[0]
        win = ' '.join(L[max(0, i0 - 2):i0 + 3])
        ok = re.search(dec, win) is not None
        bad += 0 if ok else 1
        print('  %-10s 首现 L%-4d [%s] · 全文 %d 处 · %s'
              % (name, i0 + 1, sec[i0][:14], len(hits), '✅ 该处有解码' if ok else '⚠ **首现无解码**'))
        if not ok:
            print('             → %s' % L[i0].strip()[:120])

    print()
    print('  未登记的新代号（防"内部编号外泄"）：')
    seen = set()
    for i, l in enumerate(L):
        for m in NEWCODE_RE.finditer(l):
            tok = m.group(1)
            if WHITELIST.match(tok) or KNOWN_RE.match(tok) or tok in seen:
                continue
            seen.add(tok)
            print('    ⚠ %s（L%d [%s]）%s' % (tok, i + 1, sec[i][:14], l.strip()[:90]))
    if not seen:
        print('    ✅ 无')
    print()
    print('结论：%s' % ('✅ 全部代号首现自带解码' if not bad else '⚠ %d 个代号族"首现无解码"——请补一句解释或改为指针' % bad))
    if bad and strict:
        print('（--strict：以退出码 1 报出 → tools/verify.py 据此判定本轮**未通过**）')
    return 1 if (bad and strict) else 0


if __name__ == '__main__':
    sys.exit(main())
