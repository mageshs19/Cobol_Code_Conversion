"""
Sheet Mapping schema catalog.

This module owns all Sheet Mapping names, aliases, and model-field mapping.
Parser logic must not hardcode Sheet Mapping column labels.
"""


SHEET_MAPPING_COLUMN_IDMS_TO_DB2_MAPPING = "IDMS to DB2 Mapping"
SHEET_MAPPING_COLUMN_COBOL_RECORD_IDMS = "Cobol Record IDMS"
SHEET_MAPPING_COLUMN_COBOL_ZONE = "Cobol Zone"
SHEET_MAPPING_COLUMN_IDMS_KEY = "IDMS Key"
SHEET_MAPPING_COLUMN_IDMS_PIC_CLAUSE = "IDMS PIC Clause"
SHEET_MAPPING_COLUMN_LENGTH_OF_FIELD_BYTES = "Length of Field Bytes"
SHEET_MAPPING_COLUMN_FIELD_END_POSITION = "Field end position"
SHEET_MAPPING_COLUMN_DB2_KEY = "DB2 Key"
SHEET_MAPPING_COLUMN_NEW_DB2_RECORD = "New DB2 Record"
SHEET_MAPPING_COLUMN_NEW_DB2_FIELD_NAME = "New DB2 Field name"
SHEET_MAPPING_COLUMN_NEW_DB2_DATA_TYPE = "New DB2 Data Type"
SHEET_MAPPING_COLUMN_HOPEX_EXPRESSION_TYPE_REMARK = "Hopex Expression TypeRemark"
SHEET_MAPPING_COLUMN_REMARKS = "Remarks"
SHEET_MAPPING_COLUMN_RELATION = "Relation"
SHEET_MAPPING_COLUMN_REFERENCE_FIELD_NAME_COPYBOOK = "Reference Field Name (CopyBook) "
SHEET_MAPPING_COLUMN_REFERENCE_FIELD_PIC_CLAUSE = "Reference Field PIC Clause"
SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_TABLE = "Cross Application DB2 table"
SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_FIELD_NAME = "Cross Application DB2 Field Name"
SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_DATA_TYPE = "Cross Appln DB2 Data Type"
SHEET_MAPPING_COLUMN_BASETYPE = "Basetype"


SHEET_MAPPING_CANONICAL_COLUMNS = [
    SHEET_MAPPING_COLUMN_IDMS_TO_DB2_MAPPING,
    SHEET_MAPPING_COLUMN_COBOL_RECORD_IDMS,
    SHEET_MAPPING_COLUMN_COBOL_ZONE,
    SHEET_MAPPING_COLUMN_IDMS_KEY,
    SHEET_MAPPING_COLUMN_IDMS_PIC_CLAUSE,
    SHEET_MAPPING_COLUMN_LENGTH_OF_FIELD_BYTES,
    SHEET_MAPPING_COLUMN_FIELD_END_POSITION,
    SHEET_MAPPING_COLUMN_DB2_KEY,
    SHEET_MAPPING_COLUMN_NEW_DB2_RECORD,
    SHEET_MAPPING_COLUMN_NEW_DB2_FIELD_NAME,
    SHEET_MAPPING_COLUMN_NEW_DB2_DATA_TYPE,
    SHEET_MAPPING_COLUMN_HOPEX_EXPRESSION_TYPE_REMARK,
    SHEET_MAPPING_COLUMN_REMARKS,
    SHEET_MAPPING_COLUMN_RELATION,
    SHEET_MAPPING_COLUMN_REFERENCE_FIELD_NAME_COPYBOOK,
    SHEET_MAPPING_COLUMN_REFERENCE_FIELD_PIC_CLAUSE,
    SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_TABLE,
    SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_FIELD_NAME,
    SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_DATA_TYPE,
    SHEET_MAPPING_COLUMN_BASETYPE,
]


SHEET_MAPPING_FIELD_ALIASES = {
    SHEET_MAPPING_COLUMN_COBOL_RECORD_IDMS: [
        "Cobol Record IDMS",
        "COBOL RECORD IDMS",
        "Cobol Record",
        "COBOL Record",
        "IDMS Record",
        "Record IDMS",
        "Cobol Record Name",
        "IDMS to DB2 Mapping",
        "Cobol Recrd IDMS",
        "COBOL RECRD IDMS",
        "Cobol Rec IDMS",
        "COBOL REC IDMS",
        "Cobol Rord IDMS",
        "COBOL RCRD IDMS",
        "Cobol Recrd",
        "COBOL RECRD",
    ],
    SHEET_MAPPING_COLUMN_COBOL_ZONE: [
        "Cobol Zone",
        "COBOL Zone",
        "COBOL ZONE",
        "Cobol Field",
        "COBOL Field",
        "IDMS Field",
        "IDMS COBOL Zone",
        "IDMS COBOL Field",
        "Zone",
    ],
    SHEET_MAPPING_COLUMN_IDMS_KEY: [
        "IDMS Key",
        "IDMS KEY",
        "Key IDMS",
        "IDMS_Key",
    ],
    SHEET_MAPPING_COLUMN_IDMS_PIC_CLAUSE: [
        "IDMS PIC Clause",
        "IDMS PIC",
        "PIC Clause",
        "Picture",
        "PIC",
    ],
    SHEET_MAPPING_COLUMN_LENGTH_OF_FIELD_BYTES: [
        "Length of Field Bytes",
        "Length",
        "Field Length",
        "Length Bytes",
        "Length of Field",
    ],
    SHEET_MAPPING_COLUMN_FIELD_END_POSITION: [
        "Field end position",
        "Field End Position",
        "End Position",
        "Field End",
    ],
    SHEET_MAPPING_COLUMN_DB2_KEY: [
        "DB2 Key",
        "DB2 key",
        "DB2 KEY",
        "Key DB2",
        "DB2_key",
        "DB2_Key",
        "DB2KEY",
    ],
    SHEET_MAPPING_COLUMN_NEW_DB2_RECORD: [
        "New DB2 Record",
        "New DB2 Record ",
        "DB2 Record",
        "DB2 Table",
        "New DB2 Table",
        "Table",
        "DB2_Table",
        "New DB2_Record",
    ],
    SHEET_MAPPING_COLUMN_NEW_DB2_FIELD_NAME: [
        "New DB2 Field name",
        "New DB2 Field Name",
        "New DB2_Field name",
        "New DB2_Field Name",
        "New DB2 Field",
        "New DB2_Field",
        "DB2 Field",
        "DB2 Column",
        "New DB2 Column",
        "Column",
        "DB2_Field",
        "DB2_Column",
    ],
    SHEET_MAPPING_COLUMN_NEW_DB2_DATA_TYPE: [
        "New DB2 Data Type",
        "New DB2 DataType",
        "New DB2_Data Type",
        "DB2 Data Type",
        "DB2 Type",
        "Data Type",
    ],
    SHEET_MAPPING_COLUMN_HOPEX_EXPRESSION_TYPE_REMARK: [
        "Hopex Expression TypeRemark",
        "Hopex Expression Type",
        "Expression Type",
        "Hopex Remark",
    ],
    SHEET_MAPPING_COLUMN_REMARKS: [
        "Remarks",
        "Remark",
        "Comments",
        "Comment",
    ],
    SHEET_MAPPING_COLUMN_RELATION: [
        "Relation",
        "Relationship",
        "Set Relation",
    ],
    SHEET_MAPPING_COLUMN_REFERENCE_FIELD_NAME_COPYBOOK: [
        "Reference Field Name (CopyBook) ",
        "Reference Field Name (CopyBook)",
        "Reference Field Name",
        "CopyBook Field",
        "Copybook Field",
        "Reference Field",
    ],
    SHEET_MAPPING_COLUMN_REFERENCE_FIELD_PIC_CLAUSE: [
        "Reference Field PIC Clause",
        "Reference PIC Clause",
        "Reference PIC",
    ],
    SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_TABLE: [
        "Cross Application DB2 table",
        "Cross Application DB2 Table",
        "Cross App DB2 Table",
        "Cross Application Table",
    ],
    SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_FIELD_NAME: [
        "Cross Application DB2 Field Name",
        "Cross App DB2 Field Name",
        "Cross Application DB2 Field",
        "Cross App DB2 Field",
    ],
    SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_DATA_TYPE: [
        "Cross Appln DB2 Data Type",
        "Cross Application DB2 Data Type",
        "Cross App DB2 Data Type",
    ],
    SHEET_MAPPING_COLUMN_BASETYPE: [
        "Basetype",
        "Base Type",
        "BaseType",
    ],
}


SHEET_MAPPING_MODEL_FIELD_MAP = {
    "cobol_record_idms": SHEET_MAPPING_COLUMN_COBOL_RECORD_IDMS,
    "cobol_zone": SHEET_MAPPING_COLUMN_COBOL_ZONE,
    "idms_key": SHEET_MAPPING_COLUMN_IDMS_KEY,
    "idms_pic_clause": SHEET_MAPPING_COLUMN_IDMS_PIC_CLAUSE,
    "length_of_field_bytes": SHEET_MAPPING_COLUMN_LENGTH_OF_FIELD_BYTES,
    "field_end_position": SHEET_MAPPING_COLUMN_FIELD_END_POSITION,
    "db2_key": SHEET_MAPPING_COLUMN_DB2_KEY,
    "new_db2_record": SHEET_MAPPING_COLUMN_NEW_DB2_RECORD,
    "new_db2_field_name": SHEET_MAPPING_COLUMN_NEW_DB2_FIELD_NAME,
    "new_db2_data_type": SHEET_MAPPING_COLUMN_NEW_DB2_DATA_TYPE,
    "hopex_expression_type_remark": SHEET_MAPPING_COLUMN_HOPEX_EXPRESSION_TYPE_REMARK,
    "remarks": SHEET_MAPPING_COLUMN_REMARKS,
    "relation": SHEET_MAPPING_COLUMN_RELATION,
    "reference_field_name_copybook": SHEET_MAPPING_COLUMN_REFERENCE_FIELD_NAME_COPYBOOK,
    "reference_field_pic_clause": SHEET_MAPPING_COLUMN_REFERENCE_FIELD_PIC_CLAUSE,
    "cross_application_db2_table": SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_TABLE,
    "cross_application_db2_field_name": SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_FIELD_NAME,
    "cross_application_db2_data_type": SHEET_MAPPING_COLUMN_CROSS_APPLICATION_DB2_DATA_TYPE,
    "basetype": SHEET_MAPPING_COLUMN_BASETYPE,
}


SHEET_MAPPING_HEADER_DETECTION_GROUPS = [
    [
        SHEET_MAPPING_COLUMN_COBOL_RECORD_IDMS,
        "Cobol Recrd IDMS",
        "IDMS Record",
    ],
    [
        SHEET_MAPPING_COLUMN_NEW_DB2_RECORD,
        "DB2 Table",
        "DB2 Record",
    ],
    [
        SHEET_MAPPING_COLUMN_NEW_DB2_FIELD_NAME,
        "New DB2_Field name",
        "DB2 Column",
    ],
]