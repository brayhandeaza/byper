import mongoose, { Schema } from "mongoose";


const ProjectDownloadSchema = new Schema({
    project: String,
    count: Number
})

const ProjectDownloadModel = mongoose.model('project_downloads', ProjectDownloadSchema);


export default ProjectDownloadModel
