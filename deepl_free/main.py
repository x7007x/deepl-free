import itertools
import json
import mimetypes
import os
import re
import time

import requests


class DeepLError(RuntimeError):
    pass


class DeepL:
    ENDPOINT = "https://oneshot-free.www.deepl.com/v1/translate"
    TABLES_URL = "https://raw.githubusercontent.com/un-ts/deeplx/master/packages/%40deeplx/core/src/constants.ts"
    DOC_BASE = "https://document-translation-free.www.deepl.com/documentTranslation"
    CLEARANCE_URL = "https://clearance.deepl.com/token"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    def __init__(self, sleep=3, retries=120):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": self.USER_AGENT})
        self.sleep = sleep
        self.retries = retries

        try:
            raw = self.s.get(self.TABLES_URL, timeout=20).text
        except requests.RequestException as e:
            raise DeepLError(f"could not download language tables: {e}")

        def table(name):
            m = re.search(r"export const " + name + r"[^{]*\{(.*?)\n\}", raw, re.S)
            return dict(re.findall(r"^\s*'?([A-Z0-9-]+)'?\s*:\s*'([^']+)'", m.group(1), re.M)) if m else {}

        targets = table("TARGET_LANG_MAP")
        overrides = table("SOURCE_LANG_MAP")
        m = re.search(r"export const SUPPORTED_LANGUAGES\s*=\s*\[(.*?)\]\s*as const", raw, re.S)
        langs = re.findall(r"code:\s*'([^']+)'\s*,\s*language:\s*'([^']+)'", m.group(1)) if m else []
        mx = re.search(r"MAX_FREE_TEXT_LENGTH\s*=\s*(\d+)", raw)

        if not (targets and overrides and langs and mx):
            raise DeepLError(f"could not extract language tables from {self.TABLES_URL}")

        self.targets = targets
        self.sources = {**targets, **overrides}
        self.language_names = dict(langs)
        self.names = {v.lower(): k for k, v in self.language_names.items()}
        self.max_length = int(mx.group(1))

    def _resolve(self, table, language):
        lang = language.strip()
        code = table.get(lang.upper()) or table.get(self.names.get(lang.lower(), ""))
        if not code:
            raise ValueError(f"unsupported language: {language}")
        return code

    def _post(self, body):
        r = self.s.post(self.ENDPOINT, json=body, timeout=60)
        try:
            data = r.json()
        except ValueError:
            raise DeepLError(f"invalid response (HTTP {r.status_code})")

        if r.status_code != 200 and "exceeds maximum length" in json.dumps(data):
            limit = int(data.get("text_character_limit") or 0)
            if limit and limit != self.max_length:
                self.max_length = limit
                r = self.s.post(self.ENDPOINT, json=body, timeout=60)
                try:
                    data = r.json()
                except ValueError:
                    raise DeepLError(f"invalid response (HTTP {r.status_code})")

        if r.status_code != 200:
            if "exceeds maximum length" in json.dumps(data):
                raise DeepLError("text exceeds maximum length")
            raise DeepLError(data.get("title") or data.get("message") or f"HTTP {r.status_code}")

        out = data.get("translations") or []
        if len(out) != 1:
            raise DeepLError("translation count mismatch")
        return out[0]

    def translate(self, text, target="en", source="auto"):
        body = {"text": [text], "target_lang": self._resolve(self.targets, target)}
        if source and source.strip().lower() != "auto":
            body["source_lang"] = self._resolve(self.sources, source)
        return self._post(body)["text"]

    def detect(self, text):
        body = {"text": [text], "target_lang": next(iter(self.targets.values()))}
        return (self._post(body).get("detected_source_language") or "auto").upper()

    def languages(self):
        return dict(self.language_names)

    def translate_file(self, path, target="en", source="auto"):
        tgt = self._resolve(self.targets, target)
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lstrip(".").lower()
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        call_id = itertools.count(1)

        def clearance():
            r = self.s.get(self.CLEARANCE_URL,
                headers={"Origin": "https://www.deepl.com", "Referer": "https://www.deepl.com/"},
                timeout=20)
            if r.status_code != 200 or not any(c.name == "dl_clearance" for c in self.s.cookies):
                raise DeepLError("could not obtain clearance token")

        def upload():
            with open(path, "rb") as f:
                return self.s.post(self.DOC_BASE + "/upload",
                    params={"fileExtension": ext, "expectsPro": "false", "retainDocument": "false"},
                    files={"file": (name, f, content_type)}, timeout=120)

        def rpc(method, params):
            r = self.s.post(f"{self.DOC_BASE}?method={method}",
                json={"jsonrpc": "2.0", "method": method, "params": params, "id": next(call_id)},
                headers={"Content-Type": "application/json"}, timeout=60)
            try:
                data = r.json()
            except ValueError:
                raise DeepLError(f"invalid JSON-RPC response for {method} (HTTP {r.status_code})")
            if r.status_code != 200 or "error" in data:
                raise DeepLError(data.get("error", {}).get("message") or f"HTTP {r.status_code}")
            return data.get("result") or {}

        def wait(ref, wanted, error_terminal=False):
            last = None
            for _ in range(self.retries):
                result = rpc("getTranslationStatus", {"documentIdAndKey": ref, "expectsPro": False})
                last = result.get("status")
                if last == wanted:
                    return result
                if error_terminal and last == "error":
                    raise DeepLError(f"translation failed: {result.get('notes')}")
                time.sleep(self.sleep)
            raise DeepLError(f"document status did not reach {wanted!r} (last: {last!r})")

        clearance()
        r = upload()
        if r.status_code != 200 and "insufficient_clearance" in r.text:
            clearance()
            r = upload()
        if r.status_code != 200:
            try:
                message = r.json().get("error", {}).get("message") or r.text
            except ValueError:
                message = r.text
            raise DeepLError(f"upload failed: {message[:200]}")

        doc = r.json()
        ref = {"documentId": doc["id"], "documentKey": doc["key"]}
        analysis = wait(ref, "analysisDone")

        src = (self._resolve(self.sources, source)
               if source and source.strip().lower() != "auto"
               else (analysis.get("sourceLanguageCode") or "en"))

        rpc("startTranslation", {
            "documentIdAndKey": ref,
            "translationConfiguration": {
                "sourceLangCode": src, "targetLangCode": tgt,
                "languageModel": "nextgen", "enableWatermark": False,
            },
            "expectsPro": False,
        })
        wait(ref, "done", error_terminal=True)

        r = self.s.post(self.DOC_BASE + "/download", files={
            "documentId": (None, doc["id"]),
            "documentKey": (None, doc["key"]),
            "fileName": (None, name),
            "expectsPro": (None, "false"),
        }, timeout=120)
        if r.status_code != 200 or "json" in r.headers.get("content-type", ""):
            raise DeepLError(f"download failed: {r.text[:200]}")
        return r.content


if __name__ == "__main__":
    d = DeepL()
    print(len(d.languages()), "languages")
    print(d.translate("Hello, how are you?", "ar"))
    print(d.translate("مرحبا بك في القاهرة", "en"))
    print(d.translate("Hola mundo", target="de", source="es"))
    print(d.detect("Bonjour le monde"))
    print(d.languages()["ZH-HANS"])
