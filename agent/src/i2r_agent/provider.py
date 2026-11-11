from __future__ import annotations

import json
import http.client
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .common import Failure, now, save


def credential(cfg):
    spec = cfg["model"]
    variable = spec["credential_variable"]
    if os.environ.get(variable):
        return os.environ[variable]
    path = Path(spec.get("credential_file", ""))
    if path.is_file():
        for line in path.read_text().splitlines():
            match = re.fullmatch(r"\s*(?:export\s+)?" + re.escape(variable) + r"\s*=\s*(.*?)\s*", line)
            if match:
                return match[1].strip('"\'')
    raise Failure("missing_credentials", f"Configure {variable}; no key is logged")


def decode_model_json(content,directory):
    """Repair only one terminal object delimiter; never rewrite code strings."""
    try:return json.loads(content)
    except json.JSONDecodeError as error:
        stripped=content.strip()
        for variant,label in [(stripped+'}','added one missing final object brace'),
                              (stripped[:-1] if stripped.endswith('}') else '', 'removed one trailing unmatched closing brace')]:
            try:value=json.loads(variant)
            except ValueError:continue
            if isinstance(value,dict):
                save(Path(directory)/'format-normalizations.json',{'normalization':label,'source_strings_unchanged':True})
                return value
        raise Failure('invalid_model_response',f'JSON syntax: {error.msg} at line {error.lineno}, column {error.colno}',
            {'position':error.pos,'excerpt':content[max(0,error.pos-200):error.pos+200],
             'instruction':'Return a complete JSON object. Escape backslashes inside strings; close every object/array. Original response is saved.'}) from error


class Provider:
    def __init__(self, cfg, directory):
        self.cfg, self.directory = cfg, Path(directory)
        self.calls = 0
        self.phase_calls = {'preprocessing':0,'generation':0,'source_optimization':0}
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.unknown_usage_requests = []
        # A resumed trial keeps the same budget, including requests interrupted
        # before a response arrived. Archived request/response files remain intact.
        for request_path in sorted(p for p in self.directory.glob('*/request.json') if p.parent.name.isdigit()):
            folder=request_path.parent
            self.calls=max(self.calls,int(folder.name))
            state_path=folder/'call-state.json'
            metadata_path=folder/'metadata.json'
            state=json.loads(state_path.read_text()) if state_path.exists() else (json.loads(metadata_path.read_text()) if metadata_path.exists() else {})
            phase=state.get('phase','generation')
            self.phase_calls[phase]=self.phase_calls.get(phase,0)+1
            response_path=folder/'response.json'
            if response_path.exists():
                response=json.loads(response_path.read_text())
                usage=response.get('usage') if isinstance(response,dict) else None
                if not isinstance(usage,dict) or not all(isinstance(usage.get(key),(int,float)) for key in self.usage):self.unknown_usage_requests.append(str(request_path))
                if isinstance(usage,dict):
                    for key in self.usage:
                        if isinstance(usage.get(key),(int,float)):self.usage[key]+=usage[key]
            else:self.unknown_usage_requests.append(str(request_path))

    def call(self, system, prompt, options=None, phase='generation', messages=None):
        if self.cfg['budgets']['max_model_calls'] and self.calls >= self.cfg['budgets']['max_model_calls']:
            raise Failure("budget_exhausted", "Model call budget exhausted")
        limit=(self.cfg['preprocessing']['max_plan_attempts'] if phase=='preprocessing'
               else self.cfg['repair']['max_attempts'] if phase=='generation' else None)
        if limit and self.phase_calls.get(phase,0)>=limit:
            raise Failure('budget_exhausted',phase+' model-call budget exhausted')
        gen, model = {**self.cfg["generation"], **(options or {})}, self.cfg["model"]
        effort=gen.get('reasoning_effort')
        if effort is not None and (not isinstance(effort,str) or effort not in {'low','high','max'}):
            raise Failure('invalid_model_config','reasoning_effort must be low, high or max when supplied')
        self.calls += 1
        self.phase_calls[phase]=self.phase_calls.get(phase,0)+1
        payload = {"model": model["name"], "messages": messages if messages is not None else [{"role":"system","content":system},{"role":"user","content":prompt}],
                   "response_format":{"type":"json_object"}, "max_tokens":gen["max_output_tokens"],
                   "temperature":gen["temperature"], "thinking":{"type":gen["thinking"]}, "stream":False}
        if effort is not None:payload["reasoning_effort"]=effort
        directory = self.directory / f"{self.calls:03d}"
        directory.mkdir(parents=True, exist_ok=True)
        save(directory / "request.json", payload)
        save(directory / "call-state.json", {'phase':phase,'started_at':now()})
        started = time.monotonic()
        request = urllib.request.Request(model["endpoint"].rstrip('/') + '/chat/completions',
            data=json.dumps(payload).encode(), headers={"Authorization":"Bearer " + credential(self.cfg),"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.cfg["budgets"]["model_seconds"]) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            detail=error.read(65536).decode('utf-8',errors='replace')
            secret=credential(self.cfg)
            if secret:detail=detail.replace(secret,'[REDACTED]')
            save(directory/'error.json',{'status':'provider_error','http_status':error.code,'detail':detail,'at':now()})
            raise Failure('provider_error',f'Model HTTP {error.code}: {detail}',{'http_status':error.code,'error':str(directory/'error.json'),'request':str(directory/'request.json'),'automatic_retry':False}) from error
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException, json.JSONDecodeError) as error:
            # Do not repeat unknown-outcome requests: doing so may double bill.
            save(directory / "error.json", {"status":"provider_error", "type":type(error).__name__,"at":now()})
            raise Failure("provider_error", f"Model request failed ({type(error).__name__}); request not automatically retried") from error
        save(directory / "response.json", result)
        if not isinstance(result,dict):
            self.unknown_usage_requests.append(str(directory/'request.json'))
            save(directory/'error.json',{'status':'provider_protocol_error','type':'ProviderProtocolError','reason':'Top-level response is not a JSON object','response':str(directory/'response.json'),'at':now(),'usage_unknown':True})
            raise Failure('provider_protocol_error','Provider returned non-object JSON; no model reply was decoded and usage remains unknown',{'response':str(directory/'response.json'),'request':str(directory/'request.json'),'automatic_retry':False})
        raw_usage=result.get('usage')
        usage_known=isinstance(raw_usage,dict) and all(isinstance(raw_usage.get(key),(int,float)) for key in self.usage)
        if not usage_known:self.unknown_usage_requests.append(str(directory/'request.json'))
        usage=raw_usage if isinstance(raw_usage,dict) else {}
        for key in self.usage:
            if isinstance(usage.get(key),(int,float)):self.usage[key]+=usage[key]
        save(directory / "metadata.json", {"seconds":time.monotonic()-started,"usage":usage,"cost_usd":None,'phase':phase,
                                           "model":result.get("model"),"id":result.get("id"),"usage_known":usage_known})
        choice = result["choices"][0]
        if choice.get("finish_reason") != "stop":
            content=choice.get('message',{}).get('content') or ''
            partial=directory/'partial-content.txt'
            partial.write_text(content if isinstance(content,str) else '',encoding='utf-8')
            raise Failure("incomplete_response", f"Completion ended with {choice.get('finish_reason')}",
                {'finish_reason':choice.get('finish_reason'),'response':str(directory/'response.json'),
                 'partial_content':str(partial),'partial_characters':len(content) if isinstance(content,str) else 0,
                 'partial_status':'unvalidated evidence only; never decoded or committed',
                 'max_tokens':payload['max_tokens'],'thinking':payload['thinking'],'reasoning_effort':payload.get('reasoning_effort'),'usage':usage})
        try:
            decoded=decode_model_json(choice['message']['content'],directory)
            if self.cfg.get('generation',{}).get('workflow')=='segmented-v8' and phase!='source_test_check':
                from .v8_response import normalize
                decoded,normalizations=normalize(decoded)
                if normalizations['omitted_optional_null_fields']:
                    save(directory/'response-normalizations.json',normalizations)
            return decoded
        except (KeyError,TypeError) as error:raise Failure('invalid_model_response','Expected textual JSON content') from error
