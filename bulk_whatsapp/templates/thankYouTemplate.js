export function thankYouTemplate(name, imageUrl) {
  return {
    name: "thank_you_template",
    language: { code: "sw" },
    components: [
      {
        type: "header",
        parameters: [{ type: "image", image: { link: imageUrl } }],
      },
      {
        type: "body",
        parameters: [{ type: "text", text: name }],
      },
      {
        type: "button",
        sub_type: "quick_reply",
        index: "0",
        parameters: [{ type: "payload", payload: "HUDUMA" }],
      },
      {
        type: "button",
        sub_type: "quick_reply",
        index: "1",
        parameters: [{ type: "payload", payload: "WASILIANE" }],
      }
    ],
  };
}
