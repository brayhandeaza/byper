import mongoose, { Schema } from "mongoose";


const MainSchema = new Schema({
    project: String,
})

const MainModel = mongoose.model('main', MainSchema);


export default MainModel
