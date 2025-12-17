# -*- coding: utf-8 -*-
"""
报告生成器 - 生成HTML格式的问题报告
"""

import os
import shutil
from datetime import datetime
from jinja2 import Template


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data', 'reports'
        )
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate(self, issues: list, session_id: str) -> str:
        report_dir = os.path.join(self.output_dir, session_id)
        os.makedirs(report_dir, exist_ok=True)
        media_dir = os.path.join(report_dir, 'media')
        os.makedirs(media_dir, exist_ok=True)
        
        processed_issues = []
        for issue in issues:
            processed = issue.copy()
            if 'media_path' in processed and os.path.exists(processed['media_path']):
                filename = os.path.basename(processed['media_path'])
                dest_path = os.path.join(media_dir, filename)
                shutil.copy2(processed['media_path'], dest_path)
                processed['media_filename'] = f'media/{filename}'
            else:
                processed['media_filename'] = ''
            processed_issues.append(processed)
        
        design_issues = [i for i in processed_issues if i.get('category') == '设计']
        dev_issues = [i for i in processed_issues if i.get('category') == '开发']
        discuss_issues = [i for i in processed_issues if i.get('category') not in ['设计', '开发']]
        
        template = Template(self._get_template())
        html_content = template.render(
            session_id=session_id,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_count=len(issues),
            design_count=len(design_issues),
            dev_count=len(dev_issues),
            discuss_count=len(discuss_issues),
            design_issues=design_issues,
            dev_issues=dev_issues,
            discuss_issues=discuss_issues
        )
        
        report_path = os.path.join(report_dir, 'report.html')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return report_path
    
    def _get_template(self):
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>APP体验问题清单</title>
    <style>
        body{font-family:sans-serif;background:#f5f5f5;padding:20px}
        .container{max-width:900px;margin:0 auto}
        header{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:30px;border-radius:12px;margin-bottom:24px}
        .stats{display:flex;gap:16px;margin-bottom:24px}
        .stat-card{background:#fff;padding:16px;border-radius:8px;flex:1;text-align:center}
        .stat-card .number{font-size:32px;font-weight:bold;color:#667eea}
        .issue-card{background:#fff;margin-bottom:16px;border-radius:8px;overflow:hidden}
        .issue-header{padding:16px;border-bottom:1px solid #eee;display:flex;align-items:center;gap:12px}
        .issue-number{background:#667eea;color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center}
        .issue-content{padding:16px}
        .issue-media img{max-width:100%;border-radius:8px}
        .category-title{padding:12px 16px;background:#fff;border-left:4px solid #667eea}
        .category-title.design{border-left-color:#e91e63}
        .category-title.dev{border-left-color:#2196f3}
        .user-note{background:#fff3e0;padding:12px;border-radius:6px;margin-top:12px}
    </style>
</head>
<body>
<div class="container">
    <header><h1>APP体验问题清单</h1><div>{{ timestamp }}</div></header>
    <div class="stats">
        <div class="stat-card"><div class="number">{{ total_count }}</div><div>总问题数</div></div>
        <div class="stat-card"><div class="number">{{ design_count }}</div><div>设计问题</div></div>
        <div class="stat-card"><div class="number">{{ dev_count }}</div><div>开发问题</div></div>
    </div>
    {% for issue in design_issues + dev_issues + discuss_issues %}
    <div class="issue-card">
        <div class="issue-header">
            <div class="issue-number">{{ issue.id }}</div>
            <div>{{ issue.title }}</div>
            <span>[{{ issue.category }}]</span>
        </div>
        <div class="issue-content">
            {% if issue.media_filename %}<div class="issue-media"><img src="{{ issue.media_filename }}"></div>{% endif %}
            {% if issue.description %}<p>{{ issue.description }}</p>{% endif %}
            {% if issue.suggestion %}<p>建议: {{ issue.suggestion }}</p>{% endif %}
            {% if issue.user_note %}<div class="user-note">{{ issue.user_note }}</div>{% endif %}
        </div>
    </div>
    {% endfor %}
</div>
</body>
</html>"""
