"""Execute deploy.sh against command doubles. No Google Cloud calls or resources."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
BASH=shutil.which("bash") or (str(Path("C:/Program Files/Git/bin/bash.exe")) if Path("C:/Program Files/Git/bin/bash.exe").exists() else None)
pytestmark=pytest.mark.skipif(not BASH,reason="Bash is needed for executable deployment checks")


@pytest.fixture
def deploy_stub(tmp_path):
    commands=tmp_path/"bin"
    commands.mkdir()
    gcloud=commands/"gcloud"
    gcloud.write_text('''#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$DEPLOY_RECORD"
if [[ "$1 $2 $3" == "firestore indexes composite" && "$4" == list ]]; then
 printf '%s\n' '[{"fields":[{"fieldPath":"store_id","order":"ASCENDING"},{"fieldPath":"created_at","order":"DESCENDING"},{"fieldPath":"__name__","order":"DESCENDING"}],"queryScope":"COLLECTION","state":"READY"}]'
elif [[ "$1 $2 $3" == "secrets versions list" ]]; then
 if [[ "${MOCK_HAS_APP_SECRET:-false}" == true ]]; then printf '%s\n' 'projects/mock/secrets/app/versions/1'; fi
elif [[ "$1 $2" == "projects describe" ]]; then
 printf '%s\\n' '123456789012'
elif [[ "$1 $2" == "run deploy" ]]; then
 for argument in "$@"; do
  if [[ "$argument" == --env-vars-file=* ]]; then cp "${argument#*=}" "$DEPLOY_ENV_CAPTURE"; fi
 done
elif [[ "$1 $2 $3" == "run services describe" ]]; then
 printf '%s\n' 'https://mock-cloud-run.example.invalid'
fi
''',encoding="utf-8",newline="\n")
    bq=commands/"bq"
    bq.write_text('''#!/usr/bin/env bash
set -eu
printf 'bq %s\n' "$*" >> "$DEPLOY_RECORD"
if [[ "${FAIL_WAREHOUSE:-false}" == true ]]; then exit 1; fi
''',encoding="utf-8",newline="\n")
    gcloud.chmod(0o755)
    bq.chmod(0o755)
    record=tmp_path/"commands.txt"
    env_capture=tmp_path/"deployed-env.json"
    env={**os.environ,"PATH":str(commands)+os.pathsep+os.environ["PATH"],
         "GCP_PROJECT":"retailiq-test-project","PYTHON_BIN":Path(sys.executable).as_posix(),
         "DEPLOY_RECORD":record.as_posix(),"DEPLOY_ENV_CAPTURE":env_capture.as_posix(),
         "PUBLIC_DEMO":"false","APP_KEY_FILE":"","GEMINI_KEY_FILE":""}
    env.pop("GEMINI_MODEL",None)
    env.pop("VERTEX_LOCATION",None)
    def execute(**changes):
        result=subprocess.run([BASH,(ROOT/"gcp/deploy.sh").as_posix(),"service"],
            env={**env,**changes},cwd=ROOT,capture_output=True,text=True,timeout=60)
        return result,record.read_text() if record.exists() else "",json.loads(env_capture.read_text()) if env_capture.exists() else {}
    return execute,tmp_path


def test_real_deploy_command_is_private_by_default(deploy_stub):
    execute,_=deploy_stub
    result,commands,env=execute()
    assert result.returncode==0,result.stdout+result.stderr
    assert "--no-allow-unauthenticated" in commands and " --allow-unauthenticated" not in commands
    assert "--clear-secrets" in commands
    assert "--member=serviceAccount:123456789012-compute@developer.gserviceaccount.com --role=roles/run.builder" in commands
    assert "--filter=COLLECTION_GROUP:visit_events" in commands
    assert env["RETAILIQ_TRUST_IAM"]=="true" and env["RETAILIQ_OPEN_DEMO"]=="false"
    assert env["GEMINI_MODEL"]=="gemini-3.6-flash" and env["VERTEX_LOCATION"]=="global"
    assert env["BQ_LOCATION"]=="asia-south1"
    assert "indexes composite create" not in commands,"The existing ready index should not be recreated"
    assert "--lifecycle-file=" in commands and "--public-access-prevention" in commands


def test_judge_deployment_mounts_token_without_printing_it(deploy_stub):
    execute,tmp_path=deploy_stub
    token="TEST-ONLY-ACCESS-TOKEN-DO-NOT-PUBLISH-12345"
    key_file=tmp_path/"application-token.txt"
    key_file.write_text(token)
    result,commands,env=execute(PUBLIC_DEMO="true",APP_KEY_FILE=key_file.as_posix())
    assert result.returncode==0,result.stdout+result.stderr
    assert "--allow-unauthenticated" in commands
    assert "RETAILIQ_API_KEY=retailiq-access-key:latest" in commands
    assert env["RETAILIQ_TRUST_IAM"]=="false" and env["RETAILIQ_OPEN_DEMO"]=="false"
    assert token not in commands+result.stdout+result.stderr+json.dumps(env)


def test_public_deployment_refuses_missing_application_secret(deploy_stub):
    execute,_=deploy_stub
    result,commands,_=execute(PUBLIC_DEMO="true",MOCK_HAS_APP_SECRET="false")
    assert result.returncode!=0 and "Refusing anonymous deployment" in result.stderr
    assert "run deploy" not in commands


def test_service_only_command_refuses_missing_warehouse(deploy_stub):
    execute,_=deploy_stub
    result,commands,_=execute(FAIL_WAREHOUSE="true")
    assert result.returncode!=0 and "bash gcp/deploy.sh all" in result.stderr
    assert "run deploy" not in commands
