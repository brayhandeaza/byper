import mongoose, { Schema } from "mongoose";


const PackagesSchema = new Schema({
    project: String,
    downloads: Number
})

const PackagesModel = mongoose.model('packages', PackagesSchema);


export default PackagesModel

