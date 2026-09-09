"""
邮件通知模块 - 采集完成后发送邮件通知
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


class EmailNotifier:
    def __init__(self, email_config: dict):
        self.config = email_config
        self.enabled = email_config.get("enabled", False)
        self.logger = logging.getLogger(__name__)

    def send_notification(self, cards: list, stats: Optional[dict] = None) -> bool:
        if not self.enabled:
            self.logger.info("邮件通知未启用")
            return False

        required = ["smtp_host", "smtp_user", "smtp_password", "to"]
        if not all(self.config.get(k) for k in required):
            self.logger.warning("邮件配置不完整")
            return False

        try:
            subject = self._build_subject(cards)
            body = self._build_body(cards, stats)
            msg = MIMEMultipart('alternative')
            from_name = self.config.get('from_name', 'InterviewHunter')
            from_email = self.config['smtp_user']
            msg['Subject'] = subject
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = self.config['to']
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            self._send(msg)
            self.logger.info(f"邮件已发送至 {self.config['to']}")
            return True
        except Exception as e:
            self.logger.error(f"邮件发送失败: {e}")
            return False

    def _build_subject(self, cards: list) -> str:
        count = len(cards)
        if count == 0:
            return "[面经日报] 今日暂无新面经"
        companies = list(set(c.get("company", "未知") for c in cards if c.get("company")))
        company_str = "、".join(companies[:3]) if companies else "多公司"
        return f"[面经日报] 今日新增 {count} 篇 - {company_str}"

    def _build_body(self, cards: list, stats: Optional[dict] = None) -> str:
        if not cards:
            return """<html><body><h2>今日面经日报</h2><p>今日暂无新面经入库。</p></body></html>"""

        items_html = []
        for c in cards[:20]:
            title = c.get("question", "无标题")[:80]
            company = c.get("company", "未知公司")
            position = c.get("position", "")
            tags = c.get("tags", [])
            summary = c.get("answer", "")[:150]
            tags_html = " ".join(
                f'<span style="background:#e8f4fd;padding:2px 6px;border-radius:3px;margin-right:4px;font-size:12px;">{t}</span>'
                for t in tags[:5]
            )
            items_html.append(f"""
            <div style="margin-bottom:20px;padding:15px;border-left:4px solid #4a90d9;background:#f9f9f9;">
                <h3 style="margin:0 0 8px 0;">{title}</h3>
                <p style="margin:0 0 8px 0;color:#666;font-size:14px;">
                    <strong>{company}</strong> {f'| {position}' if position else ''}
                </p>
                <div style="margin-bottom:8px;">{tags_html}</div>
                <p style="margin:0;color:#333;font-size:13px;line-height:1.6;">{summary}...</p>
            </div>""")

        stats_html = ""
        if stats:
            stats_html = f"""
            <div style="background:#f0f7ff;padding:15px;border-radius:8px;margin-bottom:20px;">
                <h4 style="margin:0 0 10px 0;">📊 统计概览</h4>
                <p style="margin:5px 0;">总计收录: <strong>{stats.get('total', 0)}</strong> 篇</p>
                <p style="margin:5px 0;">今日新增: <strong>{stats.get('today', 0)}</strong> 篇</p>
            </div>"""

        return f"""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"></head>
        <body style="font-family:'Microsoft YaHei',Arial,sans-serif;max-width:700px;margin:0 auto;padding:20px;">
            <div style="background:linear-gradient(135deg,#4a90d9,#67b26f);padding:25px;border-radius:8px 8px 0 0;">
                <h1 style="margin:0;color:#fff;font-size:24px;">📚 面经日报</h1>
            </div>
            <div style="background:#fff;padding:25px;border:1px solid #e0e0e0;border-top:none;">
                {stats_html}
                <h2 style="margin:0 0 15px 0;color:#333;">今日新增面经 ({len(cards)}篇)</h2>
                {"".join(items_html)}
                <p style="color:#888;font-size:12px;margin-top:20px;text-align:center;">
                    本邮件由 InterviewHunter 自动发送
                </p>
            </div>
        </body></html>"""

    def _send(self, msg):
        smtp_host = self.config["smtp_host"]
        smtp_port = self.config.get("smtp_port", 587)
        smtp_user = self.config["smtp_user"]
        smtp_password = self.config["smtp_password"]
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
