let socket = null;
const listeners = new Set();
let reconnectTimer = null;
let isIntentionalDisconnect = false;

export const connect = (url = 'ws://127.0.0.1:8000/ws') => {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  isIntentionalDisconnect = false;
  socket = new WebSocket(url);

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('Received message type:', data.type);
      listeners.forEach((callback) => callback(data));
    } catch (e) {
      console.error('Error parsing WebSocket message:', e);
    }
  };

  socket.onopen = () => {
    console.log('connected');
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    socket.send("ping");
    listeners.forEach((callback) => callback({ type: 'STATUS_UPDATE', value: 'connected' }));
  };

  socket.onclose = () => {
    console.log('disconnected');
    listeners.forEach((callback) => callback({ type: 'STATUS_UPDATE', value: 'disconnected' }));
    socket = null;
    
    if (!isIntentionalDisconnect) {
      console.log('reconnecting');
      listeners.forEach((callback) => callback({ type: 'STATUS_UPDATE', value: 'reconnecting' }));
      reconnectTimer = setTimeout(() => connect(url), 2000);
    }
  };

  socket.onerror = (error) => {
    console.error('WebSocket error:', error);
    listeners.forEach((callback) => callback({ type: 'STATUS_UPDATE', value: 'error' }));
  };
};

export const disconnect = () => {
  isIntentionalDisconnect = true;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close();
    socket = null;
  }
};

export const listen = (callback) => {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
};
