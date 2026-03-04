import WebSocket from 'ws';

const ws = new WebSocket('ws://127.0.0.1:8000/v1/ws/openclaw');

ws.on('open', () => {
  console.log('connected');
  ws.close();
});

ws.on('error', (err) => {
  console.error('error:', err);
});
