"""Gradio studio for YuE2 on Google Colab L4.

Importing this package must stay cheap: notebook cell 1 imports it before any
dependency is installed, so nothing here may import torch, gradio or yue2.
"""

__version__ = "0.1.1"

# Upstream pins. requirements-colab.txt carries the same YuE commit; the model
# revisions are the Hugging Face commits that were current on 2026-11-11.
YUE2_COMMIT = "1116bea76032bee5668e5f097294d082fa0b84f0"
MODEL_ID = "m-a-p/YuE2-3B"
MODEL_REVISION = "8f24312f187763b9854adeec87e437e2b03bbff1"
VAE_ID = "m-a-p/YuE2-Vae"
VAE_REVISION = "152733a19ad43aa67e367f9b5503ef8075bb5126"
