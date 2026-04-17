-- ============================================
-- Document Classification System Tables
-- PostgreSQL Version - Minimal Schema
-- ============================================

-- 1. Classification Types Master Table
-- Central lookup for all document classification types
CREATE TABLE ClassificationTypes (
    TypeID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    TypeName VARCHAR(100) NOT NULL UNIQUE,
    Description VARCHAR(500) NULL,
    IsActive BOOLEAN DEFAULT true,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ModifiedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IX_ClassificationTypes_Name ON ClassificationTypes(TypeName);


-- 2. Classification Keywords Table
-- Stores keywords mapped to document types for multi-stage matching
CREATE TABLE ClassificationKeywords (
    KeywordID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    TypeID INT NOT NULL,
    ClassificationKeywords VARCHAR(500) NOT NULL,
    KeywordType INT NOT NULL DEFAULT 0,
    Source INT NOT NULL DEFAULT 0,
    KeywordHitCount INT NOT NULL DEFAULT 0,
    KeywordMissCount INT NOT NULL DEFAULT 0,
    LastSeenDate TIMESTAMP NULL,
    IsActive BOOLEAN DEFAULT true,                    -- Soft delete flag
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ModifiedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT FK_Keywords_Type FOREIGN KEY (TypeID) REFERENCES ClassificationTypes(TypeID)
);

CREATE INDEX IX_ClassificationKeywords_TypeID ON ClassificationKeywords(TypeID);
CREATE INDEX IX_ClassificationKeywords_KeywordType ON ClassificationKeywords(KeywordType);


-- 3. Classification Type Trust System
-- Tracks HitCount/MissCount for trust-based auto-classification
CREATE TABLE ClassificationTypeTrustSystem (
    TrustID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    TypeID INT NOT NULL UNIQUE,
    HitCount INTEGER DEFAULT 0,
    MissCount INTEGER DEFAULT 0,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ModifiedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT FK_Trust_Type FOREIGN KEY (TypeID) REFERENCES ClassificationTypes(TypeID)
);

CREATE INDEX IX_ClassificationTypeTrustSystem_TypeID ON ClassificationTypeTrustSystem(TypeID);


-- ============================================
-- Function for Auto-Updating Timestamps
-- ============================================

CREATE OR REPLACE FUNCTION update_modified_date()
RETURNS TRIGGER AS $$
BEGIN
    NEW.ModifiedDate = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to auto-insert trust record when new type is added
CREATE OR REPLACE FUNCTION insert_trust_on_new_type()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO ClassificationTypeTrustSystem (TypeID, HitCount, MissCount)
    VALUES (NEW.TypeID, 0, 0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- Triggers for Auto-Updating Timestamps
-- ============================================

CREATE TRIGGER TR_ClassificationTypes_UpdateDate
    BEFORE UPDATE ON ClassificationTypes
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_date();

CREATE TRIGGER TR_ClassificationTypes_InsertTrust
    AFTER INSERT ON ClassificationTypes
    FOR EACH ROW
    EXECUTE FUNCTION insert_trust_on_new_type();

CREATE TRIGGER TR_ClassificationKeywords_UpdateDate
    BEFORE UPDATE ON ClassificationKeywords
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_date();

CREATE TRIGGER TR_ClassificationTypeTrustSystem_UpdateDate
    BEFORE UPDATE ON ClassificationTypeTrustSystem
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_date();


-- ============================================
-- Seed Data
-- ============================================

-- Seed ClassificationTypes
INSERT INTO ClassificationTypes (TypeName, Description) VALUES
('Invoice', 'Financial invoices and billing documents'),
('Purchase Order', 'Purchase orders and procurement documents'),
('Referral', 'Medical referral and requisition documents'),
('Fax_Monitoring', 'Fax monitoring and command documents'),
('Production_Monitoring', 'Production system health monitoring documents');


-- Seed ClassificationKeywords
-- KeywordType: 0=PRIMARY, 1=CONTEXTUAL, 2=ABSENCE, 3=STRUCTURAL, 4=SEMANTIC_ALIAS
-- Source:      0=SEED

-- ── Invoice ──────────────────────────────────────────────────────────────────
INSERT INTO ClassificationKeywords (TypeID, ClassificationKeywords, KeywordType, Source)
SELECT TypeID, kw.keyword, kw.ktype, 0
FROM ClassificationTypes
CROSS JOIN (VALUES
    -- PRIMARY
    ('invoice',                0),
    ('bosch canada',           0),
    -- SEMANTIC_ALIAS
    ('Bill',                   4),
    ('Statement',              4),
    ('Tax Invoice',            4),
    ('Charges',                4),
    ('Payment Due',            4),
    -- CONTEXTUAL
    ('Invoice No.',            1),
    ('Invoice Date',           1),
    ('Due Date',               1),
    ('Bill To',                1),
    ('Subtotal',               1),
    ('Tax Rate',               1),
    ('Amount Due',             1),
    ('Net 30',                 1),
    ('Net 60',                 1),
    ('Remit To',               1),
    -- STRUCTURAL
    ('line items table',       3),
    ('quantity x unit price',  3),
    ('vendor letterhead',      3),
    -- ABSENCE
    ('no line items',          2),
    ('no total amount',        2)
) AS kw(keyword, ktype)
WHERE TypeName = 'Invoice';

-- ── Purchase Order ────────────────────────────────────────────────────────────
INSERT INTO ClassificationKeywords (TypeID, ClassificationKeywords, KeywordType, Source)
SELECT TypeID, kw.keyword, kw.ktype, 0
FROM ClassificationTypes
CROSS JOIN (VALUES
    -- PRIMARY
    ('Purchase Order',                   0),
    -- SEMANTIC_ALIAS
    ('PO#',                              4),
    ('P.O.',                             4),
    ('Order Form',                       4),
    ('Procurement Form',                 4),
    -- CONTEXTUAL
    ('Ship To',                          1),
    ('Delivery Date',                    1),
    ('Requested By',                     1),
    ('Approved By',                      1),
    ('Order Date',                       1),
    ('Requisition Number',               1),
    ('Vendor',                           1),
    ('Supplier',                         1),
    -- STRUCTURAL
    ('authorization signature block',    3),
    ('delivery instructions section',    3),
    -- ABSENCE
    ('no invoice number',                2),
    ('no amount due',                    2),
    ('no remit to',                      2)
) AS kw(keyword, ktype)
WHERE TypeName = 'Purchase Order';

-- ── Referral ──────────────────────────────────────────────────────────────────
INSERT INTO ClassificationKeywords (TypeID, ClassificationKeywords, KeywordType, Source)
SELECT TypeID, kw.keyword, kw.ktype, 0
FROM ClassificationTypes
CROSS JOIN (VALUES
    -- PRIMARY
    ('Diagnostic',              0),
    ('Requisition',             0),
    -- SEMANTIC_ALIAS
    ('Referral Form',           4),
    ('Consultation Request',    4),
    ('Patient Transfer',        4),
    -- CONTEXTUAL
    ('Referring Physician',     1),
    ('Referring Provider',      1),
    ('Date of Birth',           1),
    ('Diagnosis Code',          1),
    ('ICD-10',                  1),
    ('Clinical Information',    1),
    ('Reason for Referral',     1),
    ('Specialist',              1),
    -- STRUCTURAL
    ('clinical notes section',  3),
    ('patient demographics block', 3)
) AS kw(keyword, ktype)
WHERE TypeName = 'Referral';

-- ── Fax_Monitoring ────────────────────────────────────────────────────────────
INSERT INTO ClassificationKeywords (TypeID, ClassificationKeywords, KeywordType, Source)
SELECT TypeID, kw.keyword, kw.ktype, 0
FROM ClassificationTypes
CROSS JOIN (VALUES
    -- PRIMARY
    ('<< faxcommand : fax monitoring>>',  0),
    -- SEMANTIC_ALIAS
    ('Facsimile',                         4),
    ('FAX TRANSMISSION',                  4),
    ('Fax Cover Sheet',                   4),
    -- CONTEXTUAL
    ('Fax Number',                        1),
    ('Number of Pages',                   1),
    ('Date/Time Sent',                    1),
    ('Transmission Report',               1),
    ('OK/ERROR status',                   1),
    -- STRUCTURAL
    ('transmission log table',            3),
    ('fax header strip',                  3)
) AS kw(keyword, ktype)
WHERE TypeName = 'Fax_Monitoring';

-- ── Production_Monitoring ─────────────────────────────────────────────────────
INSERT INTO ClassificationKeywords (TypeID, ClassificationKeywords, KeywordType, Source)
SELECT TypeID, kw.keyword, kw.ktype, 0
FROM ClassificationTypes
CROSS JOIN (VALUES
    -- PRIMARY
    ('<< faxcommand : fax health monitoring >>', 0),
    -- SEMANTIC_ALIAS
    ('Production Report',           4),
    ('Daily Production',            4),
    ('Shift Report',                4),
    ('Output Summary',              4),
    -- CONTEXTUAL
    ('Units Produced',              1),
    ('Batch Number',                1),
    ('Production Line',             1),
    ('Shift Date',                  1),
    ('Downtime',                    1),
    ('Efficiency %',                1),
    ('Defect Rate',                 1),
    -- STRUCTURAL
    ('production metrics table',    3),
    ('shift supervisor signature',  3)
) AS kw(keyword, ktype)
WHERE TypeName = 'Production_Monitoring';

-- NOTE: ClassificationTypeTrustSystem is auto-populated by trigger TR_ClassificationTypes_InsertTrust
-- When ClassificationTypes rows are inserted, the trigger automatically creates trust records with HitCount=0, MissCount=0
