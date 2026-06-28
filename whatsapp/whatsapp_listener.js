console.log("STARTING...");

const GROUP_NAME = "AIC-CIIC Worklog";

const { Client, LocalAuth } = require("whatsapp-web.js");
const axios = require("axios");

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: false
    }
});

client.on("qr", () => {
    console.log("QR GENERATED");
});

client.on("authenticated", () => {
    console.log("AUTHENTICATED");
});

client.on("loading_screen", (percent, msg) => {
    console.log(percent, msg);
});

client.on("change_state", state => {
    console.log("STATE:", state);
});

client.on("auth_failure", msg => {
    console.log("AUTH FAILURE:", msg);
});

client.on("disconnected", reason => {
    console.log("DISCONNECTED:", reason);
});

client.on("ready", async () => {

    console.log("READY");

    try {

        await new Promise(resolve => setTimeout(resolve, 5000));

        const chats = await client.getChats();

        const group = chats.find(
            chat =>
                chat.isGroup &&
                chat.name === GROUP_NAME
        );

        if (!group) {
            console.log("GROUP NOT FOUND");
            chats.filter(c => c.isGroup).forEach(c => console.log(c.name));
            process.exit(1);
        }

        console.log("GROUP FOUND");

        const messages = await group.fetchMessages({ limit: 1000 });

        console.log("TOTAL MESSAGES:", messages.length);

        const today = new Date();
        let synced = 0;

        for (const msg of messages) {

            if (!msg.body || !msg.body.trim()) continue;

            const msgDate = new Date(msg.timestamp * 1000);

            console.log(msg.body.substring(0, 60));
            console.log("TODAY:", today.toISOString());
            console.log("MESSAGE DATE:", msgDate.toISOString());

            if (
                msgDate.getDate()     !== today.getDate()     ||
                msgDate.getMonth()    !== today.getMonth()    ||
                msgDate.getFullYear() !== today.getFullYear()
            ) {
                continue;
            }

            try {

                // --- Extract phone from msg.author BEFORE any contact lookup ---
                // msg.author in groups: "919876543210@c.us" or "20336720511031:44@lid"
                // We want just the digit part before "@"
                const rawAuthor = msg.author || msg.from || "";
                const senderPhone = rawAuthor.split("@")[0].split(":")[0];

                let contact = null;
                let senderName = "Unknown";

                try {
                    if (msg.author) {
                        contact = await client.getContactById(msg.author);
                    } else {
                        contact = await msg.getContact();
                    }
                    senderName =
                        contact?.pushname ||
                        contact?.name     ||
                        contact?.shortName||
                        "Unknown";
                } catch (e) {
                    console.log("CONTACT ERROR:", e.message);
                    // senderName stays "Unknown" — that's fine,
                    // the server will match via phone or message content
                }

                const payload = {
                    sender_name:  senderName,
                    sender_phone: senderPhone,   // clean digits only, no ":44" or "@c.us"
                    message:      msg.body,
                    timestamp:    msg.timestamp
                };

                console.log("SENDING:");
                console.log(payload);

                const response = await axios.post(
                    "http://127.0.0.1:8000/api/worklogs/whatsapp",
                    payload
                );

                console.log("RESPONSE:");
                console.log(response.data);

                synced++;

            } catch (err) {
                console.log("ERROR:");
                console.log(err.response?.data || err.message);
            }
        }

        console.log("SYNC COMPLETE");
        console.log("MESSAGES SYNCED:", synced);

        setTimeout(() => {
            console.log("EXITING");
            process.exit(0);
        }, 3000);

    } catch (err) {
        console.log("SYNC ERROR");
        console.log(err);
        process.exit(1);
    }

});

client.initialize();