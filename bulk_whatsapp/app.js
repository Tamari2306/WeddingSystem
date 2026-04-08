import axios from "axios";
import fs from "fs";
import cloudinary from "cloudinary";
import "dotenv/config";

// Load Cloudinary + WhatsApp config from .env as earlier

async function fetchGuests() {
  try {
    const response = await axios.get("http://localhost:5000/api/guests");
    return response.data.guests;
  } catch (err) {
    console.error("Error fetching guests:", err.message);
    return [];
  }
}

async function sendBulkInvitations() {
    const guests = await fetchGuests();

    console.log(`Sending invitations to ${guests.length} guests...`);

    for (const guest of guests) {
        await sendInvitationMessage(guest);
        await new Promise(res => setTimeout(res, 500)); // Rate limit
    }

    console.log("Done sending all invitations.");
}
