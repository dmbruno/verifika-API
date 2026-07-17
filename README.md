# 📸 verifika-api

![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-3.1-black?logo=flask&logoColor=white)
![Solidity](https://img.shields.io/badge/solidity-0.8.20-363636?logo=solidity&logoColor=white)
![Network](https://img.shields.io/badge/network-Polygon%20Amoy-8247E5?logo=polygon&logoColor=white)
![Tests](https://img.shields.io/badge/tests-pytest%20%E2%80%94%20no%20mocks-0A9EDC)
![Status](https://img.shields.io/badge/status-MVP%20testnet-yellow)

**API REST que certifica que una foto no fue alterada desde el momento de su
captura**, calculando su hash y anclándolo de forma inmutable en la
blockchain de Polygon. Producto standalone — cualquier cliente (una mutual
de seguros, una app de delivery, etc.) puede integrar contra esta API para
verificar más tarde que una foto no fue editada ni su registro alterado.

No tiene frontend obligatorio: este repo es solo la API.

> 🚀 **API en producción (testnet):**
> [`https://web-production-cf40e.up.railway.app`](https://web-production-cf40e.up.railway.app)

📄 Spec formal de los endpoints, autocontenida para integrar desde afuera:
[`docs/api-spec.md`](docs/api-spec.md)

---

## 🧠 Cómo funciona, en una imagen

```
foto + lat/lon (opcional)
        │
        ▼
  hash SHA-256 de imagen + timestamp + ubicación
        │
        ▼
  anclado en Polygon Amoy (inmutable, on-chain)
        │
        ▼
  { verification_id, verify_url }
```

Después, con `GET /verify/<id>` cualquiera puede confirmar que ese registro
sigue siendo exactamente el mismo que se ancló — si algo se alteró después,
la verificación falla.

## 🛠️ Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11+, Flask |
| Blockchain | web3.py, contrato en Solidity (`contracts/HashRegistry.sol`), Polygon Amoy (chainId `80002`) |
| Persistencia | SQLite, sin ORM |
| Imágenes / EXIF | Pillow |
| Producción | Railway (gunicorn + volumen persistente) |

## 📦 Instalación local

### 1. Cloná el repo y creá el entorno virtual

```bash
cd verifika-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurá las variables de entorno

```bash
cp .env.example .env
```

Completá `.env` con:

```
POLYGON_RPC_URL=   # endpoint RPC de Polygon Amoy, ej: https://polygon-amoy-bor-rpc.publicnode.com
PRIVATE_KEY=       # private key de una wallet de testnet (nunca una wallet real)
CONTRACT_ADDRESS=  # direccion del contrato HashRegistry ya deployado en Amoy
SERVER_ADDRESS=    # direccion publica correspondiente a PRIVATE_KEY
```

⚠️ **Nunca commitees `.env`** — el `.gitignore` ya lo excluye, pero doble
chequealo antes de cada push.

La wallet necesita POL de testnet para pagar el gas de cada anclaje — se
consigue gratis en el [faucet oficial de Polygon](https://faucet.polygon.technology)
(red Amoy).

Si todavía no deployaste el contrato, `contracts/deploy.py` lo compila y lo
deploya usando esas mismas variables de entorno:

```bash
python3 contracts/deploy.py
```

Esto imprime la dirección del contrato deployado y guarda el ABI en
`contracts/HashRegistry.abi.json` — copiá la dirección a `CONTRACT_ADDRESS`
en tu `.env`.

### 3. Levantá el servidor

```bash
export FLASK_APP=app
flask run
```

Por defecto queda escuchando en `http://127.0.0.1:5000`.

## 🌐 Uso con curl

Los ejemplos apuntan a producción — para probar contra tu instancia local,
reemplazá `https://web-production-cf40e.up.railway.app` por
`http://127.0.0.1:5000`.

### `POST /verify` — Verificar una foto

```bash
curl -X POST https://web-production-cf40e.up.railway.app/verify \
  -F "image=@foto.jpg" \
  -F "lat=-34.6037" \
  -F "lon=-58.3816"
```

**Respuesta:**

```json
{
  "verification_id": "8a753940-a2fc-4b62-981f-3da90bdd5881",
  "verify_url": "/verify/8a753940-a2fc-4b62-981f-3da90bdd5881"
}
```

`lat` y `lon` son opcionales — si la imagen tiene GPS en el EXIF y el cliente
también manda `lat`/`lon`, la API compara ambas ubicaciones y marca un
`location_flag` si difieren más de 500 metros (ver
[`docs/api-spec.md`](docs/api-spec.md) para el detalle completo).

### `GET /verify/<id>` — Consultar una verificación

```bash
curl https://web-production-cf40e.up.railway.app/verify/8a753940-a2fc-4b62-981f-3da90bdd5881
```

**Respuesta:**

```json
{
  "valid": true,
  "tx_hash": "e6310d61f1d7494d194e7b5dbb8680f6c29b38b79d72ed8d847ac2c22d41e5fd",
  "location_flag": null
}
```

`tx_hash` se puede verificar de forma independiente en
[amoy.polygonscan.com](https://amoy.polygonscan.com).

> 🔁 **Nota:** una misma imagen no se puede verificar dos veces — el
> contrato la rechaza on-chain (409), sin importar timestamp o ubicación
> declarados en el segundo intento. Es intencional, no un bug.

## 🧪 Tests

La suite corre contra Polygon Amoy real — **sin mocks** — así que cada
corrida ancla transacciones de verdad y consume POL de testnet de la wallet
configurada en `.env`.

```bash
pytest tests/ -v
```

## 📐 Reglas de diseño

- 🔒 Nunca se persiste la imagen original, solo su hash.
- 🧬 El hash que se ancla es el del **registro completo** (imagen +
  timestamp + ubicación), no solo de la imagen — así cualquier campo
  alterado después de anclado rompe la verificación.
- 🚫 Una misma imagen no puede verificarse dos veces — rechazo on-chain.
- 🔑 `PRIVATE_KEY` y demás secrets solo por variables de entorno, nunca
  hardcodeados.

## 📊 Estado del proyecto

MVP en testnet (Polygon Amoy). No hay mainnet ni capa de IA todavía — ver
[`CLAUDE.md`](CLAUDE.md) para el detalle de fases.
