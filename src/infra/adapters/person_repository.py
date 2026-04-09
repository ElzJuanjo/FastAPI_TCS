import re
from src.infra.config.database import get_mssql_connection
from src.domain.repositories import PersonRepository


def sanitize_nit(nit: str) -> str:
    if not nit:
        return ""
    return re.sub(r"[^A-Za-z0-9\-_]", "", nit)


def parse_full_name(full_name):
    if not full_name:
        return None, None
    parts = full_name.strip().split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else None


# =========================
# Normalización estudiantes
# =========================
STUDENT_ID_TYPE_MAP = {
    None: "TI",
    "NUIP": "TI",
    "TI": "TI",
    "RC": "RC",
    "CC": "CC",
    "CN": "CC",
    "CE": "CE",
    "CR": "PE",
    "PC": "PE",
    "PE": "PE",
    "P": "P",
    "PP": "P",
    "PA": "P",
}


def normalize_student_id_type(value):
    return STUDENT_ID_TYPE_MAP.get(value, "TI")


# =========================
# Normalización empleados
# =========================
EMPLOYEE_ID_TYPE_MAP = {
    "C": "CC",
    "N": "CC",
    "O": "CC",
    "E": "CE",
    "T": "TI",
    "P": "P",
    "A": "P",
}


def normalize_employee_id_type(value):
    return EMPLOYEE_ID_TYPE_MAP.get(value, "CC")


# =========================
# Búsquedas
# =========================
def _search_employees(cursor, nit):
    nit = sanitize_nit(nit)
    if not nit:
        return None

    query = f"""
        SELECT *
        FROM OPENQUERY(CSERPDB,
        'SELECT
            f200_id_tipo_ident,
            f200_nit,
            f200_nombres,
            f200_apellido1,
            f200_apellido2,
            f200_fecha_nacimiento,
            f015_celular,
            f015_email
         FROM t200_mm_terceros t
              INNER JOIN t015_mm_contactos co
                  ON co.f015_rowid = t.f200_rowid_contacto
              LEFT JOIN w0550_contratos tc
                  ON tc.c0550_rowid_tercero = t.f200_rowid
         WHERE f200_ind_empleado = 1
           AND f200_ind_estado = 1
           AND c0550_fecha_retiro IS NULL
           AND f200_id_cia = 1
           AND f200_ind_tipo_tercero = 1
           AND f200_nit = ''{nit}''
        ')
    """

    cursor.execute(query)
    row = cursor.fetchone()
    if not row:
        return None

    normalized_type = normalize_employee_id_type(row.f200_id_tipo_ident)
    first_name, middle_name = parse_full_name(row.f200_nombres)

    family_id = _get_family_id_for_employee(cursor, row.f200_nit)

    return {
        "nit_type": normalized_type,
        "nit": row.f200_nit,
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name_1": row.f200_apellido1,
        "last_name_2": row.f200_apellido2,
        "birth_date": (
            row.f200_fecha_nacimiento.date().isoformat()
            if row.f200_fecha_nacimiento
            else None
        ),
        "cell_phone": row.f015_celular,
        "email": row.f015_email,
        "person_source": "EMPLOYEE",
        "family_id": family_id,
        "siesa_id": row.f200_nit,
    }


def _search_students(cursor, nit):
    nit = sanitize_nit(nit)
    if not nit:
        return None

    query = """
        SELECT
            first_name,
            middle_name,
            last_name,
            date_of_birth,
            phone,
            id_number,
            id_number_type,
            family_id,
            siesa_tercero_id
        FROM students
        WHERE id_number = ?
    """

    cursor.execute(query, nit)
    row = cursor.fetchone()
    if not row:
        return None

    siesa_id = row.id_number

    if row.siesa_tercero_id and row.siesa_tercero_id != 0:
        fam_query = """
            SELECT 1
            FROM family_info
            WHERE father_id = ? OR mother_id = ?
        """
        cursor.execute(fam_query, row.siesa_tercero_id, row.siesa_tercero_id)
        if cursor.fetchone():
            siesa_id = row.siesa_tercero_id

    last_name_1, last_name_2 = parse_full_name(row.last_name)
    normalized_type = normalize_student_id_type(row.id_number_type)

    return {
        "nit_type": normalized_type,
        "nit": row.id_number,
        "first_name": row.first_name,
        "middle_name": row.middle_name,
        "last_name_1": last_name_1,
        "last_name_2": last_name_2,
        "birth_date": str(row.date_of_birth) if row.date_of_birth else None,
        "cell_phone": row.phone,
        "email": None,
        "person_source": "STUDENT",
        "family_id": row.family_id,
        "siesa_id": siesa_id,
    }


def _search_family_info(cursor, nit):
    nit = sanitize_nit(nit)
    if not nit:
        return None

    query = """
        SELECT
            father,
            father_last_name,
            father_email,
            father_cell_phone,
            father_id,
            mother,
            mother_last_name,
            mother_email,
            mother_cell_phone,
            mother_id,
            employee,
            siesa_id,
            id_family
        FROM family_info
        WHERE father_id = ? OR mother_id = ?
    """

    cursor.execute(query, nit, nit)
    row = cursor.fetchone()
    if not row:
        return None

    person_source = "EMPLOYEE" if row.employee == 1 else "FAMILY"
    siesa_id = row.siesa_id if row.siesa_id and row.siesa_id != 0 else nit

    if row.father_id == nit:
        first_name, middle_name = parse_full_name(row.father)
        last_name_1, last_name_2 = parse_full_name(row.father_last_name)
        email = row.father_email
        phone = row.father_cell_phone
    else:
        first_name, middle_name = parse_full_name(row.mother)
        last_name_1, last_name_2 = parse_full_name(row.mother_last_name)
        email = row.mother_email
        phone = row.mother_cell_phone

    return {
        "nit_type": "CC",
        "nit": nit,
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name_1": last_name_1,
        "last_name_2": last_name_2,
        "birth_date": None,
        "cell_phone": phone,
        "email": email,
        "person_source": person_source,
        "family_id": row.id_family,
        "siesa_id": siesa_id,
    }
    
def _get_family_id_for_employee(cursor, nit):
    query = """
        SELECT id_family
        FROM family_info
        WHERE father_id = ? OR mother_id = ?
    """
    cursor.execute(query, nit, nit)
    row = cursor.fetchone()
    return row.id_family if row else None


class PersonRepositorySQL(PersonRepository):
    """
    PRIORIDAD CAMBIADA (antes: Empleado > Estudiante > Familia):
      1. Estudiante   → family_id desde tabla students
      2. Familia       → family_id desde tabla family_info (id_family)
      3. Empleado      → family_id = NULL
    """

    def find_by_document(self, nit: str) -> dict:
        conn = get_mssql_connection()
        cursor = conn.cursor()

        try:
            person = _search_employees(cursor, nit)
            if person:
                return {"found": True, "person": person}

            person = _search_students(cursor, nit)
            if person:
                return {"found": True, "person": person}

            person = _search_family_info(cursor, nit)
            if person:
                return {"found": True, "person": person}

            return {"found": False}

        finally:
            conn.close()
