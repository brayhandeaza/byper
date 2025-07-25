require('dotenv').config();
import express, { Request, Response } from 'express';
import { BigQuery } from '@google-cloud/bigquery';
import mongoose, { Schema } from 'mongoose';
import fs from 'fs';
import cors from 'cors';

import { parser } from 'stream-json';
import { streamArray } from 'stream-json/streamers/StreamArray';
import path from 'path';
import pLimit from 'p-limit';

const app = express();
const port = process.env.PORT || 3001;
const bigquery = new BigQuery();

app.use(cors({
    origin: 'http://localhost:3000',
}));
app.use(express.json());

mongoose.connect(process.env.MONGODB_URL || '').then(() => {
    console.log('MongoDB connection established!')

}).catch((err) => {
    console.error("MongoDB connection error:", err)
})

// const pksData = {
//     name,
//     version,
//     yanked,
//     license,
//     classifiers,
//     releases: releasesSorted,
//     release: releasesSorted[0],
//     summary,
//     requires_python,
//     project_urls,
//     description,
//     vulnerabilities,
//     repository,
//     documentation,
//     dependencies: provides_extra
// }

const ProjectDownloadSchema = new Schema({
    project: String,
    count: Number
})

const ProjectDownload = mongoose.model('project_downloads', ProjectDownloadSchema);

function escapeRegExp(string: string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

app.get('/search', async (req: Request, res: Response) => {
    try {
        const { pkg } = req.query
        if (!pkg) {
            res.status(400).json({ error: 'Missing package name' });
            return
        }
        const data = await ProjectDownload.find({
            project: { $regex: `^${pkg.toString()}`, $options: 'i' }
        }).limit(10).exec();
        res.json(data);

    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch data' });
    }
});


app.get('/', async (req: Request, res: Response) => {
    const filePath = path.join(__dirname, 'config', 'pkg.json');

    const jsonStream = fs.createReadStream(filePath)
        .pipe(parser())
        .pipe(streamArray());

    const limit = pLimit(10); // Max 10 concurrent DB writes
    const updateTasks: Promise<any>[] = [];
    let processedCount = 0;

    jsonStream.on('data', ({ value }) => {
        const task = limit(async () => {
            try {
                await ProjectDownload.findOneAndUpdate(
                    { project: value.package_name },
                    { $inc: { count: value.download_count } },
                    { upsert: true, new: true }
                );
                processedCount++;
                if (processedCount % 100 === 0) {
                    console.log(`Processed ${processedCount} packages`);
                }
            } catch (err) {
                console.error('MongoDB update error:', err);
            }
        });
        updateTasks.push(task);
    });

    jsonStream.on('end', async () => {
        await Promise.all(updateTasks); // wait for all throttled updates to finish
        res.send({
            success: true,
            message: `✅ Finished processing ${processedCount} packages`
        });
    });

    jsonStream.on('error', (err) => {
        console.error('Stream error:', err);
        res.status(500).send({
            success: false,
            error: '❌ Failed to stream and update JSON data'
        });
    });
});



// Auth setup

app.get('/ping', async (req: Request, res: Response) => {
    try {

        const [data] = await bigquery.query(/*sql*/`
            SELECT file.project AS package_name, COUNT(*) AS download_count
            FROM bigquery-public-data.pypi.file_downloads AS file
            WHERE DATE(file.timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
            GROUP BY package_name
            ORDER BY download_count DESC
            LIMIT 10
        `);

        res.json(data);
    } catch (err) {
        console.error("BigQuery Error:", err);
        res.status(500).json({ error: 'Failed to fetch data' });
    }
});


function formatBytes(bytes: number): string {
    const gb = bytes / (1024 ** 3);
    const mb = bytes / (1024 ** 2);

    if (gb >= 1) return `${gb.toFixed(2)} GB`;
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    return `${bytes} B`;
}

app.get('/size', async (req: Request, res: Response) => {
    try {
        const ONE_TERABYTE = 1_000_000_000_000;
        // const query = /*sql*/`
        //     SELECT file.project AS package_name, COUNT(*) AS download_count
        //     FROM bigquery-public-data.pypi.file_downloads AS file
        //     WHERE DATE(file.timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        //     GROUP BY package_name
        //     ORDER BY download_count DESC
        //     LIMIT 10
        // `;

        const query = /*sql*/`          
            SELECT 
            project,
            COUNT(*) AS count
            FROM bigquery-public-data.pypi.file_downloads
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
            GROUP BY project
            ORDER BY date ASC;
        `;

        const [job] = await bigquery.createQueryJob({
            query,
            dryRun: true,
            useQueryCache: false,
        })

        const bytes = parseInt(job.metadata?.statistics.totalBytesProcessed || '0');
        if (bytes > ONE_TERABYTE) {
            return res.status(400).json({
                message: 'Query too large. Estimated cost exceeds 1 TB free tier limit.',
                estimatedBytes: bytes,
            });
        }


        const [data] = await bigquery.query(query);

        // save data into pkg file
        fs.writeFileSync('pkg.json', JSON.stringify(data, null, 2));

        res.json({
            size: formatBytes(Number(bytes)),
            data
        });

    } catch (err) {
        console.error("BigQuery Error:", err);
        res.status(500).json({ error: 'Failed to fetch data' });
    }
});

app.listen(port, () => {
    console.log(`✅ Server running on http://localhost:${port}`);
});



