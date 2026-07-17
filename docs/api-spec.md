# Verifika API — Especificación

Verifika es una API REST que certifica que una foto no fue alterada desde el
momento de su captura. Al subir una imagen, la API calcula un hash
criptográfico del registro completo (imagen + momento de captura + ubicación
declarada) y lo ancla de forma inmutable en la blockchain de Polygon. Ese
anclaje permite, en cualquier momento futuro, confirmar que el registro no
fue modificado — cualquier alteración posterior (de la imagen, el timestamp o
la ubicación) invalida la verificación.

Este documento describe los dos endpoints disponibles y es autocontenido:
no asume conocimiento del resto del proyecto.

- **Base URL:** la que te haya provisto el operador de la API (ej.
  `https://api.verifika.example`). En este documento se usa
  `https://api.verifika.example` como placeholder en los ejemplos.
- **Autenticación:** ninguna en la versión actual (MVP sobre testnet).
- **Formato:** todas las respuestas son JSON. Las requests a `POST /verify`
  son `multipart/form-data`.
- **Red blockchain:** Polygon Amoy (testnet), chainId `80002`. Toda
  transacción anclada puede verificarse de forma independiente en
  `https://amoy.polygonscan.com`.

---

## POST /verify

Sube una foto para certificarla. Calcula su hash, cruza la ubicación
declarada contra el GPS embebido en el EXIF (si existe), y ancla el hash del
registro completo en la blockchain.

### Request

```
POST /verify
Content-Type: multipart/form-data
```

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `image` | archivo (binario) | Sí | La foto a certificar. Se recomienda JPEG — es el formato del que se puede extraer GPS del EXIF de forma confiable. |
| `lat` | float | No | Latitud declarada por el cliente (ej. la del GPS del dispositivo al momento de subir la foto). |
| `lon` | float | No | Longitud declarada por el cliente. |

Ejemplo:

```bash
curl -X POST https://api.verifika.example/verify \
  -F "image=@foto.jpg" \
  -F "lat=-34.6037" \
  -F "lon=-58.3816"
```

### Response — 200 OK

```json
{
  "verification_id": "8a753940-a2fc-4b62-981f-3da90bdd5881",
  "verify_url": "/verify/8a753940-a2fc-4b62-981f-3da90bdd5881"
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `verification_id` | string (UUID) | Identificador único de esta verificación. Guardalo — es lo que necesitás para consultar el resultado con `GET /verify/<verification_id>`. |
| `verify_url` | string | Path relativo del endpoint de consulta para este `verification_id`. |

Un 200 confirma que el hash quedó anclado en la blockchain. No implica que
la ubicación declarada coincida con el GPS del EXIF — para eso ver
`location_flag` en la respuesta del `GET` (más abajo).

### Errores posibles

| Código | Cuándo ocurre | Body de ejemplo |
|---|---|---|
| `400` | Falta el campo `image` en el request. | `{"error": "falta el campo 'image'"}` |
| `400` | El archivo `image` está vacío (0 bytes). | `{"error": "imagen vacia"}` |
| `409` | Esta imagen (el mismo contenido exacto) ya fue verificada antes, en cualquier momento — la blockchain la rechaza sin importar que ahora se declare un timestamp o ubicación distintos. | `{"error": "Esta imagen ya fue verificada anteriormente"}` |
| `409` | Caso extremadamente infrecuente: el registro exacto (misma imagen + mismo timestamp de servidor + misma ubicación, hasta el microsegundo) ya fue anclado. En la práctica casi nunca ocurre salvo reintentos duplicados de la misma request. | `{"error": "Este registro (imagen + timestamp + ubicacion) ya fue anclado antes"}` |

**Nota sobre EXIF ausente:** si la imagen no trae GPS en el EXIF (foto sin
metadata de ubicación, o formato que no la soporta), esto **no** es un error
— el endpoint responde 200 igual. Simplemente no hay con qué comparar la
`lat`/`lon` declarada, así que no se genera `location_flag` (ver abajo).

---

## GET /verify/{verification_id}

Consulta el resultado de una verificación previamente creada con
`POST /verify`.

### Request

```
GET /verify/{verification_id}
```

| Parámetro | Tipo | Ubicación | Descripción |
|---|---|---|---|
| `verification_id` | string (UUID) | path | El id devuelto por `POST /verify`. |

Ejemplo:

```bash
curl https://api.verifika.example/verify/8a753940-a2fc-4b62-981f-3da90bdd5881
```

### Response — 200 OK

```json
{
  "valid": true,
  "tx_hash": "e6310d61f1d7494d194e7b5dbb8680f6c29b38b79d72ed8d847ac2c22d41e5fd",
  "location_flag": null
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `valid` | boolean | `true` si el hash del registro está confirmado en la blockchain (recalculado y comparado contra el contrato en el momento de la consulta, no un valor cacheado). `false` si el registro guardado no coincide con lo anclado on-chain — indicaría manipulación de los datos guardados. |
| `tx_hash` | string | Hash de la transacción en Polygon Amoy que ancló este registro. Verificable de forma independiente en `https://amoy.polygonscan.com/tx/<tx_hash>`. |
| `location_flag` | string \| `null` | `null` si no hubo discrepancia de ubicación **o** si no se pudo comparar (faltó `lat`/`lon` del cliente, o la imagen no tenía GPS en el EXIF). Si no es `null`, contiene un mensaje describiendo la distancia entre la ubicación declarada y la del EXIF (se marca cuando supera los 500 metros). Un `location_flag` no nulo **no** invalida la verificación — `valid` puede seguir siendo `true`; es información adicional para que el consumidor de la API decida qué hacer con ella. |

Ejemplo con discrepancia de ubicación:

```json
{
  "valid": true,
  "tx_hash": "1988a2328d9149e7ce762a909832f8dd989b622e29fc21615a61b765fdc4aa1c",
  "location_flag": "distancia entre ubicacion declarada y EXIF: 18373416.5m (supera el umbral de 500m)"
}
```

### Errores posibles

| Código | Cuándo ocurre | Body de ejemplo |
|---|---|---|
| `404` | No existe ninguna verificación con ese `verification_id`. | `{"error": "verification_id no encontrado"}` |

---

## Resumen de códigos de estado

| Código | Significado |
|---|---|
| `200` | Operación exitosa (creación o consulta). |
| `400` | Request mal formado (falta la imagen, o está vacía). |
| `404` | `verification_id` inexistente. |
| `409` | Conflicto: la imagen o el registro exacto ya estaban anclados. |
