# CLAUDE.md — verifika-api
 
## Qué es esto
API REST que certifica que una foto no fue alterada desde el momento de su captura,
usando hash SHA-256 + anclaje inmutable en blockchain (Polygon). Producto standalone,
consumible por cualquier cliente (mutual de seguros, app de delivery, etc.) vía API.
NO tiene frontend obligatorio — el frontend, si existe, es un cliente más de esta API.
 
## Deploy
- Hosteado en Railway: `https://web-production-cf40e.up.railway.app`
- Servidor de producción: gunicorn (`Procfile`), no el `flask run` de desarrollo
- SQLite vive en un volumen persistente de Railway montado en `/data`
  (variable `DATABASE_PATH=/data/verifika.db`, ver `app/db.py`)

## Alcance actual (MVP en testnet)
- Solo API REST, sin frontend, sin panel de administración todavía
- Red: Polygon Amoy (testnet) — NO mainnet todavía, eso es Fase 6 futura
- Sin capa de IA todavía (detección de manipulación/duplicados queda para cuando
  haya un cliente real pagando, no ahora)
- Nunca se persiste la imagen original, solo su hash
 
## Stack
- Backend: Python 3.11+, Flask
- Blockchain: web3.py, contrato en Solidity, red Polygon Amoy (chainId 80002)
- Persistencia: SQLite para el MVP (migrar a Postgres cuando haya tráfico real)
- Sin Supabase — Postgres/SQLite puro, SQLAlchemy opcional como ORM
- Imágenes/EXIF: Pillow
 
## Estructura de carpetas

verifika-api/
├── CLAUDE.md
├── .env.example
├── requirements.txt
├── contracts/
│   ├── HashRegistry.sol
│   └── HashRegistry.abi.json
├── app/
│   ├── __init__.py
│   ├── routes.py          # endpoints /verify y /verify/<id>
│   ├── blockchain.py      # conexión web3, anchor_hash()
│   ├── location.py        # extract_exif_gps(), distance_meters()
│   └── db.py
├── tests/
│   ├── conftest.py
│   └── test_verify_e2e.py  # pytest tests/ -v — corre contra Amoy real, sin mocks
├── docs/
│   └── api-spec.md        # spec formal de los endpoints, autocontenida para clientes
└── README.md

 
## Variables de entorno (.env, nunca commitear — usar .env.example como plantilla)

POLYGON_RPC_URL=
PRIVATE_KEY=
CONTRACT_ADDRESS=
SERVER_ADDRESS=

 
## Endpoints objetivo

POST /verify
  multipart/form-data: image (file), lat (float, opcional), lon (float, opcional)
  responde: { "verification_id": str, "verify_url": str }

GET /verify/<verification_id>
  responde: { "valid": bool, "tx_hash": str, "location_flag": str|null }

 
## Reglas de diseño (no romper)
- Nunca persistir la imagen original, solo su hash
- El hash que se ancla en blockchain es del REGISTRO completo (imagen + timestamp +
  ubicación), no solo de la imagen — así cualquier campo alterado después rompe la
  verificación
- Un mismo hash de imagen no puede registrarse dos veces (el contrato revierte —
  chequeo on-chain vía mapping `imageRegisteredAt`, independiente del record_hash)
- PRIVATE_KEY y demás secrets solo por variables de entorno, nunca hardcodeados
- No agregar IA, panel de administración, ni mainnet salvo indicación explícita
 
## Estado de fases (Cowork: marcar con [x] al terminar cada una)
- [x] Fase 0 — Setup entorno + wallet testnet
- [x] Fase 1 — Smart contract deployado en Amoy (0x6d152D528a6F079a85c341e8dd3ee0262B18aDAf —
  redeployado para agregar rechazo on-chain de imagen duplicada; la dirección
  anterior 0x8BCd86...Aa4c8 quedó obsoleta)
- [x] Fase 2 — Endpoints /verify y /verify/<id> con cruce de ubicación
- [x] Fase 3 — Persistencia SQLite
- [x] Fase 4 — Testing end-to-end en Amoy
- [x] Fase 5 — Documentación (README + spec de API)
- [ ] Fase 6 (futuro, NO ejecutar todavía) — mainnet + capa de IA
