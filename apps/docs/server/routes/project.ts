import { BigQuery } from "@google-cloud/bigquery";
import { Router, Request, Response } from "express";
import { ProjectDownloadModel } from "../models";
import { parser } from 'stream-json';
import { streamArray } from 'stream-json/streamers/StreamArray';
import path from 'path';
import pLimit from 'p-limit';
import fs from 'fs';
import { formatBytes } from "../utils";

const bigquery = new BigQuery();

const router = Router();



router.get('/search', async (req: Request, res: Response) => {
    try {
        const { pkg } = req.query
        if (!pkg) {
            res.status(400).json({ error: 'Missing package name' });
            return
        }
        const data = await ProjectDownloadModel.find({
            project: { $regex: `^${pkg.toString()}`, $options: 'i' }
        }).limit(10).exec();
        res.json(data);

    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch data' });
    }
});


router.post('/', async (req: Request, res: Response) => {
    const filePath = path.join(__dirname, 'config', 'pkg.json');
    const jsonStream = fs.createReadStream(filePath).pipe(parser()).pipe(streamArray());

    const limit = pLimit(10); // Max 10 concurrent DB writes
    const updateTasks: Promise<any>[] = [];
    let processedCount = 0;

    jsonStream.on('data', ({ value }) => {
        const task = limit(async () => {
            try {
                await ProjectDownloadModel.findOneAndUpdate(
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


router.get('/size', async (req: Request, res: Response) => {
    try {
        const ONE_TERABYTE = 1_000_000_000_000;

        const projectQuery = /*sql*/`          
            SELECT COUNT(*) AS count
            FROM (
                SELECT name
                FROM bigquery-public-data.pypi.distribution_metadata
                GROUP BY name
                HAVING COUNT(*) >= 2
            );
        `;
        const releasesQuery = /*sql*/`          
            SELECT COUNT(DISTINCT CONCAT(name, '==', version)) AS count
            FROM bigquery-public-data.pypi.distribution_metadata
            WHERE name IN (
            SELECT name
            FROM bigquery-public-data.pypi.distribution_metadata
            GROUP BY name
            HAVING COUNT(*) >= 2
            )
        `;

        // const query = /*sql*/`          
        //     SELECT COUNT(*) AS total_releases_in_multi_release_projects
        //     FROM bigquery-public-data.pypi.distribution_metadata
        //     WHERE name IN (
        //     SELECT name
        //     FROM bigquery-public-data.pypi.distribution_metadata
        //     GROUP BY name
        //     HAVING COUNT(*) >= 2
        //     )
        //     -- AND python_version != 'source' -- Optional: ignore source if counting wheels only
        //     AND has_signature = FALSE  
        // `;
        const query = /*sql*/`          
            SELECT *
            FROM bigquery-public-data.pypi.distribution_metadata
            LIMIT 1
            -- WHERE table_name = 'distribution_metadata';

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
                estimatedBytes: formatBytes(Number(bytes)),
            });
        }


        const [data] = await bigquery.query(query);
        res.json({
            size: formatBytes(Number(bytes)),
            data
            // releases: Number(data[0].count).toLocaleString('en-US'),
        });

    } catch (err: any) {
        console.error("BigQuery Error:", err);
        res.status(500).json({ err: err.toString() });
    }
});



export default router
