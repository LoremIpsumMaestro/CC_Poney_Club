"""
Script d'initialisation de la base de données Supabase
Crée les tables, index et policies RLS
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import settings
from app.database.supabase_client import get_supabase_client
from app.utils.logger import logger

# SQL pour créer le schéma complet
SCHEMA_SQL = """
-- Activer l'extension UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table profiles (extension de auth.users)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    law_firm TEXT,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Nouvelle conversation',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT FALSE
);

-- Table messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    file_type TEXT NOT NULL,
    category TEXT,
    vector_store_id TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    indexed_at TIMESTAMPTZ
);

-- Table usage_logs
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEX pour performances
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_at ON documents(uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at DESC);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - CRITIQUE pour la sécurité
-- ============================================================================

-- Activer RLS sur toutes les tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- Policies pour profiles
DROP POLICY IF EXISTS "Users view own profile" ON profiles;
CREATE POLICY "Users view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users update own profile" ON profiles;
CREATE POLICY "Users update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users insert own profile" ON profiles;
CREATE POLICY "Users insert own profile" ON profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Policies pour conversations
DROP POLICY IF EXISTS "Users manage own conversations" ON conversations;
CREATE POLICY "Users manage own conversations" ON conversations
    FOR ALL USING (auth.uid() = user_id);

-- Policies pour messages
DROP POLICY IF EXISTS "Users manage own messages" ON messages;
CREATE POLICY "Users manage own messages" ON messages
    FOR ALL USING (auth.uid() = user_id);

-- Policies pour documents
DROP POLICY IF EXISTS "Users manage own documents" ON documents;
CREATE POLICY "Users manage own documents" ON documents
    FOR ALL USING (auth.uid() = user_id);

-- Policies pour usage_logs
DROP POLICY IF EXISTS "Users view own logs" ON usage_logs;
CREATE POLICY "Users view own logs" ON usage_logs
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users insert own logs" ON usage_logs;
CREATE POLICY "Users insert own logs" ON usage_logs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Policies ADMIN (voir tout)
DROP POLICY IF EXISTS "Admins view all profiles" ON profiles;
CREATE POLICY "Admins view all profiles" ON profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

DROP POLICY IF EXISTS "Admins view all conversations" ON conversations;
CREATE POLICY "Admins view all conversations" ON conversations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ============================================================================
-- TRIGGERS pour updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""


def run_sql_script(client, sql: str):
    """
    Exécute un script SQL
    Note: Supabase Python SDK ne supporte pas l'exécution de SQL brut
    Ce script doit être exécuté manuellement dans Supabase Dashboard ou via psql
    """
    logger.warning(
        "⚠️  Le SDK Supabase Python ne supporte pas l'exécution de SQL brut."
    )
    logger.warning("Vous devez exécuter le script manuellement.")
    logger.info("\n" + "=" * 80)
    logger.info("📋 COPIEZ ET EXÉCUTEZ CE SQL DANS SUPABASE DASHBOARD:")
    logger.info("=" * 80 + "\n")
    print(sql)
    logger.info("\n" + "=" * 80)
    logger.info("Instructions:")
    logger.info("1. Allez sur https://supabase.com/dashboard")
    logger.info("2. Sélectionnez votre projet")
    logger.info("3. Allez dans 'SQL Editor'")
    logger.info("4. Créez une nouvelle query")
    logger.info("5. Collez le SQL ci-dessus")
    logger.info("6. Exécutez (RUN)")
    logger.info("=" * 80)


async def init_database():
    """Initialise la base de données"""
    try:
        logger.info("🚀 Initialisation de la base de données Supabase...")

        # Vérifier la configuration
        if not settings.supabase_url or not settings.supabase_key:
            logger.error("❌ SUPABASE_URL et SUPABASE_KEY requis dans .env")
            return False

        # Obtenir le client
        client = get_supabase_client()

        # Afficher le script SQL
        run_sql_script(client, SCHEMA_SQL)

        logger.info("✅ Base de données prête !")
        logger.info(
            "\nAprès avoir exécuté le SQL, créez votre premier utilisateur admin :"
        )
        logger.info("python scripts/create_test_users.py")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(init_database())
