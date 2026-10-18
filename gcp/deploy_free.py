"""Deploy only public static assets to unbilled Firebase Hosting (Spark).

Official flow: https://firebase.google.com/docs/hosting/api-deploy
No Cloud Build, Cloud Run, Vertex, model requests, billing links or token files.
Run --check-only for an entirely local asset validation without Google calls.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCOUNT = "owner@example.com"
HOSTING = "https://firebasehosting.googleapis.com/v1beta1"
MANAGEMENT = "https://firebase.googleapis.com/v1beta1"
ROOT_FILES = ("index.html", "retail_data.js", "runtime-config.js", "commerce-api.js")
PUBLIC_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".css"}
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_DEMO_BYTES = 16 * 1024 * 1024
DEMO_FILES = ("demo.html", "demo/RetailIQ_Abhishek_voice_demo.mp4")
ALLOWED_HOSTS = {"firebasehosting.googleapis.com", "firebase.googleapis.com", "upload-firebasehosting.googleapis.com"}


class DeploymentError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def collect_files(root: Path = ROOT, include_deck: bool = False, include_demo: bool = False) -> dict[str, bytes]:
    root = root.resolve()
    candidates = [root / name for name in ROOT_FILES]
    candidates.append(root / "demo/samples/shelf_compliant.jpg")
    for folder in ("assets", "brand"):
        candidates.extend(p for p in (root / folder).rglob("*") if p.is_file() and p.suffix.lower() in PUBLIC_EXTENSIONS)
    if include_deck:
        candidates.extend(root / name for name in ("pitch-slides.html", "pitch-slides.pdf"))
    if include_demo:
        candidates.extend(root / name for name in DEMO_FILES)
    files = {}
    total = 0
    for source in sorted(candidates):
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(root):
            raise DeploymentError("A required public asset is missing or resolves outside the repository")
        raw = source.read_bytes()
        total += len(raw)
        file_limit = MAX_DEMO_BYTES if include_demo and source == root / DEMO_FILES[1] else MAX_FILE_BYTES
        if len(raw) > file_limit or total > MAX_TOTAL_BYTES or len(files) >= 500:
            raise DeploymentError("Static bundle exceeds the bounded free-deployment limit")
        files["/" + source.relative_to(root).as_posix()] = raw
    runtime = files["/runtime-config.js"].decode("utf-8-sig")
    if not re.search(r'backend[\"\']?\s*:\s*false\b', runtime):
        raise DeploymentError("runtime-config.js must explicitly use backend:false for Spark hosting")
    return files


def compressed_files(files: dict[str, bytes]) -> tuple[dict[str, str], dict[str, bytes]]:
    manifest, blobs = {}, {}
    for path, raw in files.items():
        compressed = gzip.compress(raw, compresslevel=9, mtime=0)
        digest = hashlib.sha256(compressed).hexdigest()
        manifest[path] = digest
        blobs[digest] = compressed
    return manifest, blobs


class SparkDeployment:
    def __init__(self, project: str, account: str, gcloud: str):
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
            raise DeploymentError("Invalid Google Cloud project ID")
        if not re.fullmatch(r"[A-Za-z0-9_.+@-]+", account) or "@" not in account:
            raise DeploymentError("Invalid Google account")
        self.project, self.account, self.gcloud = project, account, gcloud
        self._token = None
        self._opener = urllib.request.build_opener(NoRedirect())

    def cli(self, *arguments: str) -> str:
        # OAuth output is captured only in memory. Never include command output in exceptions.
        result = subprocess.run([self.gcloud, *arguments, "--account=" + self.account, "--quiet"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        if result.returncode:
            raise DeploymentError("Google CLI operation failed (" + " ".join(arguments[:2]) + "); no deployment fallback was attempted")
        return result.stdout.strip()

    def require_unbilled(self) -> None:
        try:
            billing = json.loads(self.cli("billing", "projects", "describe", self.project, "--format=json"))
        except (ValueError, subprocess.SubprocessError) as exc:
            raise DeploymentError("Cannot verify billing status; free-only deployment stopped") from exc
        if billing.get("billingEnabled") is not False:
            raise DeploymentError("Billing is enabled or unknown; refusing free-only deployment")

    def request(self, method: str, url: str, body=None, *, binary: bool = False, allow_missing: bool = False):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise DeploymentError("Refused an unexpected Firebase API destination")
        if self._token is None:
            self._token = self.cli("auth", "print-access-token")
            if not self._token or any(c.isspace() for c in self._token):
                raise DeploymentError("Could not obtain a valid in-memory OAuth token")
        data = body if binary else (json.dumps(body).encode("utf-8") if body is not None else None)
        request = urllib.request.Request(url, data=data, method=method,
            headers={"Authorization":"Bearer " + self._token,
                     "X-Goog-User-Project":self.project,
                     "Content-Type":"application/octet-stream" if binary else "application/json"})
        try:
            with self._opener.open(request, timeout=45) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise DeploymentError("Firebase API response exceeded the permitted size")
            return {} if binary or not raw else json.loads(raw)
        except urllib.error.HTTPError as exc:
            if allow_missing and exc.code == 404:
                return None
            if exc.code == 429:
                raise DeploymentError("Firebase free quota/rate limit reached; stopped without billing upgrade or retries") from None
            raise DeploymentError(f"Firebase {method} request failed with HTTP {exc.code}; credentials and response body withheld") from None
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise DeploymentError("Firebase request failed; credentials and response body withheld") from None

    def ensure_firebase(self) -> None:
        existing = self.request("GET", MANAGEMENT + "/projects/" + self.project, allow_missing=True)
        if existing is not None:
            return
        operation = self.request("POST", MANAGEMENT + "/projects/" + self.project + ":addFirebase", {})
        for _ in range(45):
            if operation.get("done"):
                if operation.get("error"):
                    raise DeploymentError("Firebase project provisioning failed; no billing changes were made")
                return
            name = operation.get("name", "")
            if not re.fullmatch(r"operations/[A-Za-z0-9_./-]+", name) or ".." in name:
                raise DeploymentError("Unexpected Firebase operation name")
            time.sleep(4)
            operation = self.request("GET", MANAGEMENT + "/" + name)
        raise DeploymentError("Firebase provisioning exceeded its bounded polling window; rerun later")

    def ensure_site(self) -> str:
        listing = self.request("GET", HOSTING + "/projects/" + self.project + "/sites?pageSize=100")
        sites = listing.get("sites", [])
        default = next((s for s in sites if s.get("type") == "DEFAULT_SITE"), None)
        if default is None:
            default = self.request("POST", HOSTING + "/projects/" + self.project + "/sites?" + urllib.parse.urlencode({"siteId":self.project}), {})
        site = default.get("name", "").rsplit("/", 1)[-1]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,28}[a-z0-9]", site):
            raise DeploymentError("Unexpected Firebase Hosting site identifier")
        return site

    def deploy(self, files: dict[str, bytes]) -> str:
        # This check precedes every provisioning command and deployment phase.
        self.require_unbilled()
        self.cli("services", "enable", "firebase.googleapis.com", "firebasehosting.googleapis.com", "--project=" + self.project)
        self.ensure_firebase()
        site = self.ensure_site()
        self.require_unbilled()
        version = self.request("POST", HOSTING + "/sites/" + site + "/versions", {"config":{"headers":[
            {"glob":"**","headers":{"Cache-Control":"no-cache","X-Content-Type-Options":"nosniff","Referrer-Policy":"strict-origin-when-cross-origin"}}]}})
        name = version.get("name", "")
        if not re.fullmatch(r"sites/" + re.escape(site) + r"/versions/[A-Za-z0-9_-]+", name):
            raise DeploymentError("Unexpected Firebase Hosting version identifier")
        manifest, blobs = compressed_files(files)
        populated = self.request("POST", HOSTING + "/" + name + ":populateFiles", {"files":manifest})
        upload = populated.get("uploadUrl", "").rstrip("/")
        expected = "https://upload-firebasehosting.googleapis.com/upload/" + name + "/files"
        if upload != expected:
            raise DeploymentError("Firebase returned an unexpected upload destination")
        for digest in populated.get("uploadRequiredHashes", []):
            if digest not in blobs:
                raise DeploymentError("Firebase requested a file outside the allowlisted bundle")
            self.request("POST", upload + "/" + digest, blobs[digest], binary=True)
        self.require_unbilled()
        finalized = self.request("PATCH", HOSTING + "/" + name + "?update_mask=status", {"status":"FINALIZED"})
        if finalized.get("status") != "FINALIZED":
            raise DeploymentError("Firebase version did not finalize; nothing was released")
        self.require_unbilled()
        release = self.request("POST", HOSTING + "/sites/" + site + "/releases?" + urllib.parse.urlencode({"versionName":name}))
        if release.get("type") != "DEPLOY":
            raise DeploymentError("Firebase did not confirm a deployment release")
        return "https://" + site + ".web.app"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--gcloud", default=shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud")
    parser.add_argument("--include-deck", action="store_true")
    parser.add_argument("--include-demo", action="store_true", help="Include only the final creator-approved video and its player page")
    parser.add_argument("--check-only", action="store_true", help="Validate only public files locally; no Google or model calls")
    args = parser.parse_args(argv)
    try:
        files = collect_files(include_deck=args.include_deck, include_demo=args.include_demo)
        print(f"Validated {len(files)} allowlisted public files ({sum(map(len,files.values()))} bytes)", flush=True)
        if args.check_only:
            print("Local validation only; no cloud or model calls made")
            return 0
        result = SparkDeployment(args.project, args.account, args.gcloud).deploy(files)
        print("Firebase Spark static site: " + result)
        print("Billing remained disabled at each deployment checkpoint. No model calls were made.")
        return 0
    except (DeploymentError, OSError, subprocess.SubprocessError) as exc:
        print("Deployment stopped: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
