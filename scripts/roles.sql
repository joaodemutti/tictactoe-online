-- scripts/roles.sql
-- Modelo de privilegios do banco tictactoe. Passwords NAO ficam aqui
-- (defina com ALTER USER ... PASSWORD e guarde no gerenciador).
-- Rodar como superuser, conectado ao banco tictactoe:
--   sudo -u postgres psql -d tictactoe -f scripts/roles.sql

-- Owner (migrations / DDL)
ALTER DATABASE tictactoe OWNER TO tictactoe_user;
ALTER SCHEMA public OWNER TO tictactoe_user;

-- App (runtime / DML only)
GRANT CONNECT ON DATABASE tictactoe TO tictactoe_app;
GRANT USAGE ON SCHEMA public TO tictactoe_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tictactoe_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tictactoe_app;

-- Trava o DDL: ninguem alem do owner cria no schema public (gap do PG14,
-- onde public concede CREATE a PUBLIC por padrao)
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CREATE ON SCHEMA public TO tictactoe_user;

-- Tabelas/sequences FUTURAS criadas pelo owner ja nascem acessiveis ao app
ALTER DEFAULT PRIVILEGES FOR ROLE tictactoe_user IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tictactoe_app;
ALTER DEFAULT PRIVILEGES FOR ROLE tictactoe_user IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO tictactoe_app;
