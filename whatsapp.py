# whatsapp.py — Meta Cloud API helper for sending guest cards
import os
import requests
import logging

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_VERSION = "v19.0"
WHATSAPP_API_BASE = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"


def _headers():
    return {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    }


def upload_media(image_bytes: bytes, filename: str, mime_type: str = "image/png") -> str:
    """
    Upload an image to Meta's media endpoint.
    Returns the media_id string to use in send_image_message.
    """
    url = f"{WHATSAPP_API_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/media"
    files = {
        "file": (filename, image_bytes, mime_type),
    }
    data = {
        "messaging_product": "whatsapp",
        "type": mime_type,
    }
    response = requests.post(url, headers=_headers(), files=files, data=data)
    response.raise_for_status()
    result = response.json()
    media_id = result.get("id")
    if not media_id:
        raise ValueError(f"No media_id in response: {result}")
    logging.info(f"Uploaded media: {media_id}")
    return media_id


def send_image_message(to: str, media_id: str, caption: str) -> dict:
    """
    Send an image message with caption to a WhatsApp number.
    `to` must be in international format without +, e.g. '255674114407'
    Returns the API response dict.
    """
    url = f"{WHATSAPP_API_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "image",
        "image": {
            "id": media_id,
            "caption": caption,
        },
    }
    response = requests.post(url, headers=_headers(), json=payload)
    response.raise_for_status()
    return response.json()


def send_guest_card(to: str, guest_name: str, visual_id: int,
                    card_type: str, image_bytes: bytes, filename: str) -> dict:
    """
    Full flow: upload image then send to guest.
    Returns the API response dict.
    """
    media_id = upload_media(image_bytes, filename)

    card_type_label = (card_type or "single").title()
    caption = (
        f"Dear {guest_name},\n\n"
        f"Please find your invitation card attached.\n"
        f"Card No: *{visual_id:04d}*\n"
        f"Card Type: *{card_type_label}*\n\n"
        f"Please present this card at the entrance on the day of the event.\n\n"
        f"We look forward to celebrating with you!"
    )

    return send_image_message(to, media_id, caption)