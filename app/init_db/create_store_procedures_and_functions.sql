-- ============================================
-- Stored Functions
-- PostgreSQL Version
-- ============================================

-- Returns all active classification types
CREATE OR REPLACE FUNCTION get_classification_types()
RETURNS TABLE (
    TypeName    VARCHAR(100),
    Description VARCHAR(500)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ct.TypeName,
        ct.Description
    FROM ClassificationTypes ct
    WHERE ct.IsActive = true
    ORDER BY ct.TypeName;
END;
$$;


-- ============================================
-- Returns all active keywords grouped with their type name
-- ============================================
CREATE OR REPLACE FUNCTION get_all_keywords()
RETURNS TABLE (
    TypeName                VARCHAR(100),
    KeywordID               INT,
    TypeID                  INT,
    ClassificationKeywords  VARCHAR(500),
    KeywordType             INT,
    Source                  INT,
    KeywordHitCount         INT,
    KeywordMissCount        INT,
    LastSeenDate            TIMESTAMP,
    IsActive                BOOLEAN,
    CreatedDate             TIMESTAMP,
    ModifiedDate            TIMESTAMP
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.TypeName,
        k.KeywordID,
        k.TypeID,
        k.ClassificationKeywords,
        k.KeywordType,
        k.Source,
        k.KeywordHitCount,
        k.KeywordMissCount,
        k.LastSeenDate,
        k.IsActive,
        k.CreatedDate,
        k.ModifiedDate
    FROM ClassificationKeywords k
    JOIN ClassificationTypes t ON k.TypeID = t.TypeID
    WHERE k.IsActive = true AND t.IsActive = true
    ORDER BY t.TypeName, k.KeywordID ASC;
END;
$$;


-- ============================================
-- Returns all active keywords for a specific type
-- ============================================
CREATE OR REPLACE FUNCTION get_keywords_by_type(
    p_TypeName VARCHAR(100)
)
RETURNS TABLE (
    KeywordID               INT,
    TypeID                  INT,
    ClassificationKeywords  VARCHAR(500),
    KeywordType             INT,
    Source                  INT,
    KeywordHitCount         INT,
    KeywordMissCount        INT,
    LastSeenDate            TIMESTAMP,
    IsActive                BOOLEAN,
    CreatedDate             TIMESTAMP,
    ModifiedDate            TIMESTAMP
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        k.KeywordID,
        k.TypeID,
        k.ClassificationKeywords,
        k.KeywordType,
        k.Source,
        k.KeywordHitCount,
        k.KeywordMissCount,
        k.LastSeenDate,
        k.IsActive,
        k.CreatedDate,
        k.ModifiedDate
    FROM ClassificationKeywords k
    JOIN ClassificationTypes t ON k.TypeID = t.TypeID
    WHERE t.TypeName = p_TypeName
      AND k.IsActive = true
      AND t.IsActive = true
    ORDER BY k.KeywordID ASC;
END;
$$;


-- ============================================
-- Returns top-K active keywords for a type,
-- ranked by signal strength (HitCount - MissCount DESC).
-- Used for selective keyword loading in the agent system prompt.
-- ============================================
CREATE OR REPLACE FUNCTION get_k_keywords_by_type(
    p_TypeName VARCHAR(100),
    p_K        INT DEFAULT 100
)
RETURNS TABLE (
    KeywordID               INT,
    TypeID                  INT,
    ClassificationKeywords  VARCHAR(500),
    KeywordType             INT,
    Source                  INT,
    KeywordHitCount         INT,
    KeywordMissCount        INT,
    LastSeenDate            TIMESTAMP,
    IsActive                BOOLEAN,
    CreatedDate             TIMESTAMP,
    ModifiedDate            TIMESTAMP
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        k.KeywordID,
        k.TypeID,
        k.ClassificationKeywords,
        k.KeywordType,
        k.Source,
        k.KeywordHitCount,
        k.KeywordMissCount,
        k.LastSeenDate,
        k.IsActive,
        k.CreatedDate,
        k.ModifiedDate
    FROM ClassificationKeywords k
    JOIN ClassificationTypes t ON k.TypeID = t.TypeID
    WHERE t.TypeName = p_TypeName
      AND k.IsActive = true
      AND t.IsActive = true
    ORDER BY (k.KeywordHitCount - k.KeywordMissCount) DESC, k.KeywordID ASC
    LIMIT p_K;
END;
$$;


-- ============================================
-- Increments HitCount and updates LastSeenDate for a keyword.
-- Call after a keyword contributed to a correct classification.
-- ============================================
CREATE OR REPLACE PROCEDURE update_keyword_hit(
    p_KeywordID INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE ClassificationKeywords
    SET KeywordHitCount = KeywordHitCount + 1,
        LastSeenDate    = CURRENT_TIMESTAMP
    WHERE KeywordID = p_KeywordID
      AND IsActive = true;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Keyword with ID % not found or inactive', p_KeywordID;
    END IF;
END;
$$;


-- ============================================
-- Increments MissCount and updates LastSeenDate for a keyword.
-- Call after a keyword contributed to a wrong classification.
-- ============================================
CREATE OR REPLACE PROCEDURE update_keyword_miss(
    p_KeywordID INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE ClassificationKeywords
    SET KeywordMissCount = KeywordMissCount + 1,
        LastSeenDate     = CURRENT_TIMESTAMP
    WHERE KeywordID = p_KeywordID
      AND IsActive = true;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Keyword with ID % not found or inactive', p_KeywordID;
    END IF;
END;
$$;


-- ============================================
-- Soft-deactivates keywords whose LastSeenDate is older than 2 months.
-- Skips SEED keywords that have never been seen (LastSeenDate IS NULL).
-- Intended to be called weekly by an Azure scheduler via the API.
-- Returns the number of keywords deactivated.
-- ============================================
CREATE OR REPLACE FUNCTION deactivate_stale_keywords()
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE ClassificationKeywords
    SET IsActive = false
    WHERE IsActive = true
      AND LastSeenDate IS NOT NULL
      AND LastSeenDate < CURRENT_TIMESTAMP - INTERVAL '2 months';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;


-- ============================================
-- Inserts a new classification type
-- ============================================
CREATE OR REPLACE PROCEDURE insert_classification_type(
    p_TypeName    VARCHAR(100),
    p_Description VARCHAR(500) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO ClassificationTypes (TypeName, Description)
    VALUES (p_TypeName, p_Description);
END;
$$;


-- ============================================
-- Inserts a new classification keyword
-- ============================================
-- KeywordType values:
--   0 = PRIMARY        (core identifier, strong signal)
--   1 = CONTEXTUAL     (must co-exist with primary to validate)
--   2 = ABSENCE        (its absence disproves the type)
--   3 = STRUCTURAL     (document layout fingerprint)
--   4 = SEMANTIC_ALIAS (synonym / semantic equivalent)
--
-- Source values:
--   0 = SEED             (hardcoded at init, high trust)
--   1 = AGENT_EXTRACTED  (LLM-learned, lower trust)
--   2 = HUMAN_CORRECTED  (from a human correction event, high trust)
-- ============================================
CREATE OR REPLACE PROCEDURE insert_classification_keyword(
    p_TypeID                INT,
    p_ClassificationKeywords  VARCHAR(500),
    p_KeywordType             INT DEFAULT 0,
    p_Source                  INT DEFAULT 0
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_TypeID IS NULL THEN
        RAISE EXCEPTION 'Classification type "%" not found or inactive', p_TypeName;
    END IF;

    -- Skip if an identical active keyword already exists for this type
    IF EXISTS (
        SELECT 1 FROM ClassificationKeywords
        WHERE TypeID = p_TypeID
          AND ClassificationKeywords = p_ClassificationKeywords
          AND IsActive = true
    ) THEN
        RETURN;
    END IF;

    INSERT INTO ClassificationKeywords (
        TypeID,
        ClassificationKeywords,
        KeywordType,
        Source
    )
    VALUES (
        p_TypeID,
        p_ClassificationKeywords,
        p_KeywordType,
        p_Source
    );
END;
$$;


-- ============================================
-- Soft-deletes a keyword by its text value
-- (scoped to a TypeID to avoid cross-type removal)
-- ============================================
CREATE OR REPLACE PROCEDURE delete_classification_keyword_by_value(
    p_TypeID                 INT,
    p_ClassificationKeyword VARCHAR(500)
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE ClassificationKeywords
    SET IsActive = false
    WHERE TypeID = p_TypeID
      AND ClassificationKeywords = p_ClassificationKeyword
      AND IsActive = true;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Keyword "%" not found or already inactive for TypeID %', p_ClassificationKeywords, p_TypeID;
    END IF;
END;
$$;


-- ============================================
-- Soft-deletes a keyword by its primary key
-- ============================================
CREATE OR REPLACE PROCEDURE delete_classification_keyword_by_id(
    p_KeywordID INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE ClassificationKeywords
    SET IsActive = false
    WHERE KeywordID = p_KeywordID
      AND IsActive = true;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Keyword with ID % not found or already inactive', p_KeywordID;
    END IF;
END;
$$;
