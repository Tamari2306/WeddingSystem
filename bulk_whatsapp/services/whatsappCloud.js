import axios from "axios";
import dotenv from "dotenv";
dotenv.config();

const TOKEN = process.env.WHATSAPP_CLOUD_API_TOKEN;
const PHONE_ID = process.env.WHATSAPP_PHONE_NUMBER_ID;

export async function sendWhatsAppTemplate(to, templateData) {
  if (!TOKEN || !PHONE_ID) {
    console.log("⚠️ WhatsApp Cloud API credentials missing. Message skipped.");
    return;
  }

  try {
    const url = `https://graph.facebook.com/v20.0/${PHONE_ID}/messages`;

    const payload = {
      messaging_product: "whatsapp",
      to,
      type: "template",
      template: templateData,
    };

    const response = await axios.post(url, payload, {
      headers: {
        Authorization: `Bearer ${TOKEN}`,
        "Content-Type": "application/json",
      },
    });

    console.log("✅ Sent:", to);
    return response.data;

  } catch (error) {
    console.error("❌ Error sending to", to, error.response?.data || error);
  }
}
