-- Datos para validar comisiones iniciales sin acceso directo: correr en la réplica de lectura
-- (Metabase, DBeaver, etc.), exportar como TSV y pasarlo al script con --datos archivo.tsv.
-- Cambia la fecha en las dos líneas marcadas, o sustituye el filtro por "l.LOAN_ID IN (...)".
SELECT l.LOAN_ID AS loan, l.APPLICATION_ID AS app, lat.description AS tipo, aa.APPLICATION_TYPE AS tipo_id, l.STATUS AS status,
       l.NOTIONAL AS notional, IFNULL(rl.recurrent_type, '-') AS rec,
       (SELECT por.max_notional FROM MDS.PRODUCT_OFFERING_RESULT por WHERE por.application_id = l.APPLICATION_ID ORDER BY por.id DESC LIMIT 1) AS max_notional,
       (SELECT pos.notional FROM MDS.PRODUCT_OFFERING_SELECTED pos WHERE pos.application_id = l.APPLICATION_ID ORDER BY pos.id DESC LIMIT 1) AS notional_sel,
       (SELECT SUM(lf.fee_percent) FROM KONFIO.LOAN_FEE lf WHERE lf.loan_id = l.LOAN_ID AND lf.is_active = 1) AS pct,
       (SELECT SUM(lf.fee_amount) FROM KONFIO.LOAN_FEE lf WHERE lf.loan_id = l.LOAN_ID AND lf.is_active = 1) AS lf_total,
       (SELECT SUM(lf.fee_amount_base) FROM KONFIO.LOAN_FEE lf WHERE lf.loan_id = l.LOAN_ID AND lf.is_active = 1) AS lf_base,
       (SELECT SUM(lf.fee_iva_amount) FROM KONFIO.LOAN_FEE lf WHERE lf.loan_id = l.LOAN_ID AND lf.is_active = 1) AS lf_iva,
       (SELECT r.principal_due + r.interest_due FROM KONFIO.RECURRENT_OFFER_ACCEPTED r WHERE r.new_loan_id = l.LOAN_ID ORDER BY r.id DESC LIMIT 1) AS liq,
       (SELECT t.amount FROM PAYMENTS.TRANSACTION_ORDER_OUTGOING t WHERE t.entity_id = l.LOAN_ID AND t.transaction_product_id = 1 AND t.transaction_type_id = 2 AND t.transaction_status_id = 5 ORDER BY t.created_date DESC LIMIT 1) AS depositado,
       (SELECT t.created_date FROM PAYMENTS.TRANSACTION_ORDER_OUTGOING t WHERE t.entity_id = l.LOAN_ID AND t.transaction_product_id = 1 AND t.transaction_type_id = 2 AND t.transaction_status_id = 5 ORDER BY t.created_date DESC LIMIT 1) AS dispersado,
       ip.fee_paid,
       (SELECT ci.TOTAL FROM KONFIO.CFDI_INVOICE ci WHERE ci.INITIAL_PAYMENT_LOAN_ID = l.LOAN_ID AND IFNULL(ci.CANCELLED, 0) = 0 ORDER BY ci.TAX_STAMP_TS DESC LIMIT 1) AS factura_total,
       (SELECT ci.SUBTOTAL FROM KONFIO.CFDI_INVOICE ci WHERE ci.INITIAL_PAYMENT_LOAN_ID = l.LOAN_ID AND IFNULL(ci.CANCELLED, 0) = 0 ORDER BY ci.TAX_STAMP_TS DESC LIMIT 1) AS factura_subtotal,
       (SELECT ci.IVA FROM KONFIO.CFDI_INVOICE ci WHERE ci.INITIAL_PAYMENT_LOAN_ID = l.LOAN_ID AND IFNULL(ci.CANCELLED, 0) = 0 ORDER BY ci.TAX_STAMP_TS DESC LIMIT 1) AS factura_iva,
       (SELECT GROUP_CONCAT(CONCAT(n.id, '|', n.created_date, '|', n.created_by, '|', nr.negotiation_type_id, '|', nr.negotiation_parameter_id, '|', IFNULL(nv.original_value, ''), '|', IFNULL(nv.old_value, ''), '|', IFNULL(nv.new_value, '')) ORDER BY n.id, nr.negotiation_parameter_id SEPARATOR ';')
          FROM KONFIO.NEGOTIATION n JOIN KONFIO.NEGOTIATION_VALUES nv ON nv.negotiation_id = n.id JOIN KONFIO.NEGOTIATION_RULE nr ON nr.id = nv.negotiation_rule_id
         WHERE n.application_id = l.APPLICATION_ID AND n.is_active = 1) AS negociaciones
FROM KONFIO.LOAN l
JOIN KONFIO.APPLICATION_ANSWERS aa ON aa.APPLICATION_ANSWERS_ID = l.APPLICATION_ID
JOIN KONFIO.LU_APPLICATION_TYPE lat ON lat.id = aa.APPLICATION_TYPE
LEFT JOIN KONFIO.RECURRENT_LOAN rl ON rl.new_application_id = l.APPLICATION_ID AND rl.is_active = 1
LEFT JOIN KONFIO.INITIAL_PAYMENT ip ON ip.loan_id = l.LOAN_ID
WHERE l.LOAN_ID IN (
    SELECT t2.entity_id FROM PAYMENTS.TRANSACTION_ORDER_OUTGOING t2
    WHERE t2.transaction_product_id = 1 AND t2.transaction_type_id = 2 AND t2.transaction_status_id = 5
      AND t2.created_date >= '2026-10-06 00:00:00'   -- fecha a revisar
      AND t2.created_date <  '2026-10-07 00:00:00'   -- día siguiente
)
