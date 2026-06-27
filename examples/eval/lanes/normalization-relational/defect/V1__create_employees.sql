CREATE TABLE employees (
    employee_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_email VARCHAR(320) NOT NULL UNIQUE,
    employee_name VARCHAR(200) NOT NULL,
    hired_at      TIMESTAMPTZ  NOT NULL,
    dept_id       INTEGER      NOT NULL,
    dept_name     VARCHAR(120) NOT NULL,
    dept_location VARCHAR(120) NOT NULL
);
