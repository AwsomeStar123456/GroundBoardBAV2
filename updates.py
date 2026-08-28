# updates.py
"""
Pull firmware files from GitHub using update_manifest.json.

Only paths listed in the manifest are replaced. Local files that are
not in the manifest (config.json, user data, etc.) are left alone.
"""

import gc
import ssl
import socket

try:
    import uos as os
except Exception:
    import os

try:
    import ujson as json
except Exception:
    import json

try:
    import utime as time
except Exception:
    import time


RAW_HOST = "raw.githubusercontent.com"
API_HOST = "api.github.com"
DEFAULT_GITHUB_REPO = "AwsomeStar123456/GroundBoardBA"
DEFAULT_FALLBACK_FILES = [
    "main.py",
    "updates.py",
    "update_manifest.json",
    "lib/__init__.py",
    "lib/xglcd_font.py",
    "utils/__init__.py",
    "utils/airportwifi.py",
    "utils/apportal.py",
    "utils/button.py",
    "utils/config.py",
    "utils/i2cdisplay.py",
    "utils/led.py",
    "utils/metar.py",
    "utils/wifi.py",
]
DEFAULT_PRESERVE = ["config.json", "configKSLC.json"]


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000.0)


def _iso8601_utc_from_unix(ts):
    try:
        tm = time.gmtime(int(ts))
        return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
            tm[0], tm[1], tm[2], tm[3], tm[4], tm[5]
        )
    except Exception:
        return None


def _utc_now_iso8601():
    try:
        return _iso8601_utc_from_unix(time.time())
    except Exception:
        return None


def _wrap_tls(sock, host):
    try:
        return ssl.wrap_socket(sock, server_hostname=host)
    except Exception:
        return ssl.wrap_socket(sock)


def _ensure_dirs_for_file(path):
    if not path or "/" not in path:
        return
    cur = ""
    for p in path.split("/")[:-1]:
        if not p:
            continue
        cur = p if cur == "" else cur + "/" + p
        try:
            os.mkdir(cur)
        except Exception:
            pass


def _read_headers(sock, max_bytes=4096):
    data = b""
    while len(data) < max_bytes and b"\r\n\r\n" not in data:
        chunk = sock.read(256) if hasattr(sock, "read") else sock.recv(256)
        if not chunk:
            break
        data += chunk
    if b"\r\n\r\n" not in data:
        return None, None
    header, rest = data.split(b"\r\n\r\n", 1)
    return header, rest


def _parse_status_code(header_bytes):
    try:
        first = header_bytes.split(b"\r\n", 1)[0]
        return int(first.split(b" ")[1])
    except Exception:
        return None


def _http_get_stream(host, path, port=443, timeout_s=12, extra_headers=None):
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    try:
        try:
            s.settimeout(timeout_s)
        except Exception:
            pass
        s.connect(addr)
        ss = _wrap_tls(s, host)
        try:
            st = getattr(ss, "settimeout", None)
            if st:
                st(timeout_s)
        except Exception:
            pass

        headers = ""
        if extra_headers:
            for k, v in extra_headers.items():
                headers += "{}: {}\r\n".format(k, v)

        req = (
            "GET {} HTTP/1.0\r\n"
            "Host: {}\r\n"
            "User-Agent: RunwaySense-Updater\r\n"
            "Accept: */*\r\n"
            "Accept-Encoding: identity\r\n"
            "Connection: close\r\n"
            "{}"
            "\r\n"
        ).format(path, host, headers)

        try:
            ss.write(req.encode("utf-8"))
        except Exception:
            ss.send(req.encode("utf-8"))
        return ss, s
    except Exception:
        try:
            s.close()
        except Exception:
            pass
        raise


def _body_prefix(body, max_len=160):
    if not body:
        return ""
    try:
        if isinstance(body, (bytes, bytearray)):
            b = body[:max_len]
            try:
                return b.decode("utf-8")
            except Exception:
                return b.decode("latin-1")
        return str(body)[:max_len]
    except Exception:
        return ""


def _http_get_to_bytes(host, path, timeout_s=12, extra_headers=None, max_bytes=200000):
    ss = None
    s = None
    try:
        ss, s = _http_get_stream(host, path, timeout_s=timeout_s, extra_headers=extra_headers)
        header, rest = _read_headers(ss)
        if header is None:
            return None, None
        code = _parse_status_code(header)
        chunks = []
        size = 0
        if rest:
            chunks.append(rest)
            size += len(rest)
        while True:
            chunk = ss.read(1024) if hasattr(ss, "read") else ss.recv(1024)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise MemoryError("HTTP body exceeded max_bytes")
        return code, b"".join(chunks)
    finally:
        try:
            if ss:
                ss.close()
        except Exception:
            pass
        try:
            if s:
                s.close()
        except Exception:
            pass


def _http_get_to_file(host, path, dest_path, timeout_s=20, extra_headers=None):
    ss = None
    s = None
    tmp_path = dest_path + ".tmp"
    try:
        _ensure_dirs_for_file(dest_path)
        ss, s = _http_get_stream(host, path, timeout_s=timeout_s, extra_headers=extra_headers)
        header, rest = _read_headers(ss)
        if header is None:
            return False, "no_headers"
        code = _parse_status_code(header)
        if code != 200:
            return False, "http_{}".format(code)

        with open(tmp_path, "wb") as f:
            if rest:
                f.write(rest)
            while True:
                chunk = ss.read(1024) if hasattr(ss, "read") else ss.recv(1024)
                if not chunk:
                    break
                f.write(chunk)

        try:
            os.remove(dest_path)
        except Exception:
            pass
        try:
            os.rename(tmp_path, dest_path)
        except Exception:
            with open(tmp_path, "rb") as src, open(dest_path, "wb") as out:
                while True:
                    buf = src.read(1024)
                    if not buf:
                        break
                    out.write(buf)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return True, None
    except Exception as e:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return False, str(e)
    finally:
        try:
            if ss:
                ss.close()
        except Exception:
            pass
        try:
            if s:
                s.close()
        except Exception:
            pass


def _normalize_subdir(subdir):
    if not subdir:
        return ""
    return str(subdir).strip().strip("/")


def _join_repo_path(subdir, relpath):
    subdir = _normalize_subdir(subdir)
    relpath = str(relpath).lstrip("/")
    return (subdir + "/" + relpath) if subdir else relpath


def _repo_owner_and_name(repo):
    if not repo:
        return None, None
    try:
        repo = str(repo).strip()
        if repo.startswith("https://github.com/"):
            repo = repo[len("https://github.com/"):]
        if repo.endswith(".git"):
            repo = repo[:-4]
        repo = repo.strip("/")
    except Exception:
        pass
    if "/" not in repo:
        return None, None
    owner, name = repo.split("/", 1)
    owner = owner.strip()
    name = name.strip()
    if not owner or not name:
        return None, None
    return owner, name


def _cfg_get(cfg, key, default=None):
    if cfg is None:
        return default
    try:
        val = cfg.get(key, default)
        return default if val is None else val
    except Exception:
        return default


def _get_manifest_file_list(repo, branch, subdir, manifest_path):
    full_path = "/{}/{}/{}".format(repo, branch, _join_repo_path(subdir, manifest_path))
    code, body = _http_get_to_bytes(RAW_HOST, full_path, timeout_s=15, max_bytes=60000)
    if code != 200 or not body:
        return None
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception:
        obj = json.loads(body)
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("files"), list):
        return obj.get("files")
    return None


def _get_tree_file_list(repo_owner, repo_name, branch, subdir, allowed_exts):
    path = "/repos/{}/{}/git/trees/{}?recursive=1".format(repo_owner, repo_name, branch)
    headers = {"Accept": "application/vnd.github+json"}
    code, body = _http_get_to_bytes(API_HOST, path, timeout_s=20, extra_headers=headers, max_bytes=200000)
    if code != 200 or not body:
        return None, {"http": code, "body": _body_prefix(body)}
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception:
        obj = json.loads(body)
    tree = obj.get("tree") if isinstance(obj, dict) else None
    if not tree:
        return None, {"http": code, "body": _body_prefix(body), "error": "missing_tree"}

    subdir = _normalize_subdir(subdir)
    out = []
    for item in tree:
        try:
            if item.get("type") != "blob":
                continue
            p = item.get("path")
            if not p:
                continue
            if subdir:
                if not p.startswith(subdir + "/"):
                    continue
                p_rel = p[len(subdir) + 1:]
            else:
                p_rel = p
            if allowed_exts:
                ok = False
                for ext in allowed_exts:
                    if p_rel.endswith(ext):
                        ok = True
                        break
                if not ok:
                    continue
            out.append(p_rel)
        except Exception:
            pass
    return out, None


def run_update(cfg=None, connect_fn=None, progress_fn=None):
    """
    Download files listed in GitHub update_manifest.json and replace locals.

    Files not in the manifest are not touched.
    config.json is never overwritten.

    Returns (ok: bool, info: dict)
    """
    repo = _cfg_get(cfg, "GITHUB_REPO", DEFAULT_GITHUB_REPO) or DEFAULT_GITHUB_REPO
    branch = _cfg_get(cfg, "GITHUB_BRANCH", "main") or "main"
    subdir = _cfg_get(cfg, "GITHUB_SUBDIR", "") or ""
    manifest_path = _cfg_get(cfg, "UPDATE_MANIFEST_PATH", "update_manifest.json") or "update_manifest.json"

    allowed_exts = _cfg_get(cfg, "UPDATE_FILE_EXTENSIONS", [".py", ".json", ".mpy"])
    if not isinstance(allowed_exts, list):
        allowed_exts = [".py", ".json", ".mpy"]

    preserve = _cfg_get(cfg, "UPDATE_PRESERVE_FILES", DEFAULT_PRESERVE)
    if not isinstance(preserve, list):
        preserve = list(DEFAULT_PRESERVE)

    owner, name = _repo_owner_and_name(repo)
    if owner is None:
        return False, {"reason": "bad_config", "key": "GITHUB_REPO", "value": repo}

    if connect_fn is not None:
        try:
            st = connect_fn()
            if not st:
                return False, {"reason": "no_internet"}
        except Exception as e:
            return False, {"reason": "wifi_error", "error": str(e)}

    try:
        ts = _utc_now_iso8601()
        if ts and cfg is not None:
            cfg.set("LAST_UPDATE_CHECK", ts)
    except Exception:
        pass

    print("Update starting: repo=", repo, "branch=", branch, "subdir=", subdir)

    files = None
    try:
        files = _get_manifest_file_list(repo, branch, subdir, manifest_path)
        if files:
            print("Using manifest file list:", manifest_path, "count=", len(files))
    except Exception as e:
        print("Manifest fetch failed:", e)

    if not files:
        files, tree_err = _get_tree_file_list(owner, name, branch, subdir, allowed_exts)
        if not files:
            fallback = _cfg_get(cfg, "UPDATE_FALLBACK_FILES", DEFAULT_FALLBACK_FILES)
            if not isinstance(fallback, list) or not fallback:
                fallback = DEFAULT_FALLBACK_FILES
            print("GitHub API listing failed; using fallback list. err=", tree_err)
            files = fallback
            if not files:
                return False, {"reason": "no_file_list", "api": tree_err}
        else:
            print("Using GitHub tree file list. count=", len(files))

    # Never write preserved files, even if they appear in the manifest.
    preserve_set = set([str(p).lstrip("/") for p in preserve])
    files = [f for f in files if str(f).lstrip("/") not in preserve_set]

    def _sort_key(p):
        p = str(p)
        if p == "updates.py":
            return (2, p)
        if p == "main.py":
            return (3, p)
        return (1, p)

    files.sort(key=_sort_key)

    ok_count = 0
    fail = []
    total = len(files)

    for i, relpath in enumerate(files):
        gc.collect()
        relpath = str(relpath).lstrip("/")
        remote_path = "/{}/{}/{}".format(repo, branch, _join_repo_path(subdir, relpath))
        print("[{} / {}] GET".format(i + 1, total), remote_path, "->", relpath)
        if progress_fn:
            try:
                progress_fn(i + 1, total, relpath)
            except Exception:
                pass

        ok, err = _http_get_to_file(RAW_HOST, remote_path, relpath, timeout_s=25)
        if ok:
            ok_count += 1
        else:
            fail.append({"file": relpath, "error": err})
            break
        _sleep_ms(50)

    if fail:
        print("Update failed:", fail[0])
        return False, {"reason": "download_failed", "ok": ok_count, "failed": fail}

    print("Update complete. files_updated=", ok_count)
    return True, {"updated": ok_count}
