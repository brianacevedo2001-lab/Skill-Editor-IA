"""Brutos y entregas por la API de Google Drive (nunca por la app de escritorio montada en <DRIVE>).

Credenciales (fuera de git):
  secrets/google_oauth_client.json   cliente OAuth «aplicación de escritorio» (lo descargas de Google Cloud)
  secrets/google_token.json          token que se crea la primera vez que autorizas en el navegador

Uso:
  python pipeline/drive_api.py auth                       autoriza y comprueba la conexión
  python pipeline/drive_api.py listar [--carpeta ID]      vídeos de la carpeta de brutos (y sus subcarpetas)
  python pipeline/drive_api.py bajar <id> <fileId>...     descarga a raw/<id>/ (en trozos, reanudable)
  python pipeline/drive_api.py bajar <id> --carpeta ID    descarga todos los vídeos de esa carpeta
  python pipeline/drive_api.py subir <archivo>... [--carpeta ID]   sube a la carpeta de entregas

Permisos: drive.readonly (leer brutos) + drive.file (subir entregas).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from comun import MARCA, RAW, SECRETS, duracion, escribir_json, leer_json

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]
CLIENTE = SECRETS / "google_oauth_client.json"
TOKEN = SECRETS / "google_token.json"
TROZO = 32 * 1024 * 1024  # 32 MB por petición
CAMPOS = "id,name,mimeType,size,md5Checksum,modifiedTime,videoMediaMetadata,parents"


def config() -> dict:
    return leer_json(MARCA / "proyecto.json")


def credenciales():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:  # token revocado o caducado: volver a autorizar
            print(f"No se pudo refrescar el token ({e}); vuelvo a pedir autorización.")
            creds = None
    if not creds or not creds.valid:
        if not CLIENTE.exists():
            sys.exit(f"Falta {CLIENTE}. Descarga el cliente OAuth (aplicación de escritorio) y guárdalo ahí.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENTE), SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent",
                                      authorization_prompt_message="Abriendo el navegador para autorizar…")
    SECRETS.mkdir(exist_ok=True)
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds


def servicio():
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=credenciales(), cache_discovery=False)


def mb(n) -> str:
    return f"{int(n) / 1024 / 1024:,.0f} MB".replace(",", ".")


def es_video(f: dict) -> bool:
    return f["mimeType"].startswith("video/") or f["name"].lower().endswith((".mp4", ".mov", ".mkv"))


def hijos(svc, carpeta: str) -> list[dict]:
    res, token = [], None
    while True:
        r = svc.files().list(
            q=f"'{carpeta}' in parents and trashed = false",
            fields=f"nextPageToken, files({CAMPOS})", pageSize=200, pageToken=token,
            orderBy="folder,name", supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        res += r.get("files", [])
        token = r.get("nextPageToken")
        if not token:
            return res


def cmd_auth(_args) -> None:
    svc = servicio()
    about = svc.about().get(fields="user(emailAddress,displayName)").execute()["user"]
    print(f"Conectado como {about['displayName']} <{about['emailAddress']}>")
    for clave in ("brutos", "entregas"):
        cid = config()[clave]["carpetaDriveId"]
        f = svc.files().get(fileId=cid, fields="id,name,capabilities(canAddChildren)",
                            supportsAllDrives=True).execute()
        print(f"  {clave}: «{f['name']}» ({cid})")


def cmd_listar(args) -> None:
    svc = servicio()
    carpeta = args.carpeta or config()["brutos"]["carpetaDriveId"]

    def mostrar(cid: str, sangria: str = "") -> None:
        for f in hijos(svc, cid):
            if f["mimeType"] == "application/vnd.google-apps.folder":
                print(f"{sangria}📁 {f['name']}  (carpeta {f['id']})")
                mostrar(f["id"], sangria + "   ")
            elif es_video(f):
                vm = f.get("videoMediaMetadata", {})
                dur = f"{int(vm['durationMillis']) / 1000:7.1f} s" if "durationMillis" in vm else "   ? s"
                res = f"{vm.get('width', '?')}x{vm.get('height', '?')}"
                print(f"{sangria}🎞  {f['name']:<45} {mb(f.get('size', 0)):>10}  {dur}  {res:>10}  {f['id']}")

    mostrar(carpeta)


def descargar(svc, creds, f: dict, destino: Path) -> Path:
    """Descarga por rangos a <nombre>.part y renombra al terminar. Reanuda si se corta."""
    from google.auth.transport.requests import AuthorizedSession

    final = destino / f["name"]
    total = int(f["size"])
    if final.exists() and final.stat().st_size == total:
        print(f"  ✔ ya estaba: {final.name} ({mb(total)})")
        return final
    parcial = final.with_suffix(final.suffix + ".part")
    hecho = parcial.stat().st_size if parcial.exists() else 0
    if hecho:
        print(f"  ↻ reanudando {f['name']} desde {mb(hecho)}")
    sesion = AuthorizedSession(creds)
    url = f"https://www.googleapis.com/drive/v3/files/{f['id']}?alt=media&supportsAllDrives=true"
    t0, reintentos = time.time(), 0
    with open(parcial, "ab") as out:
        while hecho < total:
            fin = min(hecho + TROZO, total) - 1
            try:
                r = sesion.get(url, headers={"Range": f"bytes={hecho}-{fin}"}, timeout=120)
                r.raise_for_status()
            except Exception as e:
                reintentos += 1
                if reintentos > 8:
                    raise
                espera = min(2 ** reintentos, 60)
                print(f"\n  ⚠ fallo de red ({e}); reintento en {espera} s")
                time.sleep(espera)
                continue
            out.write(r.content)
            hecho += len(r.content)
            reintentos = 0
            vel = hecho / max(time.time() - t0, 1e-3) / 1024 / 1024
            print(f"\r  ↓ {f['name']}: {hecho * 100 / total:5.1f} %  {mb(hecho)} / {mb(total)}  {vel:5.1f} MB/s",
                  end="", flush=True)
    print()
    if parcial.stat().st_size != total:
        raise RuntimeError(f"Tamaño incorrecto en {parcial}")
    parcial.replace(final)
    return final


def cmd_bajar(args) -> None:
    svc = servicio()
    creds = credenciales()
    destino = RAW / args.id
    destino.mkdir(parents=True, exist_ok=True)

    if args.carpeta:
        archivos = [f for f in hijos(svc, args.carpeta) if es_video(f)]
    else:
        archivos = [svc.files().get(fileId=i, fields=CAMPOS, supportsAllDrives=True).execute()
                    for i in args.archivos]
    if not archivos:
        sys.exit("No hay vídeos que descargar.")

    manifiesto_ruta = destino / "drive.json"
    manifiesto = leer_json(manifiesto_ruta) if manifiesto_ruta.exists() else {}
    for f in archivos:
        ruta = descargar(svc, creds, f, destino)
        dur_local = duracion(ruta)
        vm = f.get("videoMediaMetadata", {})
        dur_drive = int(vm["durationMillis"]) / 1000 if "durationMillis" in vm else None
        aviso = ""
        if dur_drive and abs(dur_local - dur_drive) > 1.0:
            aviso = f"  ⚠ Drive dice {dur_drive:.1f} s"
        print(f"  ✔ {ruta.name}: {mb(ruta.stat().st_size)}, {dur_local:.1f} s (ffprobe){aviso}")
        manifiesto[f["name"]] = {"fileId": f["id"], "size": int(f["size"]), "md5": f.get("md5Checksum"),
                                 "modifiedTime": f.get("modifiedTime"), "duracion": round(dur_local, 3)}
    escribir_json(manifiesto_ruta, manifiesto)
    print(f"Listo: {destino}")


def cmd_subir(args) -> None:
    from googleapiclient.http import MediaFileUpload

    svc = servicio()
    carpeta = args.carpeta or config()["entregas"]["carpetaDriveId"]
    for ruta in map(Path, args.archivos):
        media = MediaFileUpload(str(ruta), resumable=True, chunksize=TROZO)
        req = svc.files().create(body={"name": ruta.name, "parents": [carpeta]}, media_body=media,
                                 fields="id,name,webViewLink", supportsAllDrives=True)
        resp = None
        while resp is None:
            estado, resp = req.next_chunk()
            if estado:
                print(f"\r  ↑ {ruta.name}: {estado.progress() * 100:5.1f} %", end="", flush=True)
        print(f"\r  ✔ {resp['name']} → {resp['webViewLink']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth").set_defaults(fn=cmd_auth)
    s = sub.add_parser("listar"); s.add_argument("--carpeta"); s.set_defaults(fn=cmd_listar)
    s = sub.add_parser("bajar"); s.add_argument("id"); s.add_argument("archivos", nargs="*")
    s.add_argument("--carpeta"); s.set_defaults(fn=cmd_bajar)
    s = sub.add_parser("subir"); s.add_argument("archivos", nargs="+"); s.add_argument("--carpeta")
    s.set_defaults(fn=cmd_subir)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
