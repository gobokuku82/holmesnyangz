-- Add missing columns to chat_sessions table
ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS last_message TEXT,
ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 0;