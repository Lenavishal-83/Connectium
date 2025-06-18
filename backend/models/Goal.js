const mongoose = require('mongoose');
const goalSchema = new mongoose.Schema({
  team_id: { type: mongoose.Schema.Types.ObjectId, ref: 'Team', required: true },
  title: { type: String, required: true },
  description: String,
  due_date: Date,
  completed: { type: Boolean, default: false },
  tags: [String]
});
module.exports = mongoose.model('Goal', goalSchema);