from __future__ import annotations

from io import BytesIO
from typing import Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


def render_pdf(
    title: str,
    user_profile: Dict,
    weights: Dict[str, int],
    ranking: List[Dict],
    summary_markdown: str,
    disclaimer: str,
) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    c.setFont("STSong-Light", 12)

    width, height = A4
    y = height - 40

    def line(text: str, step: int = 18) -> None:
        nonlocal y
        if y < 60:
            c.showPage()
            c.setFont("STSong-Light", 12)
            y = height - 40
        c.drawString(40, y, text[:100])
        y -= step

    line(title, 24)
    line(f"国家: {user_profile.get('country')}   专业方向: {user_profile.get('major')}")
    line(f"预算上限: {user_profile.get('budget_max')}")
    line(f"关注维度: {'、'.join(user_profile.get('selected_dimensions', []))}")
    line("")

    line("权重配置:", 20)
    for k, v in weights.items():
        line(f"- {k}: {v}")

    line("", 14)
    line("综合排名:", 20)
    for row in ranking:
        line(f"{row['rank']}. {row['school']} - {row['program']} | 总分 {row['total_score']}")

    line("", 14)
    line("AI分析:", 20)
    for raw in summary_markdown.splitlines():
        for i in range(0, len(raw), 48):
            line(raw[i : i + 48], 16)

    line("", 14)
    line(disclaimer, 16)

    c.save()
    return buffer.getvalue()
