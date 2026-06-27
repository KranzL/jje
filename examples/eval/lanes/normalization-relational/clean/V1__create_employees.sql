CREATE TABLE departments (
    dept_id       INTEGER      PRIMARY KEY,
    dept_name     VARCHAR(120) NOT NULL UNIQUE,
    dept_location VARCHAR(120) NOT NULL
);

CREATE TABLE employees (
    employee_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_email VARCHAR(320) NOT NULL UNIQUE,
    employee_name VARCHAR(200) NOT NULL,
    hired_at      TIMESTAMPTZ  NOT NULL,
    dept_id       INTEGER      NOT NULL REFERENCES departments (dept_id)
);
