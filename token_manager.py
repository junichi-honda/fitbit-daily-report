import os, base64, requests
from nacl import encoding, public


def encrypt_secret(public_key_str, secret_value):
    pub_key = public.PublicKey(
        public_key_str.encode("utf-8"), encoding.Base64Encoder()
    )
    encrypted = public.SealedBox(pub_key).encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def update_github_secret(new_refresh_token):
    owner, repo = os.environ["GH_REPO_OWNER"], os.environ["GH_REPO_NAME"]
    headers = {
        "Authorization": f"Bearer {os.environ['GH_PAT']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    key_data = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key",
        headers=headers,
    ).json()
    requests.put(
        f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/FITBIT_REFRESH_TOKEN",
        headers=headers,
        json={
            "encrypted_value": encrypt_secret(key_data["key"], new_refresh_token),
            "key_id": key_data["key_id"],
        },
    ).raise_for_status()
    print("✅ GitHub Secret更新完了")
