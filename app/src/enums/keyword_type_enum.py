from enum import Enum

class KeywordTypeEnum(Enum):
  PRIMARY = 0, # Core identifier, strong signal
  CONTEXTUAL = 1, # Must co-exist with primary to validate
  ABSENCE = 2, # Its absence disproves the type
  STRUCTURAL = 3, # Document layout fingerprint
  SEMANTIC_ALIAS = 4 # Synonym/semantic equivalent

