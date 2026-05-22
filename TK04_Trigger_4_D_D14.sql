-- ============================================================
-- TK04 - Trigger #4: Validasi Promotion saat digunakan ke Order
-- ============================================================

-- 1. Function
CREATE OR REPLACE FUNCTION validate_promotion_on_order()
RETURNS TRIGGER AS $$
DECLARE
    v_promo_code        VARCHAR(50);
    v_usage_limit       INTEGER;
    v_usage_count       INTEGER;
    v_start_date        DATE;
    v_end_date          DATE;
    v_event_date        DATE;
BEGIN
    -- Check 1: Promotion exists
    SELECT promo_code, usage_limit, start_date, end_date
    INTO v_promo_code, v_usage_limit, v_start_date, v_end_date
    FROM promotion
    WHERE promotion_id = NEW.promotion_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ERROR: Promotion dengan ID % tidak ditemukan.', NEW.promotion_id;
    END IF;

    -- Check 2: Usage limit not exceeded
    SELECT COUNT(*)
    INTO v_usage_count
    FROM order_promotion
    WHERE promotion_id = NEW.promotion_id;

    IF v_usage_count >= v_usage_limit THEN
        RAISE EXCEPTION 'ERROR: Promotion "%" telah mencapai batas maksimum penggunaan.', v_promo_code;
    END IF;

    -- Check 3: Event date within promotion period
    -- Trace: order_promotion -> order -> ticket -> ticket_category -> event
    SELECT DATE(e.event_datetime)
    INTO v_event_date
    FROM event e
    JOIN ticket_category tc ON tc.tevent_id = e.event_id
    JOIN ticket t ON t.tcategory_id = tc.category_id
    JOIN "order" o ON o.order_id = t.torder_id
    WHERE o.order_id = NEW.order_id
    LIMIT 1;

    IF v_event_date IS NOT NULL THEN
        IF v_event_date < v_start_date OR v_event_date > v_end_date THEN
            RAISE EXCEPTION 'ERROR: Promotion "%" tidak berlaku untuk tanggal event ini.', v_promo_code;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Trigger
DROP TRIGGER IF EXISTS trg_validate_promotion_on_order ON order_promotion;

CREATE TRIGGER trg_validate_promotion_on_order
BEFORE INSERT ON order_promotion
FOR EACH ROW
EXECUTE FUNCTION validate_promotion_on_order();