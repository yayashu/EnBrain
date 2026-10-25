# -*- coding: utf-8 -*-
"""改动后验证：本轮备份存在性 + JS 语法/括号配平 + 残留关键词。

用法：
    python tools/verify.py --topic <主题>
    python tools/verify.py --topic <主题> --residue "领导看板,沉默部门"

为什么要做"备份存在性检查"：可验证的规则才会被执行。
把"本轮是否有 pre- 备份"纳入验证清单后，遗漏从"不可见"变为"可发现"。
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_tool(name):
    """工具定位：公开工具在 tools/，依赖内部材料的工具在 internal/tools/（2026-10-25 分仓）。"""
    for d in ('tools', os.path.join('internal', 'tools')):
        fp = os.path.join(ROOT, d, name)
        if os.path.exists(fp):
            return fp
    return None

def find(topic):
    """本轮备份查找（原由 preflight 提供；2026-10-25 分仓后自带，避免依赖内部工具）。"""
    import glob
    return sorted(glob.glob(os.path.join(ROOT, 'backups', 'pre-%s-*' % topic)))


def main(argv):
    topic = None
    residue = None
    i = 1
    while i < len(argv):
        if argv[i] == '--topic' and i + 1 < len(argv):
            topic = argv[i + 1]; i += 2
        elif argv[i] == '--residue' and i + 1 < len(argv):
            residue = argv[i + 1]; i += 2
        else:
            i += 1

    fails = []

    # ① 备份存在性（本轮）
    if topic:
        hits = find(topic)
        print('[1] 本轮备份（pre-%s-*）：%d 个 %s' % (topic, len(hits), '✅' if hits else '❌ 缺失'))
        if hits:
            print('    →', os.path.basename(hits[-1]))
        else:
            fails.append('本轮无 pre 备份')
    else:
        print('[1] 未指定 --topic，跳过备份检查')

    # ② JS 语法 + 括号配平
    p = os.path.join(ROOT, 'product-demo.html')
    if os.path.exists(p):
        src = open(p, encoding='utf-8').read()
        blocks = re.findall(r'<script>(.*?)</script>', src, re.S)
        js = max(blocks, key=len) if blocks else ''
        print('[2] product-demo.html：script 块 %d 个，主块 %d 字符' % (len(blocks), len(js)))
        print('    括号配平：braces %d · parens %d · brackets %d' % (
            js.count('{') - js.count('}'), js.count('(') - js.count(')'), js.count('[') - js.count(']')))
        try:
            import esprima
            esprima.parseScript(js)
            print('    JS 语法：✅ 通过（esprima 解析）')
        except ImportError:
            print('    JS 语法：⚠️ 跳过（未安装 esprima，可 pip install esprima）')
        except Exception as e:
            print('    JS 语法：❌ 失败 → %s' % str(e)[:120])
            fails.append('JS 语法错误')

    # ③ 未声明标识符（"点开就崩"）+ 内联事件处理器指向不存在的函数（"点了没反应"）
    #    背景 v5.166：岗位清单页用了 kbOnboardPost（8 处引用 · 0 处声明），语法/括号/死代码审计全过，点开即 ReferenceError。
    import subprocess
    tool = find_tool('audit_undeclared.py')
    if tool:
        r = subprocess.run([sys.executable, tool], capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        out = r.stdout or ''
        bad = [l.strip() for l in out.split('\n') if l.strip().startswith('❌')]
        print('[3] 未声明标识符 / 内联处理器：%s' % ('✅ 无嫌疑' if r.returncode == 0 else '❌ 有嫌疑'))
        for b in bad:
            print('    ' + b)
        if r.returncode != 0:
            fails.append('未声明标识符 / 内联处理器指向缺失函数（进页面即崩或点击没反应）')
    else:
        print('[3] 未声明标识符审计：⚠️ 跳过（缺 tools/audit_undeclared.py）')

    # ④ HTML 标签配平（模板字符串里的 HTML 结构 —— JS 括号配平查不出它）
    #    背景 v5.168：替换清单区时误删一个 <div> 开标签，JS 语法/括号全过，页面结构却坏了。
    if os.path.exists(p):
        src2 = open(p, encoding='utf-8').read()
        od, cd = src2.count('<div'), src2.count('</div>')
        print('[4] HTML 标签配平：<div> %d · </div> %d %s' % (od, cd, '✅' if od == cd else '❌ 差 %d' % (od - cd)))
        if od != cd:
            fails.append('HTML 标签不配平（<div> 与 </div> 数量不等）')
        lines2 = src2.split('\n')
        # 边界必须用"下一个 function 起始"：用"第一个独立 }"会在含嵌套块的长函数里提前截断（假阴性）
        starts2 = [(k2, mm2.group(1)) for k2, l2 in enumerate(lines2)
                   for mm2 in [re.match(r'\s*function (\w+)\s*\(', l2)] if mm2]
        for idx2, (k2, fn2) in enumerate(starts2):
            e2 = starts2[idx2 + 1][0] if idx2 + 1 < len(starts2) else len(lines2)
            body2 = '\n'.join(lines2[k2:e2])
            if body2.count('<div') != body2.count('</div>'):
                print('    ⚠ %s（L%d）：<div> %d / </div> %d' % (fn2, k2 + 1, body2.count('<div'), body2.count('</div>')))
                fails.append('函数 %s 标签不配平' % fn2)

    # ⑥ 对外材料"代号首现是否自带解码"（依据方法论 §9.16；v5.206 挂入卡口）
    #    背景：可研 §1.2 曾写「文档 → K1-K6 六层可溯源知识 → 层间落差识别（K2×K3 / K5×K3）→ 两类结论」——
    #    解释它的表在 82 / 95 行之后，读者在第一屏撞上未解码的代号（v5.201 沉淀判据 · v5.202 工具化）。
    tg = find_tool('audit_jargon.py')
    if tg:
        MATS = ['docs/谋全局EnBrain-路演版.md',
                'docs/谋全局EnBrain-需求说明书（对外版）.md',
                'internal/谋全局EnBrain-可行性研究报告.md',
                'internal/谋全局EnBrain-GoToMarket策略.md',
                'internal/谋全局EnBrain-VC可行性分析.md']   # 2026-10-25：内部材料移入 internal/，缺失即跳过
        print('[6] 对外材料代号首现解码：')
        for m in MATS:
            fp = os.path.join(ROOT, m)
            if not os.path.exists(fp):
                print('    ⚠️ 跳过（缺 %s）' % os.path.basename(m))
                continue
            rr = subprocess.run([sys.executable, tg, '--strict', fp], capture_output=True, text=True,
                                encoding='utf-8', errors='replace')
            tail = [l.strip() for l in (rr.stdout or '').split('\n') if l.strip()]
            print('    %-42s %s' % (os.path.basename(m), (tail[-1] if tail else '?')))
            if rr.returncode != 0:
                fails.append('%s：代号首现无解码' % os.path.basename(m))
    else:
        print('[6] 代号首现解码审计：⚠️ 跳过（缺 tools/audit_jargon.py）')

    # ⑦ 分册《功能规格》自检（v5.235：§5 外迁后，12.9 万字符的规格正文必须仍在审计之内）
    ts = find_tool('audit_spec.py')
    if ts:
        rr = subprocess.run([sys.executable, ts], capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
        tail = [l.strip() for l in (rr.stdout or '').split('\n') if l.strip()]
        print('[7] 分册《功能规格》自检：%s' % (tail[-1] if tail else '?'))
        if rr.returncode != 0:
            fails.append('分册自检未通过（见 audit_spec 输出）')
    else:
        print('[7] 分册自检：⚠️ 跳过（缺 tools/audit_spec.py）')

    # ⑧ 结构体检（v5.240：章号 / 章体量 / 目录覆盖 / 依赖层级顺序 / 议题分散 / 实现痕迹）
    ts2 = find_tool('audit_structure.py')
    if ts2:
        rr2 = subprocess.run([sys.executable, ts2], capture_output=True, text=True,
                             encoding='utf-8', errors='replace')
        tail2 = [l.strip() for l in (rr2.stdout or '').split('\n') if l.strip()]
        print('[8] 结构体检：%s' % (tail2[-1] if tail2 else '?'))
        if rr2.returncode != 0:
            fails.append('结构体检未通过（见 audit_structure 输出）')
    else:
        print('[8] 结构体检：⚠️ 跳过（缺 tools/audit_structure.py）')

    # ⑨ 内部一致性（v5.240：此前该审计只在人工运行时跑，未进轮次卡口）
    ts3 = find_tool('audit_consistency.py')
    if ts3:
        rr3 = subprocess.run([sys.executable, ts3], capture_output=True, text=True,
                             encoding='utf-8', errors='replace')
        # 取"最后一条有内容的行"——过滤纯分隔线（否则会把 `====` 当成结论打印）
        tail3 = [l.strip() for l in (rr3.stdout or '').split('\n')
                 if l.strip() and set(l.strip()) != {'='}]
        print('[9] 内部一致性：%s' % (tail3[-1] if tail3 else '?'))
        if rr3.returncode != 0:
            fails.append('内部一致性审计未通过（见 audit_consistency 输出）')
    else:
        print('[9] 内部一致性：⚠️ 跳过（缺 tools/audit_consistency.py）')

    # ⑩ 语感体检（v5.265：对外文本——依 §7.2 分档，**只定位候选、不阻塞**）
    tv = find_tool('audit_voice.py')
    if tv:
        rv = subprocess.run([sys.executable, tv], capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
        sums = [l.strip()[8:] for l in (rv.stdout or '').split('\n') if l.startswith('SUMMARY ')]
        print('[10] 语感体检：%s' % (' ｜ '.join(sums) if sums else '?'))
        print('     ℹ 只定位不阻塞——正文的反向命中多为正当条目（指标 / 门槛 / 非功能阈值本就“给实现”）；'
              '但**低于零的正向信号（判断 · 量级 · 经验坐标 · 代价）才是要补的**')
    else:
        print('[10] 语感体检：⚠️ 跳过（缺 tools/audit_voice.py）')

    # ⑪ 术语体检（v5.292：一个东西一个名字——依 §9.13；只定位、不阻塞）
    tt = find_tool('audit_terms.py')
    if tt:
        rt = subprocess.run([sys.executable, tt], capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
        sm = [l.strip()[8:] for l in (rt.stdout or '').split('\n') if l.startswith('SUMMARY ')]
        print('[11] 术语体检：%s' % (sm[-1] if sm else '?'))
        print('     ℹ 只查禁用变体（正名唯一）；命中处在上方清单给出行号，人工核对')
    else:
        print('[11] 术语体检：⚠️ 跳过（缺 tools/audit_terms.py）')

    # ⑤ 残留关键词
    if residue:
        words = [w.strip() for w in residue.split(',') if w.strip()]
        prd = os.path.join(ROOT, 'internal', '谋全局EnBrain-产品需求文档.md')
        d = open(prd, encoding='utf-8').read() if os.path.exists(prd) else ''
        print('[5] 残留检查：')
        for w in words:
            print('    %-20s 原型 %d · PRD %d' % (w, src.count(w) if os.path.exists(p) else 0, d.count(w)))

    print('\n%s' % ('❌ 未通过：' + ' / '.join(fails) if fails else '✅ 验证通过'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
