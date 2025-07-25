import { MongoClient } from "mongodb";

export const db = new MongoClient(process.env?.MONGODB_URL || "");
