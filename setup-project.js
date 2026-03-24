 
const fs = require('fs');
const path = require('path');

const projectStructure = {
  // === CONFIG & ROOT ===
  'package.json': `{
  "name": "codementor-backend-core",
  "version": "1.0.0",
  "scripts": {
    "dev": "ts-node-dev src/index.ts"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/cors": "^2.8.17",
    "ts-node-dev": "^2.0.0",
    "typescript": "^5.3.3"
  }
}`,
  'tsconfig.json': `{
  "compilerOptions": {
    "target": "ES6",
    "module": "CommonJS",
    "rootDir": "./src",
    "outDir": "./dist",
    "strict": true,
    "esModuleInterop": true
  }
}`,

  // === DOCS ===
  'docs/progress.md': `# BACKEND IMPLEMENTATION STATUS\n\n**Completed modules:**\n- Problem system (Controller, Service, Route)\n- Execution system skeleton\n- Temporary Dashboard\n\n**Pending:**\n- MongoDB Integration\n- AI Assistant Module\n- Docker Sandbox Execution`,
  'docs/api.md': `# API DOCUMENTATION\n\n## Problems\n- **GET /api/problems**: Lấy danh sách bài tập.\n\n## Execution\n- **POST /api/execution/run**: Gửi code để chấm (Mock data).`,
  'docs/backend-tree.md': `# ARCHITECTURE\nClient -> Routes -> Controllers -> Services -> Execution Engine -> DB`,

  // === BACKEND CORE ===
  'src/index.ts': `import app from './app';\n\nconst PORT = 5000;\napp.listen(PORT, () => {\n  console.log(\`Backend Core is running on http://localhost:\${PORT}\`);\n});`,
  'src/app.ts': `import express from 'express';\nimport cors from 'cors';\nimport problemRoutes from './routes/problemRoutes';\n\nconst app = express();\napp.use(cors());\napp.use(express.json());\n\napp.use('/api/problems', problemRoutes);\n\nexport default app;`,
  
  // Routes
  'src/routes/problemRoutes.ts': `import express from 'express';\nimport { getProblems } from '../controllers/problemController';\n\nconst router = express.Router();\nrouter.get('/', getProblems);\n\nexport default router;`,
  
  // Controllers
  'src/controllers/problemController.ts': `import { Request, Response } from 'express';\nimport * as problemService from '../services/problemService';\n\nexport const getProblems = async (req: Request, res: Response) => {\n  const data = await problemService.getAllProblems();\n  res.json({ success: true, data });\n};`,
  
  // Services
  'src/services/problemService.ts': `export const getAllProblems = async () => {\n  return [\n    { id: 1, title: 'Two Sum', difficulty: 'Easy', status: 'mock' },\n    { id: 2, title: 'Add Two Numbers', difficulty: 'Medium', status: 'mock' }\n  ];\n};`,

  // Execution Engine (Skeleton)
  'src/execution-engine/codeRunner.ts': `export const executeCode = async (code: string, lang: string) => {\n  return { status: 'success', output: 'Hello World' };\n};`,
  
  // === TEMPORARY DASHBOARD ===
  'dashboard-demo/index.html': `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Temporary Dashboard Demo</title>
    <style>body { font-family: sans-serif; padding: 20px; }</style>
</head>
<body>
    <h1>Data Visualization (Temporary)</h1>
    <div id="content">Đang fetch API từ Backend...</div>
    <script>
        fetch('http://localhost:5000/api/problems')
            .then(res => res.json())
            .then(res => {
                document.getElementById('content').innerHTML = 
                    '<pre>' + JSON.stringify(res.data, null, 2) + '</pre>';
            })
            .catch(err => document.getElementById('content').innerHTML = 'Lỗi kết nối Backend');
    </script>
</body>
</html>`
};

// Hàm tạo file và thư mục
Object.keys(projectStructure).forEach(filePath => {
  const fullPath = path.join(__dirname, filePath);
  const dirName = path.dirname(fullPath);

  if (!fs.existsSync(dirName)) {
    fs.mkdirSync(dirName, { recursive: true });
  }

  fs.writeFileSync(fullPath, projectStructure[filePath], 'utf8');
  console.log(`Created: ${filePath}`);
});

console.log('\\n✅ Đã tạo xong toàn bộ project skeleton!');
console.log('👉 Chạy "npm install" để cài thư viện.');
console.log('👉 Chạy "npm run dev" để bật server backend.');