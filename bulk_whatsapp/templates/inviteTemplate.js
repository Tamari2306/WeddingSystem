export function inviteTemplate(name, cardNumber, imageUrl) {
  return {
    name: "invite_template",
    language: { code: "sw" },
    components: [
      {
        type: "header",
        parameters: [{ type: "image", image: { link: imageUrl } }],
      },
      {
        type: "body",
        parameters: [
          { type: "text", text: name },
          { type: "text", text: cardNumber }
        ],
      },
      {
        type: "button",
        sub_type: "quick_reply",
        index: "0",
        parameters: [{ type: "payload", payload: "NITAKUWEPO" }],
      },
      {
        type: "button",
        sub_type: "quick_reply",
        index: "1",
        parameters: [{ type: "payload", payload: "SITAKUWEPO" }],
      }
    ],
  };
}
