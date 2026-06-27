MERGE INTO warehouse.core.dim_customer AS tgt
USING (
    SELECT
        src.customer_id,
        src.address,
        src.email,
        src.segment,
        src.updated_at,
        CASE
            WHEN tgt.customer_id IS NOT NULL THEN src.customer_id
            ELSE NULL
        END AS merge_key
    FROM staging.stg_customer AS src
    LEFT JOIN warehouse.core.dim_customer AS tgt
        ON tgt.customer_id = src.customer_id
       AND tgt.is_current = true
       AND (
                tgt.address <> src.address
             OR tgt.email   <> src.email
             OR tgt.segment <> src.segment
           )

    UNION ALL

    SELECT
        src.customer_id,
        src.address,
        src.email,
        src.segment,
        src.updated_at,
        NULL AS merge_key
    FROM staging.stg_customer AS src
    JOIN warehouse.core.dim_customer AS tgt
        ON tgt.customer_id = src.customer_id
       AND tgt.is_current = true
       AND (
                tgt.address <> src.address
             OR tgt.email   <> src.email
             OR tgt.segment <> src.segment
           )
) AS staged
ON tgt.customer_id = staged.merge_key
   AND tgt.is_current = true
WHEN MATCHED THEN UPDATE SET
        tgt.valid_to   = staged.updated_at,
        tgt.is_current = false
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
        md5(staged.customer_id || '|' || CAST(staged.updated_at AS string)),
        staged.customer_id,
        staged.address,
        staged.email,
        staged.segment,
        staged.updated_at,
        NULL,
        true,
        staged.updated_at
);
