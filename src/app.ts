import express from 'express';
import cors from 'cors';
import problemRoutes from './routes/problemRoutes';

const app = express();
app.use(cors());
app.use(express.json());

// API cho bài tập
app.use('/api/problems', problemRoutes);

// API cho nộp bài (Để sửa lỗi Failed to fetch ở hình image_002b65)
app.get('/api/submissions', (req, res) => {
    res.json({
        success: true,
        data: [
            { id: 1, problem: "Two Sum", status: "Accepted", time: "2 mins ago" },
            { id: 2, problem: "Merge Arrays", status: "Wrong Answer", time: "1 hour ago" }
        ]
    });
});

export default app;