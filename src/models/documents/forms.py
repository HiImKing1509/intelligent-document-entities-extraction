from enum import Enum

class DocumentForm(str, Enum):
    NW_FORM = "NW-Form"
    NON_NW_FORM = "Non-NW-Form"