-- ============================================================================
-- CODA2Z - SCHÉMA BASE DE DONNÉES SUPABASE
-- ============================================================================
-- Version: 1.0
-- Description: Schéma complet avec tables, index, RLS et triggers
-- ============================================================================

-- Activer l'extension UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLES
-- ============================================================================

-- Table profiles (extension de auth.users)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    law_firm TEXT,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE profiles IS 'Profils utilisateurs étendus';
COMMENT ON COLUMN profiles.role IS 'Rôle: user ou admin';

-- Table conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Nouvelle conversation',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE conversations IS 'Conversations entre utilisateurs et l''assistant';

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

COMMENT ON TABLE messages IS 'Messages dans les conversations';
COMMENT ON COLUMN messages.sources IS 'Sources juridiques utilisées (JSON)';

-- Table documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL CHECK (file_size > 0),
    file_type TEXT NOT NULL,
    category TEXT CHECK (category IN ('contrat', 'consultation', 'jurisprudence', 'code', 'loi', 'doctrine', 'autre')),
    vector_store_id TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    indexed_at TIMESTAMPTZ
);

COMMENT ON TABLE documents IS 'Documents uploadés par les utilisateurs';
COMMENT ON COLUMN documents.vector_store_id IS 'ID dans ChromaDB';

-- Table usage_logs
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('query', 'upload', 'delete', 'login', 'logout', 'create_conversation')),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE usage_logs IS 'Logs d''audit et analytics';

-- ============================================================================
-- INDEX pour performances
-- ============================================================================

-- Conversations
CREATE INDEX IF NOT EXISTS idx_conversations_user_id
    ON conversations(user_id);

CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
    ON conversations(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_user_archived
    ON conversations(user_id, is_archived);

-- Messages
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON messages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at
    ON messages(created_at);

CREATE INDEX IF NOT EXISTS idx_messages_user_id
    ON messages(user_id);

-- Documents
CREATE INDEX IF NOT EXISTS idx_documents_user_id
    ON documents(user_id);

CREATE INDEX IF NOT EXISTS idx_documents_uploaded_at
    ON documents(uploaded_at DESC);

CREATE INDEX IF NOT EXISTS idx_documents_category
    ON documents(category);

-- Usage logs
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id
    ON usage_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at
    ON usage_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_usage_logs_action
    ON usage_logs(action);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - CRITIQUE pour la sécurité
-- ============================================================================

-- Activer RLS sur toutes les tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- Policies pour PROFILES
-- ----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users view own profile" ON profiles;
CREATE POLICY "Users view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users update own profile" ON profiles;
CREATE POLICY "Users update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users insert own profile" ON profiles;
CREATE POLICY "Users insert own profile" ON profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Policy admin : voir tous les profils
DROP POLICY IF EXISTS "Admins view all profiles" ON profiles;
CREATE POLICY "Admins view all profiles" ON profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ----------------------------------------------------------------------------
-- Policies pour CONVERSATIONS
-- ----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users manage own conversations" ON conversations;
CREATE POLICY "Users manage own conversations" ON conversations
    FOR ALL USING (auth.uid() = user_id);

-- Policy admin
DROP POLICY IF EXISTS "Admins view all conversations" ON conversations;
CREATE POLICY "Admins view all conversations" ON conversations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ----------------------------------------------------------------------------
-- Policies pour MESSAGES
-- ----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users manage own messages" ON messages;
CREATE POLICY "Users manage own messages" ON messages
    FOR ALL USING (auth.uid() = user_id);

-- Policy admin
DROP POLICY IF EXISTS "Admins view all messages" ON messages;
CREATE POLICY "Admins view all messages" ON messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ----------------------------------------------------------------------------
-- Policies pour DOCUMENTS
-- ----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users manage own documents" ON documents;
CREATE POLICY "Users manage own documents" ON documents
    FOR ALL USING (auth.uid() = user_id);

-- Policy admin
DROP POLICY IF EXISTS "Admins view all documents" ON documents;
CREATE POLICY "Admins view all documents" ON documents
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ----------------------------------------------------------------------------
-- Policies pour USAGE_LOGS
-- ----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users view own logs" ON usage_logs;
CREATE POLICY "Users view own logs" ON usage_logs
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users insert own logs" ON usage_logs;
CREATE POLICY "Users insert own logs" ON usage_logs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Policy admin : voir tous les logs
DROP POLICY IF EXISTS "Admins view all logs" ON usage_logs;
CREATE POLICY "Admins view all logs" ON usage_logs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ============================================================================
-- TRIGGERS pour updated_at automatique
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger sur profiles
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger sur conversations
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VUES UTILES (optionnel)
-- ============================================================================

-- Vue : Conversations avec nombre de messages
CREATE OR REPLACE VIEW conversations_with_stats AS
SELECT
    c.*,
    COUNT(m.id) as message_count,
    MAX(m.created_at) as last_message_at
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
GROUP BY c.id;

COMMENT ON VIEW conversations_with_stats IS 'Conversations enrichies avec statistiques';

-- Vue : Statistiques utilisateurs
CREATE OR REPLACE VIEW user_statistics AS
SELECT
    p.id as user_id,
    p.full_name,
    p.law_firm,
    COUNT(DISTINCT c.id) as total_conversations,
    COUNT(DISTINCT m.id) as total_messages,
    COUNT(DISTINCT d.id) as total_documents,
    MAX(ul.created_at) as last_activity
FROM profiles p
LEFT JOIN conversations c ON p.id = c.user_id
LEFT JOIN messages m ON p.id = m.user_id
LEFT JOIN documents d ON p.id = d.user_id
LEFT JOIN usage_logs ul ON p.id = ul.user_id
GROUP BY p.id, p.full_name, p.law_firm;

COMMENT ON VIEW user_statistics IS 'Statistiques globales par utilisateur';

-- ============================================================================
-- FONCTION : Suppression automatique des anciennes conversations
-- ============================================================================

CREATE OR REPLACE FUNCTION delete_old_conversations()
RETURNS void AS $$
BEGIN
    DELETE FROM conversations
    WHERE updated_at < NOW() - INTERVAL '90 days'
    AND is_archived = true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION delete_old_conversations IS 'Supprime les conversations archivées de plus de 90 jours (RGPD)';

-- ============================================================================
-- CRON JOB (nécessite l'extension pg_cron, optionnel)
-- ============================================================================

-- Décommenter si pg_cron est disponible
-- SELECT cron.schedule(
--     'delete-old-conversations',
--     '0 3 * * *',  -- Tous les jours à 3h du matin
--     'SELECT delete_old_conversations();'
-- );

-- ============================================================================
-- GRANTS ET PERMISSIONS
-- ============================================================================

-- Assurer que les utilisateurs authentifiés peuvent accéder aux tables
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- ============================================================================
-- FIN DU SCHÉMA
-- ============================================================================

-- Vérification
SELECT
    'Installation Coda2z terminée !' as message,
    NOW() as timestamp;
