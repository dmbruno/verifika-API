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
│   ├── HashRegistry.sol       # onlyOwner — solo el multisig puede registerHash()
│   ├── HashRegistry.abi.json
│   ├── SimpleMultisig.sol     # multisig de recuperacion (ver seccion Seguridad)
│   ├── SimpleMultisig.abi.json
│   └── deploy.py              # deploya ambos contratos en secuencia
├── app/
│   ├── __init__.py
│   ├── routes.py          # endpoints /verify y /verify/<id>
│   ├── blockchain.py      # conexión web3, anchor_hash() via multisig
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
MULTISIG_ADDRESS=

 
## Endpoints objetivo

POST /verify
  multipart/form-data: image (file), lat (float, opcional), lon (float, opcional)
  responde: { "verification_id": str, "verify_url": str }

GET /verify/<verification_id>
  responde: { "valid": bool, "tx_hash": str, "location_flag": str|null }

 
## Seguridad — arquitectura de claves (multisig)
- `HashRegistry.registerHash()` tiene `onlyOwner`: solo el contrato `SimpleMultisig`
  puede llamarlo (verificado: ni siquiera la wallet operativa puede llamarlo
  directo, revierte con "no autorizado")
- `SimpleMultisig` tiene 2 owners (`required = 1`): la wallet operativa (`PRIVATE_KEY`
  en `.env`/Railway) y una clave de respaldo guardada **offline, fuera de este
  repo y de la infraestructura del servidor**
- Por qué `required = 1` y no 2: con 2 se necesitaría aprobación manual en cada
  `POST /verify`, matando la automatización del producto. Con 1, cualquiera de
  las dos claves opera sola — la de respaldo sirve para recuperación
  (`removeOwner`/`addOwner` si la clave operativa se pierde o se filtra), no
  para exigir doble aprobación en cada anclaje
- **Qué protege esto:** pérdida de la clave operativa (hardware roto, error
  humano, etc.) — el sistema no queda huérfano, la clave de respaldo puede
  reemplazarla
- **Qué NO protege:** una clave operativa robada sigue pudiendo operar sola
  mientras nadie note el robo y ejecute la recuperación con la clave de
  respaldo. Esto es un multisig de recuperación, no un esquema de aprobación
  dual — para eso hace falta `required > 1` y un segundo aprobador humano
  real, lo cual no aplica todavía (dev único)
- Para producción/mainnet, migrar a una solución auditada (Gnosis Safe /
  Safe{Wallet}) en vez de `SimpleMultisig.sol`, que es intencionalmente
  mínimo y sin auditar — suficiente para testnet, no para producción real

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
- [x] Fase 1 — Smart contract deployado en Amoy. Direcciones vigentes:
  `HashRegistry` = `0xABfAC6be44300E0430c01b845423c226682dd153`,
  `SimpleMultisig` (owner de HashRegistry) = `0xdEFd9A0Ae52BF272c40aca3797d96fb9606B4c40`.
  Historial: v1 `0x8BCd86...Aa4c8` (sin rechazo de duplicados) → v2
  `0x6d152D52...B18aDAf` (agrega rechazo de imagen duplicada) → v3 actual
  (agrega `onlyOwner` + multisig de recuperación). Las anteriores quedaron obsoletas
- [x] Fase 2 — Endpoints /verify y /verify/<id> con cruce de ubicación
- [x] Fase 3 — Persistencia SQLite
- [x] Fase 4 — Testing end-to-end en Amoy
- [x] Fase 5 — Documentación (README + spec de API)
- [ ] Fase 6 (futuro, NO ejecutar todavía) — mainnet + capa de IA
