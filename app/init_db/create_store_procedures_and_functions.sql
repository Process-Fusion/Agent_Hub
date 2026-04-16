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
