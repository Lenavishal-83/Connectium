const mongoose = require('mongoose');
const teamMemberSchema = new mongoose.Schema({
  team_id: { type: mongoose.Schema.Types.ObjectId, ref: 'Team', required: true },
  user_id: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  role: { type: String, default: 'member' }
});
module.exports = mongoose.model('TeamMember', teamMemberSchema);