-- ============================================================
-- TK04 - Trigger #5 (Wajib Kelompok)
-- Part 1: Cek keterikatan Seat sebelum dihapus
-- Part 2: Cek kuota Ticket Category sebelum buat Tiket baru
-- ============================================================


-- ─── PART 1: Cek has_relationship sebelum DELETE seat ────────────────────────

CREATE OR REPLACE FUNCTION check_seat_before_delete()
RETURNS TRIGGER AS $$
DECLARE
    v_is_assigned   INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_is_assigned
    FROM has_relationship
    WHERE seat_id = OLD.seat_id;

    IF v_is_assigned > 0 THEN
        RAISE EXCEPTION 'ERROR: Kursi % - Baris % No. % tidak dapat dihapus karena sudah terisi.',
            OLD.section, OLD.row_number, OLD.seat_number;
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_seat_before_delete ON seat;

CREATE TRIGGER trg_check_seat_before_delete
BEFORE DELETE ON seat
FOR EACH ROW
EXECUTE FUNCTION check_seat_before_delete();


-- ─── PART 2: Cek kuota ticket_category sebelum INSERT ticket ─────────────────

CREATE OR REPLACE FUNCTION check_ticket_quota_before_insert()
RETURNS TRIGGER AS $$
DECLARE
    v_category_name VARCHAR(50);
    v_quota         INTEGER;
    v_sold_count    INTEGER;
BEGIN
    SELECT category_name, quota
    INTO v_category_name, v_quota
    FROM ticket_category
    WHERE category_id = NEW.tcategory_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ERROR: Kategori tiket tidak ditemukan.';
    END IF;

    SELECT COUNT(*)
    INTO v_sold_count
    FROM ticket
    WHERE tcategory_id = NEW.tcategory_id;

    IF v_sold_count >= v_quota THEN
        RAISE EXCEPTION 'ERROR: Kuota kategori tiket % sudah penuh. Tidak dapat membuat tiket baru.',
            v_category_name;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_ticket_quota ON ticket;

CREATE TRIGGER trg_check_ticket_quota
BEFORE INSERT ON ticket
FOR EACH ROW
EXECUTE FUNCTION check_ticket_quota_before_insert();