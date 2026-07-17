# verifika-api

API REST que certifica que una foto no fue alterada desde el momento de su
captura. Calcula el hash SHA-256 de la imagen y de su metadata (timestamp,
ubicación), y lo ancla de forma inmutable en la blockchain de Polygon (red
Amoy, testnet). Cualquier cliente (una mutual de seguros, una app de delivery,
etc.) puede integrar contra esta API para verificar más tarde que una foto no
fue editada ni su registro alterado.

Es un producto standalone: no tiene frontend obligatorio. Este repo es solo
la API.

**API en producción (testnet):** `https://web-production-cf40e.up.railway.app`

Para la especificación formal de los endpoints (pensada para compartir con
clientes que van a integrar), ver [`docs/api-spec.md`](docs/api-spec.md).

## Stack

- Backend: Python 3.11+, Flask
- Blockchain: web3.py, contrato en Solidity (`contracts/HashRegistry.sol`), red Polygon Amoy (chainId 80002)
- Persistencia: SQLite (sin ORM)
- Imágenes / EXIF: Pillow

## Instalación local

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

## Uso con curl

Los ejemplos usan `http://127.0.0.1:5000` (local) — para probar contra
producción, reemplazá por `https://web-production-cf40e.up.railway.app`.

### Verificar una foto

```bash
curl -X POST http://127.0.0.1:5000/verify \
  -F "image=@foto.jpg" \
  -F "lat=-34.6037" \
  -F "lon=-58.3816"
```

Respuesta:

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

### Consultar una verificación

```bash
curl http://127.0.0.1:5000/verify/8a753940-a2fc-4b62-981f-3da90bdd5881
```

Respuesta:

```json
{
  "valid": true,
  "tx_hash": "e6310d61f1d7494d194e7b5dbb8680f6c29b38b79d72ed8d847ac2c22d41e5fd",
  "location_flag": null
}
```

`tx_hash` se puede verificar de forma independiente en
`https://amoy.polygonscan.com/tx/<tx_hash>`.

## Tests

La suite de tests corre contra Polygon Amoy real — sin mocks — así que cada
corrida ancla transacciones de verdad y consume POL de testnet de la wallet
configurada en `.env`.

```bash
pytest tests/ -v
```

## Reglas de diseño

- Nunca se persiste la imagen original, solo su hash.
- El hash que se ancla es el del **registro completo** (imagen + timestamp +
  ubicación), no solo de la imagen — así cualquier campo alterado después de
  anclado rompe la verificación.
- Una misma imagen no puede verificarse dos veces — el contrato la rechaza
  on-chain, sin importar el timestamp o la ubicación declarada en el segundo
  intento.
- `PRIVATE_KEY` y demás secrets solo por variables de entorno, nunca hardcodeados.

## Estado del proyecto

MVP en testnet (Polygon Amoy). No hay mainnet ni capa de IA todavía — ver
`CLAUDE.md` para el detalle de fases.
