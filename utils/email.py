from typing import Any, Dict, List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi import BackgroundTasks
from pydantic import EmailStr
from pathlib import Path
import jinja2

from core.config import settings

# 创建邮件连接配置
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    TEMPLATE_FOLDER=Path(settings.MAIL_TEMPLATES_DIR),
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# 创建 FastMail 实例
mail = FastMail(conf)

# 创建Jinja2模板环境
template_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(settings.MAIL_TEMPLATES_DIR)
)

async def send_email(
    email_to: List[EmailStr],
    subject: str,
    template_name: str,
    template_data: Dict[str, Any]
) -> None:
    """
    发送邮件的通用函数
    """
    # 使用Jinja2渲染模板
    template = template_env.get_template(f"{template_name}.html")
    html_content = template.render(**template_data)
    
    # 创建消息
    message = MessageSchema(
        subject=subject,
        recipients=email_to,
        body=html_content,
        subtype=MessageType.html
    )
    
    # 发送邮件
    await mail.send_message(message)

async def send_verification_email(
    background_tasks: BackgroundTasks,
    email_to: EmailStr,
    token: str,
    username: str
) -> None:
    """
    发送邮箱验证邮件
    """
    subject = f"【{settings.MAIL_FROM_NAME}】请验证您的邮箱"
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    template_data = {
        "username": username,
        "verification_url": verification_url,
        "app_name": settings.MAIL_FROM_NAME,
        "token_part": token[:6]  # 显示部分token作为备用
    }
    
    # 使用BackgroundTasks在后台发送邮件
    background_tasks.add_task(
        send_email,
        email_to=[email_to],
        subject=subject,
        template_name="email_verification",
        template_data=template_data
    )

async def send_password_reset_email(
    background_tasks: BackgroundTasks,
    email_to: EmailStr,
    token: str,
    username: str
) -> None:
    """
    发送密码重置邮件
    """
    subject = f"【{settings.MAIL_FROM_NAME}】密码重置请求"
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    template_data = {
        "username": username,
        "reset_url": reset_url,
        "app_name": settings.MAIL_FROM_NAME,
        "token_part": token[:6],  # 显示部分token作为备用
        "expire_hours": settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
    }
    
    # 使用BackgroundTasks在后台发送邮件
    background_tasks.add_task(
        send_email,
        email_to=[email_to],
        subject=subject,
        template_name="password_reset",
        template_data=template_data
    ) 