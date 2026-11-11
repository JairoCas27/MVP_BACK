import os
import smtplib
from email.message import EmailMessage
from datetime import datetime

BRAND = "La Fogata"
COLOR = "#D63447"

def _cfg():
    return {
        'host': os.getenv('SMTP_HOST', ''),
        'port': int(os.getenv('SMTP_PORT', '587')),
        'user': os.getenv('SMTP_USER', ''),
        'password': os.getenv('SMTP_PASSWORD', ''),
        'from_addr': os.getenv('SMTP_FROM', os.getenv('SMTP_USER', 'no-reply@lafogata.com')),
        'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
    }

def _wrap(title, body_html):
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:linear-gradient(135deg,#D63447 0%,#a82333 100%);padding:28px 32px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:26px;font-weight:800;letter-spacing:-0.5px;">{BRAND}</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:13px;">Pollo a la brasa - Pedidos en linea</p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h2 style="margin:0 0 16px;color:#111827;font-size:20px;font-weight:700;">{title}</h2>
            {body_html}
          </td>
        </tr>
        <tr>
          <td style="background:#f9fafb;padding:20px 32px;text-align:center;border-top:1px solid #e5e7eb;">
            <p style="margin:0;color:#6b7280;font-size:12px;">{BRAND} - Pollo a la brasa - Lima, Peru</p>
            <p style="margin:4px 0 0;color:#9ca3af;font-size:11px;">Este es un correo automatico, por favor no responder.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

def send_email(to, subject, html_body):
    cfg = _cfg()
    if not to:
        return False
    if not cfg['host'] or not cfg['user']:
        print(f"[EMAIL DEMO] To: {to} | Subject: {subject}")
        print(html_body[:500])
        try:
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'emails.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"--- {datetime.now()} ---\nTo: {to}\nSubject: {subject}\n{html_body}\n\n")
        except Exception:
            pass
        return True
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = cfg['from_addr']
        msg['To'] = to
        msg.set_content("Este correo requiere un cliente compatible con HTML.")
        msg.add_alternative(html_body, subtype='html')
        with smtplib.SMTP(cfg['host'], cfg['port'], timeout=20) as server:
            if cfg['use_tls']:
                server.starttls()
            server.login(cfg['user'], cfg['password'])
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

def send_welcome(name, email):
    body = f"""
    <p style="color:#374151;font-size:15px;line-height:1.6;">Hola <strong>{name}</strong>,</p>
    <p style="color:#374151;font-size:15px;line-height:1.6;">Gracias por crear tu cuenta en {BRAND}. Ahora puedes:</p>
    <ul style="color:#374151;font-size:15px;line-height:1.8;">
      <li>Hacer pedidos en linea en segundos</li>
      <li>Elegir modalidad: salon, recojo o delivery</li>
      <li>Pagar con Yape, Plin o efectivo</li>
      <li>Seguir el estado de tu pedido en tiempo real</li>
    </ul>
    <p style="color:#374151;font-size:15px;line-height:1.6;">Te esperamos!</p>
    <a href="#" style="display:inline-block;margin-top:12px;padding:12px 24px;background:{COLOR};color:#fff;text-decoration:none;border-radius:999px;font-weight:700;">Ir a la tienda</a>
    """
    return send_email(email, f"Bienvenido a {BRAND}!", _wrap("Bienvenido", body))

def send_receipt(order, items):
    email = order.customer_email
    if not email:
        return False
    rows = "".join(
        f"<tr><td style='padding:8px 0;border-bottom:1px solid #f1f5f9'>{it['product_name']}</td>"
        f"<td style='padding:8px 0;border-bottom:1px solid #f1f5f9;text-align:center'>{it['quantity']}</td>"
        f"<td style='padding:8px 0;border-bottom:1px solid #f1f5f9;text-align:right'>S/ {float(it['subtotal']):.2f}</td></tr>"
        for it in items
    )
    body = f"""
    <p style="color:#374151;font-size:15px;line-height:1.6;">Hola <strong>{order.customer_name}</strong>, gracias por tu compra.</p>
    <p style="color:#6b7280;font-size:13px;">Pedido <strong>#{order.id}</strong> - {order.order_type} - {order.payment_type}</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
      <thead>
        <tr style="border-bottom:2px solid #e5e7eb;">
          <th style="text-align:left;padding:8px 0;color:#6b7280;font-size:12px;text-transform:uppercase;">Producto</th>
          <th style="text-align:center;padding:8px 0;color:#6b7280;font-size:12px;text-transform:uppercase;">Cant.</th>
          <th style="text-align:right;padding:8px 0;color:#6b7280;font-size:12px;text-transform:uppercase;">Subtotal</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <div style="display:flex;justify-content:space-between;padding:12px 0;border-top:2px solid #e5e7eb;font-weight:700;">
      <span>Total</span>
      <span style="color:{COLOR};font-size:18px;">S/ {float(order.total_amount):.2f}</span>
    </div>
    {f"<p style='color:#6b7280;font-size:13px;margin-top:8px;'>Direccion: {order.delivery_address}</p>" if order.delivery_address else ""}
    {f"<p style='color:#6b7280;font-size:13px;'>Mesa: {order.table_number}</p>" if getattr(order, 'table_number', None) else ""}
    """
    return send_email(email, f"Boleta de tu pedido #{order.id}", _wrap(f"Boleta #{order.id}", body))

def send_status_update(order, status):
    email = order.customer_email
    if not email:
        return False
    status_colors = {
        "PENDIENTE": "#D97706",
        "PREPARANDO": "#0284C7",
        "EN_CAMINO": "#7C3AED",
        "LISTO_PARA_RECOJO": "#16A34A",
        "FINALIZADO": "#16A34A",
        "CANCELADO": "#DC2626",
    }
    color = status_colors.get(status, "#D63447")

    try:
        from app.models.database import Order as O
        o = O.query.get(order.id)
        items = o.items if o else []
    except Exception:
        items = getattr(order, 'items', []) or []

    items_html = ""
    for it in items:
        name = 'Producto'
        try:
            from app.models.database import Product
            prod = Product.query.get(it.product_id)
            if prod:
                name = prod.name
        except Exception:
            pass
        if getattr(it, 'product_name', None):
            name = it.product_name
        items_html += f"""
        <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:14px;">
          <div style="flex:1;">
            <div style="font-weight:600;">{it.quantity}x {name}</div>
            {f"<div style='color:#6b7280;font-size:12px;margin-top:2px;'>{it.options}</div>" if getattr(it, 'options', None) else ""}
          </div>
          <div style="font-weight:700;">S/ {float(it.subtotal):.2f}</div>
        </div>
        """

    status_to_idx = {
        "PENDIENTE": 0,
        "PREPARANDO": 1,
        "EN_CAMINO": 2,
        "LISTO_PARA_RECOJO": 2,
        "FINALIZADO": 3,
        "CANCELADO": -1,
    }
    current_idx = status_to_idx.get(status, 0)
    steps = ["PENDIENTE", "PREPARANDO", "LISTO", "FINALIZADO"]
    step_cells = ""
    for idx, step in enumerate(steps):
        done = current_idx >= idx
        label = "En camino" if (step == "LISTO" and order.order_type == "DELIVERY") else ("Listo" if step == "LISTO" else step.capitalize())
        bg = "linear-gradient(135deg,#D63447,#a82333)" if done else "#e5e7eb"
        col = "#fff" if done else "#9ca3af"
        txt = "#D63447" if done else "#9ca3af"
        shadow = "0 4px 12px rgba(214,52,71,0.35)" if done else "none"
        mark = "\u2713" if done else str(idx + 1)
        step_cells += f"""
        <td style="text-align:center;vertical-align:top;width:25%;padding:0 4px;">
          <div style="width:34px;height:34px;border-radius:50%;margin:0 auto 6px;display:inline-flex;align-items:center;justify-content:center;background:{bg};color:{col};font-weight:700;font-size:13px;box-shadow:{shadow};">
            {mark}
          </div>
          <div style="font-size:11px;color:{txt};font-weight:600;">{label}</div>
        </td>
        """

    body = f"""
    <div style="background:#f9fafb;border-radius:16px;padding:20px 16px;margin-bottom:16px;">
      <div style="text-align:center;margin-bottom:18px;">
        <div style="color:#6b7280;font-size:12px;margin-bottom:6px;">Estado actual</div>
        <span style="display:inline-block;padding:8px 24px;background:{color};color:#fff;border-radius:999px;font-weight:700;font-size:15px;">{status}</span>
      </div>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        <tr>{step_cells}</tr>
      </table>
    </div>

    <p style="color:#374151;font-size:15px;line-height:1.6;">Hola <strong>{order.customer_name}</strong>, el estado de tu pedido <strong>#{order.id}</strong> cambio a <strong>{status}</strong>.</p>

    <div style="margin:16px 0;">
      <h3 style="font-size:14px;font-weight:700;color:#111827;margin-bottom:8px;">Productos</h3>
      {items_html}
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px;border-top:2px solid #e5e7eb;">
        <tr>
          <td style="padding:10px 0;font-weight:700;">Pago: {order.payment_type}</td>
          <td style="padding:10px 0;font-weight:700;text-align:right;color:{COLOR};font-size:18px;">Total: S/ {float(order.total_amount):.2f}</td>
        </tr>
      </table>
    </div>

    <div style="border-top:1px solid #e5e7eb;padding-top:12px;font-size:13px;color:#6b7280;">
      <div>Cliente: <strong style="color:#374151">{order.customer_name}</strong></div>
      <div>Tipo de pedido: <strong style="color:#374151">{order.order_type}</strong></div>
      {f"<div>Direccion: <strong style='color:#374151'>{order.delivery_address}</strong></div>" if order.delivery_address else ""}
    </div>
    """
    return send_email(email, f"Actualizacion de tu pedido #{order.id}", _wrap(f"Pedido #{order.id}", body))

def send_reset_token(email, token):
    body = f"""
    <p style="color:#374151;font-size:15px;line-height:1.6;">Recibimos una solicitud para restablecer tu contraseña.</p>
    <div style="text-align:center;margin:24px 0;">
      <div style="display:inline-block;padding:16px 32px;background:#f9fafb;border:2px dashed #D63447;border-radius:12px;">
        <span style="font-size:32px;font-weight:800;letter-spacing:6px;color:#D63447;">{token}</span>
      </div>
    </div>
    <p style="color:#6b7280;font-size:13px;">Este codigo expira en <strong>90 segundos</strong>. Si no solicitaste este cambio, ignora este correo.</p>
    """
    return send_email(email, "Recuperar contraseña - La Fogata", _wrap("Recuperar contraseña", body))