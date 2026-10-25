# -*- coding: utf-8 -*-
"""对外文本语感体检（只读）——工程语感 ✗ vs 专家语感 ✓
判据依《方法论》§9.19 附判据（v5.262/v5.263）：
  ① 做判断的读者 → 散文给判断（先倾向 · 再结构性理由）；做实现的 → 留清单与表。
  ② 量级 ≠ 阈值：量级（5–20 套 / 4–8 周）**留着**；要下沉的是 ≥ / ≤ / 精确百分比。
  ③ 「专家语感」≠ 加经验之谈：经验坐标只能用自有调研与行业常识；需私有样本的标「待实测」。
  ④ 空词（客观 / 全面 / 高效…）是从判断退化成形容词的信号。
用法：python tools/audit_voice.py [文件...]
"""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
print('脚本开始 · 语感体检')

DOCS = sys.argv[1:] or ['docs/谋全局EnBrain-需求说明书（对外版）.md']

# 反向信号（工程语感）
BAD = [('空词', r'客观|全面|高效|智能|强大|先进|领先|完善|便捷|优质|全覆盖|极致'),
       ('实现视角', r'字段|接口文档|表结构|数据库表|函数|\w+\(\)|JSON|API 级|颗粒度到'),
       ('精确阈值', r'[≥≤]\s*\d|\d+\.\d+\s*%|\d+\s*%'),
       ('治理腔', r'本文档|本文件|本报告|口径|真源|判定方式|下沉|指针|编号约定')]
# 正向信号（专家语感）
GOOD = [('判断', r'不是|而是|应当|宁可|恰好|注定|换一家|本质|换句话说|我们建议|不建议|先说'),
        ('结构性理由', r'谁按|按.{0,6}划分|物理限制|没有一方|不存在|无论谁|谁也'),
        ('量级', r'\d+[–~-]\d+\s*(套|场|周|天|份|页|人|%)|数十|数百|数千'),
        ('经验坐标', r'通常|典型|一般|行业|实践|惯例|常见|多数企业|公开信息|政策|调研'),
        ('取舍代价', r'代价|前提是|条件是|代价是|退路|否则|一旦')]

def klass(l):
    s = l.strip()
    if not s: return '空行'
    if s.startswith('#'): return '标题'
    if s.startswith('|') or s.startswith('> **失败模式') : return '表格'
    if re.match(r'^([-*+]|\d+\.)\s', s): return '清单'   # 标记后必须跟空格：`**加粗段**` 是正文，不是清单
    if s.startswith('>'): return '引用'
    return '正文'

SUMS = []
for doc in DOCS:
    t = io.open(doc, encoding='utf-8').read()
    L = t.split('\n')
    print('\n' + '=' * 100)
    print('■ %s（%d 字符 / %d 行）' % (doc.split('/')[-1], len(t), len(L)))
    print('=' * 100)

    # 按二级章分组
    chaps = []
    for i, l in enumerate(L):
        if re.match(r'^## ', l):
            chaps.append((i, l.strip('# ').strip()))
    chaps.append((len(L), '（尾）'))

    print('%-34s %5s %5s %5s %5s | %5s %5s %5s %5s %5s' % ('章', '空词', '实现', '阈值', '治理', '判断', '结构', '量级', '经验', '代价'))
    print('-' * 100)
    todo = []
    tot = {n: 0 for n, _ in BAD + GOOD}
    for k in range(len(chaps) - 1):
        s0, name = chaps[k]
        s1 = chaps[k + 1][0]
        blk = L[s0:s1]
        cnt = {n: 0 for n, _ in BAD + GOOD}
        for j, l in enumerate(blk):
            kind = klass(l)
            if kind in ('表格', '标题', '清单', '空行'):
                continue
            for n, p in BAD + GOOD:
                if n == '空词':
                    l = l.replace('智能分析平台', '')      # 项目名，不是空词
                if n == '精确阈值' and re.search(r'可推算|假设|依据', l):
                    continue                              # 测算行：可研本该给可推算依据
                m = re.findall(p, l)
                if m:
                    cnt[n] += len(m)
                    if n in ('空词', '实现视角', '精确阈值'):
                        todo.append((s0 + j + 1, n, l.strip()[:78]))
        row = [cnt[n] for n, _ in BAD] + [cnt[n] for n, _ in GOOD]
        for n, c in cnt.items():
            tot[n] += c
        print('%-34s %5d %5d %5d %5d | %5d %5d %5d %5d %5d' % tuple([name[:32]] + row))

    # 立场核对清单（v5.272 · **只列出、不判定**）：凡"我加的话"——章首引子与代价 / 取舍句
    ABS = r'没有意义|只有一条|都发生在|一律|绝不|永远|一定|根本|只取决于|只应当'
    claims = []
    for k in range(len(chaps) - 1):
        for i in range(chaps[k][0] + 1, chaps[k + 1][0]):
            u = L[i].strip()
            if not u:
                continue
            if u.startswith('#'):
                break
            if u.startswith('**') or u.startswith('> **'):
                claims.append((i + 1, '引子', u))
            break
    ilines = set(c[0] for c in claims)
    for i, l in enumerate(L):
        u = l.strip()
        if u.startswith('#') or u.startswith('|') or u.startswith('- '):
            continue   # 排除标题 / 表格行 / 列表项（目录条目与模块卡字段会含"取舍"二字，属噪声）
        if not re.search(r'\*\*代价|代价是|\*\*取舍|换来了', u):
            continue   # 认这几种形态；仅含"取舍"二字（术语 / 目录 / 模块卡字段）不算
        if i + 1 in ilines:
            continue   # 已被列为引子的行（引子含"代价"时）不重复列
        claims.append((i + 1, '取舍', u))
    SUMS.append((doc.split('/')[-1],
                 sum(tot[n] for n, _ in BAD if n != '治理腔'),   # 治理腔（口径 / 真源…）单列，不计入缺陷
                 sum(tot[n] for n, _ in GOOD),
                 len([c for c in claims if c[1] == '引子']),
                 len([c for c in claims if c[1] == '取舍'])))
    print('\n--- 待改候选（正文段：空词 / 实现视角 / 精确阈值）%d 处 ---' % len(todo))
    for ln, kind, txt in todo[:28]:
        print('  L%-5d [%s] %s' % (ln, kind, txt))
    # 长段与破折号
    longs = [(i + 1, l.strip()) for i, l in enumerate(L)
             if klass(l) == '正文' and (len(l.strip()) > 320 or l.count('——') >= 4)]
    print('\n--- 长段 / 破折号堆叠（%d 处）---' % len(longs))
    for ln, txt in longs[:12]:
        print('  L%-5d %d 字符 · 破折号 %d · %s' % (ln, len(txt), txt.count('——'), txt[:60]))

    print('\n--- 立场核对清单（**我加的话：只列、不判**；⚠＝含绝对化措辞，自造商业逻辑的高频形态）共 %d 条 ---' % len(claims))
    print('    %-7s %-5s %-4s %s' % ('行', '类型', '标记', '内容（真源出处待标：___）'))
    for ln, kind, txt in claims:
        print('    L%-6d [%s] %s %s' % (ln, kind, '⚠' if re.search(ABS, txt) else '  ', txt[:92]))
    print('    ℹ 依 §9.15（v5.269）：**每句判断都要能指回真源哪一句**；答不上来＝自造概括 ✗；能用真源措辞就用真源的')

# 机读汇总（供 verify [10] 解析：**只报数字，不阻塞**）
print()
for nm, bad, good, ni, nj in SUMS:
    print('SUMMARY %s 反向=%d 正向=%d 引子=%d 取舍=%d' % (nm, bad, good, ni, nj))
