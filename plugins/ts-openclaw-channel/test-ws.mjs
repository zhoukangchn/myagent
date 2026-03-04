import WebSocket from 'ws';

const ws = new WebSocket('ws://127.0.0.1:8000/v1/ws/openclaw', {
  headers: { "x-openclaw-id": "openclaw-test" }
});

ws.on('open', () => {
  console.log('connected');
  ws.send(JSON.stringify({ type: 'ping' }));
});

ws.on('message', (data) => {
  console.log('received:', data.toString());
  ws.close();
});

ws.on('error', (err) => {
  console.error('error:', err);
});
