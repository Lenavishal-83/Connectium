const mongoose = require('mongoose');
const todoSchema = new mongoose.Schema({
  user_id: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  title: { type: String, required: true },
  description: String,
  due_date: Date,
  completed: { type: Boolean, default: false },
  tags: [String]
});
module.exports = mongoose.model('ToDo', todoSchema);