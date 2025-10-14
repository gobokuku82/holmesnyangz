-- Migration: Create Long-term Memory tables
-- Date: 2025-10-14
-- Description: Create conversation_memories, user_preferences, entity_memories tables

-- ==============================
-- 1. conversation_memories table
-- ==============================
CREATE TABLE IF NOT EXISTS conversation_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    response_summary TEXT NOT NULL,
    relevance VARCHAR(20) NOT NULL,
    intent_detected VARCHAR(50),
    entities_mentioned JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    conversation_metadata JSONB
);

-- Indexes for conversation_memories
CREATE INDEX IF NOT EXISTS idx_conv_mem_user_created ON conversation_memories(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conv_mem_relevance ON conversation_memories(relevance);

-- ==============================
-- 2. user_preferences table
-- ==============================
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================
-- 3. entity_memories table
-- ==============================
CREATE TABLE IF NOT EXISTS entity_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    entity_name VARCHAR(200),
    mention_count INTEGER DEFAULT 1,
    first_mentioned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_mentioned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    entity_context JSONB
);

-- Indexes for entity_memories
CREATE INDEX IF NOT EXISTS idx_entity_mem_user_type ON entity_memories(user_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_mem_entity ON entity_memories(entity_type, entity_id);

-- Unique constraint to prevent duplicate entity tracking
ALTER TABLE entity_memories
ADD CONSTRAINT uq_user_entity UNIQUE (user_id, entity_type, entity_id);
