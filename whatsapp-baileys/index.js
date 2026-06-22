const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason
} = require('@whiskeysockets/baileys');

async function start() {

    const { state, saveCreds } =
        await useMultiFileAuthState('auth_info');

    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', ({ connection, lastDisconnect }) => {

        if (connection === 'open') {
            console.log('WhatsApp Connected');
        }

        if (connection === 'close') {

            const shouldReconnect =
                lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;

            console.log('Disconnected');

            if (shouldReconnect) {
                start();
            }
        }
    });
}

start();