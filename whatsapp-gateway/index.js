const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');

const PORT = process.env.PORT || 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const GROUP_NAME = process.env.WHATSAPP_GROUP_NAME || 'AIC-CIIC Worklog';

const app = express();
app.use(express.json());

let client;
let targetGroupId = null;
const messageBuffer = [];

function normalizePhone(jid) {
    if (!jid) return '';
    return jid.replace('@s.whatsapp.net', '').replace(/\D/g, '').slice(-10);
}

async function forwardToBackend(msg) {
    const payload = {
        message_id: msg.id._serialized,
        group_id: msg.from,
        sender_phone: normalizePhone(msg.author || msg.from),
        sender_name: msg._data?.notifyName || 'Unknown',
        message_body: msg.body,
        timestamp: new Date(msg.timestamp * 1000).toISOString(),
    };

    messageBuffer.push({
        ...payload,
        timestamp: msg.timestamp * 1000,
    });

    try {
        const response = await fetch(`${BACKEND_URL}/api/worklogs/ingest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            console.error('Backend ingest failed:', await response.text());
        }
    } catch (err) {
        console.error('Backend unreachable:', err.message);
    }
}

function startWhatsApp() {
    client = new Client({
        authStrategy: new LocalAuth({
            clientId: 'wap-worklog',
            dataPath: process.env.SESSION_PATH || './session',
        }),
        puppeteer: {
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox'],
        },
    });

    client.on('ready', async () => {
        console.log('WhatsApp Ready');
        const chats = await client.getChats();
        const group = chats.find(
            (c) => c.isGroup && c.name.toLowerCase().includes(GROUP_NAME.toLowerCase())
        );
        if (group) {
            targetGroupId = group.id._serialized;
            console.log(`Target group: ${group.name} (${targetGroupId})`);
        } else {
            console.warn(`Group "${GROUP_NAME}" not found. Available groups:`);
            chats.filter((c) => c.isGroup).forEach((c) => console.log(`  - ${c.name}`));
        }
    });

    client.on('message_create', async (msg) => {
        if (!msg.from.endsWith('@g.us')) return;
        if (targetGroupId && msg.from !== targetGroupId) return;
        if (msg.fromMe) return;
        console.log(`[${msg.from}] ${msg.body.substring(0, 80)}`);
        await forwardToBackend(msg);
    });

    client.on('auth_failure', (msg) => console.error('Auth failure:', msg));
    client.on('disconnected', (reason) => console.log('Disconnected:', reason));

    client.initialize();
}

app.get('/health', (req, res) => {
    res.json({ status: 'ok', group: targetGroupId, buffered: messageBuffer.length });
});

app.post('/send', async (req, res) => {
    try {
        const { message, group = true } = req.body;
        if (!client || !message) {
            return res.status(400).json({ error: 'Client not ready or message missing' });
        }
        if (group && targetGroupId) {
            await client.sendMessage(targetGroupId, message);
        } else {
            return res.status(400).json({ error: 'Target group not configured' });
        }
        res.json({ status: 'sent' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/messages', (req, res) => {
    const { start, end } = req.query;
    const startMs = start ? new Date(start).getTime() : 0;
    const endMs = end ? new Date(end).getTime() : Date.now();
    const filtered = messageBuffer.filter(
        (m) => m.timestamp >= startMs && m.timestamp <= endMs
    );
    res.json({ messages: filtered });
});

app.listen(PORT, () => {
    console.log(`WhatsApp Gateway on port ${PORT}`);
    startWhatsApp();
});
