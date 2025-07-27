require('dotenv').config();
import express from 'express';
import mongoose from 'mongoose';
import cors from 'cors';
import { projectRouter } from './routes';

const app = express();
const port = process.env.PORT || 3001;

app.use(express.json());
app.use(cors({
    origin: 'http://localhost:3000',
}));


// Router
app.use('/api/project', projectRouter);

mongoose.connect(process.env.MONGODB_URL || '').then(() => {
    console.log('MongoDB connection established!')

}).catch((err) => {
    console.error("MongoDB connection error:", err)
})



app.listen(port, () => {
    console.log(`✅ Server running on http://localhost:${port}`);
});



