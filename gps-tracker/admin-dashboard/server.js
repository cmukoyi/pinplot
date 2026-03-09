const express = require('express');
const path = require('path');
const app = express();

const PORT = process.env.PORT || 3000;
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

app.use(express.static('public'));
app.use(express.json());

// Serve the admin dashboard
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Proxy API requests
app.use('/api', async (req, res) => {
  try {
    const fetch = (await import('node-fetch')).default;
    const url = `${API_URL}${req.originalUrl.replace('/api', '/api')}`;
    const response = await fetch(url, {
      method: req.method,
      headers: req.headers,
      body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined
    });
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Admin dashboard running on http://0.0.0.0:${PORT}`);
  console.log(`API URL: ${API_URL}`);
});
