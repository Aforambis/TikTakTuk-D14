-- TRIGGER 2A: Cegah duplikasi nama venue di kota yang sama
CREATE OR REPLACE FUNCTION check_venue_duplicate()
RETURNS TRIGGER AS $$
DECLARE
    existing_id UUID;
BEGIN
    SELECT venue_id INTO existing_id
    FROM venue
    WHERE LOWER(venue_name) = LOWER(NEW.venue_name)
    AND LOWER(city) = LOWER(NEW.city)
    AND venue_id != NEW.venue_id;

    IF existing_id IS NOT NULL THEN
        RAISE EXCEPTION 'Venue ''%'' di kota ''%'' sudah terdaftar dengan ID %.', 
            NEW.venue_name, NEW.city, existing_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- TRIGGER 2B: Cegah hapus venue kalau masih ada event aktif
CREATE OR REPLACE TRIGGER trigger_check_venue_duplicate
BEFORE INSERT OR UPDATE ON venue
FOR EACH ROW EXECUTE FUNCTION check_venue_duplicate();

CREATE OR REPLACE FUNCTION check_venue_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM event
        WHERE venue_id = OLD.venue_id
        AND event_datetime >= NOW()
    ) THEN
        RAISE EXCEPTION 'Venue ''%'' masih memiliki event aktif sehingga tidak dapat dihapus.', 
            OLD.venue_name;
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_check_venue_delete
BEFORE DELETE ON venue
FOR EACH ROW EXECUTE FUNCTION check_venue_delete();