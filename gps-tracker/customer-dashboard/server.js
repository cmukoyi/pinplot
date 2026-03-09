const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Proxy API requests to backend
app.use('/api', async (req, res) => {
  const backendUrl = process.env.BACKEND_URL || 'http://backend:8000/api/v1';
  const fullUrl = `${backendUrl}${req.url}`;
  
  try {
    const fetch = (await import('node-fetch')).default;
    const response = await fetch(fullUrl, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        ...req.headers
      },
      body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined
    });
    
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    console.error('API proxy error:', error);
    res.status(500).json({ error: 'Failed to reach backend' });
  }
});

app.listen(PORT, () => {
  console.log(`Customer Dashboard running on port ${PORT}`);
});
