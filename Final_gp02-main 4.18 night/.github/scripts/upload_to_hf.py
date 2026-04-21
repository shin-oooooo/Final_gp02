"""Upload repo contents to Hugging Face Space via huggingface_hub API."""
import os
from huggingface_hub import HfApi

token = os.environ.get("HF_TOKEN", "").strip()
if not token:
    raise ValueError(
        "HF_TOKEN is empty. "
        "Make sure the GitHub secret SHINO_TOKEN is set and contains a valid HF access token (hf_...)."
    )

# 与 HF Space 仓库一致（GitHub 仓库名可与 Space 不同）
repo_id = "shinopqxm/lreport3l-main"

api = HfApi(token=token)

api.create_repo(
    repo_id=repo_id,
    repo_type="space",
    space_sdk="docker",
    exist_ok=True,
)

api.upload_folder(
    folder_path=".",
    repo_id=repo_id,
    repo_type="space",
    ignore_patterns=[
        ".git/**",
        "**/__pycache__/**",
        "*.pyc",
        # 仅上传默认 Kronos bundle（与仓库一致）；其余体积大且未使用
        "kronos_weights/kronos-base/**",
        "kronos_weights/kronos-mini/**",
        "kronos_weights/tokenizer-2k/**",
        "kronos_data/**",
        ".github/**",
        "check2.py",
    ],
)
print("Upload complete.")
