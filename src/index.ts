import app from './app';

const PORT = 5000;
app.listen(PORT, () => {
  console.log(`Backend Core is running on http://localhost:${PORT}`);
});