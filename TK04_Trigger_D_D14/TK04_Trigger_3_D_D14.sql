-- TRIGGER 3: Validasi Artist pada Event & Cek Sisa Kuota Kategori Tiket

-- PART 1: Validasi Duplikasi artist_id dan event_id pada EVENT_ARTIST
CREATE OR REPLACE FUNCTION check_artist_event_insert()
RETURNS TRIGGER AS $$
DECLARE
    v_artist_name VARCHAR;
    v_event_title VARCHAR;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM artist WHERE artist_id = NEW.artist_id) THEN
        RAISE EXCEPTION 'ERROR: Artist dengan ID % tidak ditemukan.', NEW.artist_id;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM event WHERE event_id = NEW.event_id) THEN
        RAISE EXCEPTION 'ERROR: Event dengan ID % tidak ditemukan.', NEW.event_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM event_artist 
        WHERE artist_id = NEW.artist_id AND event_id = NEW.event_id
    ) THEN
        SELECT name INTO v_artist_name FROM artist WHERE artist_id = NEW.artist_id;
        SELECT event_title INTO v_event_title FROM event WHERE event_id = NEW.event_id;
        RAISE EXCEPTION 'ERROR: Artist "%" sudah terdaftar pada event "%".', v_artist_name, v_event_title;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_artist_event_insert ON event_artist;
CREATE TRIGGER trg_check_artist_event_insert
BEFORE INSERT ON event_artist
FOR EACH ROW
EXECUTE FUNCTION check_artist_event_insert();

-- PART 2: Menampilkan Sisa Kuota Ticket Category Berdasarkan event_id
CREATE OR REPLACE FUNCTION get_ticket_quota(p_event_id UUID)
RETURNS TABLE (
    category_name VARCHAR,
    sisa_kuota INTEGER
) AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM event WHERE event_id = p_event_id) THEN
        RAISE EXCEPTION 'ERROR: Event dengan ID % tidak ditemukan.', p_event_id;
    END IF;

    RETURN QUERY
    SELECT 
        tc.category_name::VARCHAR,
        (tc.quota - COALESCE(
            (SELECT COUNT(*) FROM ticket t WHERE t.category_id = tc.category_id)
        , 0))::INTEGER AS sisa_kuota
    FROM ticket_category tc
    WHERE tc.event_id = p_event_id;
END;
$$ LANGUAGE plpgsql;