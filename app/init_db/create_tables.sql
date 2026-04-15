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
    Stage INTEGER DEFAULT 1,                          -- Stage number for staged matching (N=1, N=2, etc.)
    IsActive BOOLEAN DEFAULT true,                    -- Soft delete flag
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ModifiedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT FK_Keywords_Type FOREIGN KEY (TypeID) REFERENCES ClassificationTypes(TypeID)
);

CREATE INDEX IX_ClassificationKeywords_TypeID ON ClassificationKeywords(TypeID);
CREATE INDEX IX_ClassificationKeywords_Stage ON ClassificationKeywords(Stage);


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
INSERT INTO ClassificationKeywords (TypeID, ClassificationKeywords, Stage)
SELECT TypeID, 'invoice', 1 FROM ClassificationTypes WHERE TypeName = 'Invoice'
UNION ALL
SELECT TypeID, 'Purchase Order', 1 FROM ClassificationTypes WHERE TypeName = 'Purchase Order'
UNION ALL
SELECT TypeID, 'Diagnostic', 1 FROM ClassificationTypes WHERE TypeName = 'Referral'
UNION ALL
SELECT TypeID, 'Requisition', 1 FROM ClassificationTypes WHERE TypeName = 'Referral'
UNION ALL
SELECT TypeID, 'bosch canada', 2 FROM ClassificationTypes WHERE TypeName = 'Invoice'
UNION ALL
SELECT TypeID, '<< faxcommand : fax monitoring>>', 1 FROM ClassificationTypes WHERE TypeName = 'Fax_Monitoring'
UNION ALL
SELECT TypeID, '<< faxcommand : fax health monitoring >>', 1 FROM ClassificationTypes WHERE TypeName = 'Production_Monitoring';

-- NOTE: ClassificationTypeTrustSystem is auto-populated by trigger TR_ClassificationTypes_InsertTrust
-- When ClassificationTypes rows are inserted, the trigger automatically creates trust records with HitCount=0, MissCount=0
