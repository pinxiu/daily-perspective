"""Email the daily highlights and weekly trends over Gmail SMTP.

Needs SMTP_USERNAME + SMTP_APP_PASSWORD (a Google Account App Password) to do
anything; without them, sending is skipped and the digest/trends still get
written to the repo as usual.
"""
from __future__ import annotations

import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from .render import _long_date

DEFAULT_TO = "pinxiu.gong@gmail.com"


def _send(subject: str, html_body: str, text_body: str) -> bool:
    user = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_APP_PASSWORD")
    if not user or not password:
        print("  ! SMTP_USERNAME/SMTP_APP_PASSWORD not set: skipping email")
        return False

    to_addr = os.environ.get("EMAIL_TO") or DEFAULT_TO
    from_addr = os.environ.get("EMAIL_FROM") or user
    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or 465)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(host, port) as server:
            server.login(user, password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        print(f"  sent email to {to_addr}")
        return True
    except Exception as e:  # a failed send shouldn't fail the whole job
        print(f"  ! sending email failed: {e}")
        return False


def _daily_content(day: date, reflection: str, sections: list[dict], site_url: str) -> tuple[str, str, str]:
    link = f"{site_url.rstrip('/')}/{day.isoformat()}.html" if site_url else f"{day.isoformat()}.html"

    text = [_long_date(day), ""]
    html = [f'<h1 style="font-family:Georgia,serif">{escape(_long_date(day))}</h1>']
    if reflection:
        text += [reflection, ""]
        html.append(f'<p style="font-style:italic;color:#444">{escape(reflection)}</p>')

    for s in sections:
        if not s["stories"]:
            continue
        text.append(s["name"].upper())
        html.append(f'<h2 style="font-family:sans-serif;font-size:1.05rem">{escape(s["name"])}</h2>')
        if s["overview"]:
            text.append(s["overview"])
            html.append(f'<p style="color:#333">{escape(s["overview"])}</p>')
        html.append('<ul style="padding-left:1.2rem">')
        for st in s["stories"]:
            it = st["item"]
            text.append(f"- {it.title} ({it.source})")
            html.append(f'<li><a href="{escape(it.url)}">{escape(it.title)}</a> '
                        f'<span style="color:#888">— {escape(it.source)}</span>')
            if st.get("why_it_matters"):
                text.append(f"  {st['why_it_matters']}")
                html.append(f'<br><span style="color:#555">{escape(st["why_it_matters"])}</span>')
            html.append("</li>")
        html.append("</ul>")
        text.append("")

    text.append(f"Full digest: {link}")
    html.append(f'<p><a href="{escape(link)}">Read the full digest online →</a></p>')

    subject = f"Daily Perspective — {_long_date(day)}"
    return subject, "\n".join(html), "\n".join(text)


def send_daily_email(day: date, reflection: str, sections: list[dict], site_url: str) -> bool:
    if not any(s["stories"] for s in sections):
        return False
    subject, html, text = _daily_content(day, reflection, sections, site_url)
    return _send(subject, f"<html><body>{html}</body></html>", text)


def send_weekly_email(today: date, trends: dict[str, str]) -> bool:
    if not trends:
        return False
    subject = f"Weekly trends — {_long_date(today)}"
    text = [f"Weekly trends, week ending {_long_date(today)}", ""]
    html = [
        '<h1 style="font-family:Georgia,serif">Weekly trends</h1>',
        f'<p style="color:#888">Week ending {escape(_long_date(today))}</p>',
    ]
    for name, t in trends.items():
        text += [name.upper(), t, ""]
        html += [
            f'<h2 style="font-family:sans-serif;font-size:1.05rem">{escape(name)}</h2>',
            f'<p style="color:#333">{escape(t)}</p>',
        ]
    return _send(subject, f"<html><body>{''.join(html)}</body></html>", "\n".join(text))
