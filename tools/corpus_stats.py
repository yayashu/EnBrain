# -*- coding: utf-8 -*-
"""公开文档语料统计（可重复执行）——PRD F16.6.1 / B1 / 实测记录的**数字复算入口**。

用法：
    python tools/corpus_stats.py            # 统计（并报告编码状态）
    python tools/corpus_stats.py --fix      # 顺手修 toc.json 的乱码标题（改前自动备份）

为什么要有这个工具：被引用的数字（"40 页 / 25 页运维 / N 个二级标题"）**必须能被复算**，
不能手写进文档（方法论已记过 4 次"手写计数必错"的教训）。
"""
import io
import json
import os
import shutil
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOC = os.path.join(ROOT, 'internal', 'kb-corpus', 'odoo', 'toc.json')   # 语料属内部材料，不随开源发布

# 运维 / 部署语境词（用于判定"二级标题是不是功能模块名"）
OPS_WORDS = ['安装', '配置', '版本', '升级', '更新', '容器', '数据库', '备份', '迁移', '部署',
             '账户', '邮件', '安全', '日志', '监控', '系统需求', '下载', '启动', '设置',
             '域名', '服务器', '性能', '维护', '故障', '调试', '恢复']


def fix_mojibake(s):
    """把"UTF-8 被按 GBK 读"造成的乱码还原；不可还原则原样返回。"""
    if not isinstance(s, str):
        return s
    try:
        back = s.encode('gbk').decode('utf-8')
        return back
    except Exception:
        return s


def looks_mojibake(s):
    try:
        s.encode('gbk').decode('utf-8')
        return True
    except Exception:
        return False


def load():
    if not os.path.exists(TOC):
        raise SystemExit('!! 语料未就绪：%s\n'
                         '   语料（Odoo 中文文档 40 页）属内部材料，不随开源发布；\n'
                         '   复算方法见 experiments/公开文档实测记录.md §一（来源与规模）与 §二（命令）。'
                         % TOC)
    with io.open(TOC, encoding='utf-8', errors='replace') as f:
        return json.load(f)


def stats(data, decoded):
    pages = len(data)
    ops = [e for e in data if str(e.get('slug', '')).startswith('administration')]
    apps = [e for e in data if not str(e.get('slug', '')).startswith('administration')]
    lv = {}
    for e in data:
        for h in (e.get('headings') or []):
            k = h.get('level')
            lv[k] = lv.get(k, 0) + 1

    def h_of(level, group=None):
        src = data if group is None else group
        return sum(1 for e in src for h in (e.get('headings') or []) if h.get('level') == level)

    def ops_ratio(group):
        """该组 h2 标题里，含运维语境词的比例（＝"标题是不是功能模块"的反向指标）"""
        tot = hit = 0
        for e in group:
            for h in (e.get('headings') or []):
                if h.get('level') != 2:
                    continue
                t = h.get('title') or ''
                tot += 1
                if any(w in t for w in OPS_WORDS):
                    hit += 1
        return tot, hit

    ops_tot, ops_hit = ops_ratio(ops)
    app_tot, app_hit = ops_ratio(apps)
    chars = [e.get('chars', 0) for e in data]
    return {
        'pages': pages,
        'ops': len(ops), 'apps': len(apps),
        'levels': lv,
        'h1': h_of(1), 'h2': h_of(2), 'h3': h_of(3), 'h4': h_of(4),
        'ops_h2': h_of(2, ops), 'app_h2': h_of(2, apps),
        'ops_h2_all': ops_tot, 'ops_h2_opsword': ops_hit,
        'app_h2_all': app_tot, 'app_h2_opsword': app_hit,
        'chars_total': sum(chars),
        'chars_median': sorted(chars)[len(chars) // 2] if chars else 0,
        'decoded': decoded,
    }


def main(argv):
    data = load()
    decoded = not any(looks_mojibake(h.get('title') or '')
                      for e in data[:6] for h in (e.get('headings') or []))

    if '--fix' in argv and not decoded:
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        bak_dir = os.path.join(ROOT, 'backups')
        if not os.path.isdir(bak_dir):
            os.makedirs(bak_dir, exist_ok=True)   # 2026-10-25 清理备份目录后按需重建
        shutil.copy(TOC, os.path.join(bak_dir, 'pre-corpus-encoding-%s-toc.json' % ts))
        for e in data:
            e['slug'] = fix_mojibake(e.get('slug', ''))
            e['url'] = fix_mojibake(e.get('url', ''))
            for h in (e.get('headings') or []):
                h['title'] = fix_mojibake(h.get('title') or '')
        with io.open(TOC, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=1))
        print('已修复 toc.json 编码（原文件已备份到 backups/pre-corpus-encoding-%s-*）' % ts)
        data = load()
        decoded = True

    s = stats(data, decoded)
    print('语料：internal/kb-corpus/odoo/toc.json（内部材料，不随开源发布）')
    print('编码状态：%s' % ('✅ 标题可读' if decoded else '⚠ 标题乱码（可跑 --fix 修复）'))
    print()
    print('页数            ：%d' % s['pages'])
    print('  运维 / 部署类 ：%d（slug 前缀 administration*）' % s['ops'])
    print('  应用类        ：%d' % s['apps'])
    print('标题层级分布    ：h1=%d · h2=%d · h3=%d · h4=%d' % (s['h1'], s['h2'], s['h3'], s['h4']))
    print('二级标题（h2）  ：全部 %d · 运维类 %d · 应用类 %d' % (s['h2'], s['ops_h2'], s['app_h2']))
    print('h2 含运维语境词 ：运维类 %d/%d（%.0f%%）· 应用类 %d/%d（%.0f%%）' % (
        s['ops_h2_opsword'], s['ops_h2_all'],
        100.0 * s['ops_h2_opsword'] / (s['ops_h2_all'] or 1),
        s['app_h2_opsword'], s['app_h2_all'],
        100.0 * s['app_h2_opsword'] / (s['app_h2_all'] or 1)))
    print('字符量          ：合计 %d 字 · 单页中位 %d 字' % (s['chars_total'], s['chars_median']))
    print()
    print('SUMMARY pages=%d ops=%d apps=%d h2=%d h2_ops=%d h2_app=%d '
          'ops_opsword_ratio=%.0f%% app_opsword_ratio=%.0f%% chars=%d' % (
              s['pages'], s['ops'], s['apps'], s['h2'], s['ops_h2'], s['app_h2'],
              100.0 * s['ops_h2_opsword'] / (s['ops_h2_all'] or 1),
              100.0 * s['app_h2_opsword'] / (s['app_h2_all'] or 1),
              s['chars_total']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
