require('dotenv').config();
import express from 'express';
import mongoose from 'mongoose';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { projectRouter } from './routes';
import { parser } from 'stream-json';
import { streamArray } from 'stream-json/streamers/StreamArray';
import { Request, Response } from "express";
import { PackagesModel } from './models';

const app = express();
const port = process.env.PORT || 3001;

app.use(express.json());
app.use(cors({
    origin: 'http://localhost:3000',
}));


app.get('/test', async (req: Request, res: Response) => {
    try {
        const filePath = path.join(__dirname, 'config', 'pkg.json');
        const jsonStream = fs.createReadStream(filePath).pipe(parser()).pipe(streamArray());
        const projects: any[] = [];


        jsonStream.on('data', ({ value }) => {
            projects.push({
                project: value.package_name,
                downloads: value.download_count
            });
        });


        jsonStream.on('end', async () => {
            fs.writeFileSync(path.join(__dirname, 'config', 'projects.json'), JSON.stringify(projects));
            res.json({
                success: true,
                message: `✅ Finished processing packages`
            });
        });

    } catch (error: any) {
        res.status(500).json({ error: 'Failed to fetch data', err: error.message });
    }
});


app.get('/', async (req: Request, res: Response) => {
    const filePath = path.join(__dirname, 'config', 'projects.json');
    const jsonStream = fs.createReadStream(filePath).pipe(parser()).pipe(streamArray());
    const updateTasks: Promise<any>[] = [];

    let i = 0
    jsonStream.on('data', async ({ value }) => {
        try {
            i++
            await PackagesModel.findOneAndUpdate(
                { project: value.project },
                { $inc: { downloads: value.downloads } },
                { upsert: true, new: true }

            ).then(() => {
                console.log(`Updated or Created (${i}):`, value.project);
            })

        } catch (err) {
            console.error('MongoDB update error:', err);
        }
    });

    jsonStream.on('end', async () => {
        await Promise.all(updateTasks); // wait for all throttled updates to finish
        res.send({
            success: true,
            message: `✅ Finished processing packages`
        });
    });

    jsonStream.on('error', (err) => {
        res.status(500).send({
            success: false,
            error: '❌ Failed to stream and update JSON data'
        });
    });
});


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



