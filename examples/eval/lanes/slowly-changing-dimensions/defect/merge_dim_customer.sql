MERGE INTO warehouse.core.dim_customer AS tgt
USING staging.stg_customer AS src
ON tgt.customer_id = src.customer_id
   AND tgt.is_current = true
WHEN MATCHED AND (
        tgt.address    <> src.address
     OR tgt.email      <> src.email
     OR tgt.segment    <> src.segment
) THEN UPDATE SET
        tgt.address    = src.address,
        tgt.email      = src.email,
        tgt.segment    = src.segment,
        tgt.updated_at = src.updated_at
WHEN NOT MATCHED THEN INSERT (
        customer_sk,
        customer_id,
        address,
        email,
        segment,
        valid_from,
        valid_to,
        is_current,
        updated_at
) VALUES (
        src.customer_sk,
        src.customer_id,
        src.address,
        src.email,
        src.segment,
        src.updated_at,
        NULL,
        true,
        src.updated_at
);
