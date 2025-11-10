"""
modules/export_ppt.py

Create board-ready PPTX reports (OpenAI-Slate Modern theme by default).

Exposes:
 - create_pptx_from_insights(cards, out_path='report.pptx', logo_path=None)

`cards` is a list of dicts with keys:
  - title: str
  - summary: str
  - df: pandas.DataFrame (optional)
  - chart: dict (optional) -> { 'type': 'bar'|'line', 'x': colname, 'y': colname }

The function will render small charts using matplotlib and embed them as images on slides.

If python-pptx or matplotlib are not installed, the function will raise RuntimeError with guidance.

"""
from pathlib import Path
import time
import io
import os

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
except Exception:
    Presentation = None

try:
    import matplotlib.pyplot as plt
    import pandas as pd
except Exception:
    plt = None
    pd = None


def _ensure_dependencies():
    if Presentation is None:
        raise RuntimeError('python-pptx is required. Install with: pip install python-pptx')
    if plt is None or pd is None:
        raise RuntimeError('matplotlib and pandas are required. Install with: pip install matplotlib pandas')


def _df_to_image(df, chart_spec=None, out_path=None):
    """Render a small chart or table snapshot to an image file and return path."""
    if plt is None or pd is None:
        raise RuntimeError('matplotlib/pandas required for charts')

    fig, ax = plt.subplots(figsize=(6, 3))
    if chart_spec and chart_spec.get('type') == 'bar' and chart_spec.get('x') and chart_spec.get('y'):
        x = chart_spec['x']
        y = chart_spec['y']
        if x in df.columns and y in df.columns:
            ax.bar(df[x].astype(str), df[y])
            ax.set_xlabel(x)
            ax.set_ylabel(y)
            ax.set_title(chart_spec.get('title', ''))
        else:
            # fallback: show head of df as table
            ax.axis('off')
            table = ax.table(cellText=df.head(8).values, colLabels=df.head(8).columns, loc='center')
            table.auto_set_font_size(False)
            table.set_fontsize(8)
    else:
        # default: show a small table snapshot
        ax.axis('off')
        table = ax.table(cellText=df.head(8).values, colLabels=df.head(8).columns, loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(8)

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)

    if out_path:
        with open(out_path, 'wb') as f:
            f.write(buf.read())
        return out_path
    # else return bytes
    return buf


def create_pptx_from_insights(cards, out_path='report.pptx', logo_path=None):
    """Create PPTX file from a list of insight cards.

    cards: list of {title, summary, df (pandas.DataFrame) optional, chart optional}
    """
    _ensure_dependencies()
    prs = Presentation()

    # Title slide
    title_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = 'Automated Insights Report'
    subtitle.text = f'Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}'

    # Apply OpenAI-Slate Modern theme colors by customizing text where possible
    # Note: python-pptx doesn't support global theme changes, so we set colors per shape.

    for card in cards:
        layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
        s = prs.slides.add_slide(layout)
        # Title
        try:
            s.shapes.title.text = card.get('title', 'Insight')
        except Exception:
            pass
        # Body
        body_placeholder = None
        for ph in s.placeholders:
            if ph.placeholder_format.type == 1 or ph.placeholder_format.type == 2:
                body_placeholder = ph
                break
        if body_placeholder is not None:
            tf = body_placeholder.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = card.get('summary', '')
            p.font.size = Pt(14)
            p.font.bold = True
            p.font.name = 'Arial'
            p.font.color.rgb = RGBColor(40, 40, 40)

        # Add DataFrame snapshot as chart image if present
        df = card.get('df')
        chart_spec = card.get('chart')
        if df is not None and hasattr(df, 'to_csv'):
            img_buf = _df_to_image(df, chart_spec)
            # Save temp image
            tmp_path = f"/tmp/insight_{int(time.time()*1000)}.png"
            with open(tmp_path, 'wb') as f:
                f.write(img_buf.read())
            left = Inches(5.5)
            top = Inches(1.5)
            height = Inches(3)
            try:
                s.shapes.add_picture(tmp_path, left, top, height=height)
            except Exception:
                # fallback: skip image
                pass
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    prs.save(out_path)
    return out_path


if __name__ == '__main__':
    print('export_ppt module. Call create_pptx_from_insights(cards, out_path)')
