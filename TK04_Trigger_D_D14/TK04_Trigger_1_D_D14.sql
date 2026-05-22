-- TRIGGER 1: Validasi Username (Karakter Spesial & Duplikasi)

CREATE OR REPLACE FUNCTION check_username_validity()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.username !~ '^[a-zA-Z0-9]+$' THEN
        RAISE EXCEPTION 'Username "%" hanya boleh mengandung huruf dan angka tanpa simbol atau spasi.', NEW.username;
    END IF;

    IF EXISTS (
        SELECT 1 FROM user_account 
        WHERE LOWER(username) = LOWER(NEW.username)
          AND username != NEW.username
    ) THEN
        RAISE EXCEPTION 'Username "%" sudah terdaftar, gunakan username lain.', NEW.username;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_username_validity
BEFORE INSERT OR UPDATE ON user_account
FOR EACH ROW
EXECUTE FUNCTION check_username_validity();