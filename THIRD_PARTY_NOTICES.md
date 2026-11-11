# Third-party notices

This repository contains no third-party source code and no model weights. At
runtime the notebook installs or downloads the components below.

| Component | Used for | License | Source |
|---|---|---|---|
| yue2-infer 0.1.6 (commit `1116bea`) | Song generation pipeline | Apache-2.0 | https://github.com/multimodal-art-projection/YuE |
| m-a-p/YuE2-3B weights | Song generation model | CC BY-NC 4.0 with additional creator permission | https://huggingface.co/m-a-p/YuE2-3B and upstream `MODEL_LICENSE` |
| m-a-p/YuE2-Vae weights | Audio decoder | See the model card and upstream `MODEL_LICENSE` | https://huggingface.co/m-a-p/YuE2-Vae |
| Gradio 6.17.3 | Web interface | Apache-2.0 | https://github.com/gradio-app/gradio |
| PyTorch 2.10.0 | Installed as a yue2-infer dependency | BSD-3-Clause | https://github.com/pytorch/pytorch |
| FFmpeg with LAME | MP3 export; called as an external program, preinstalled on Colab, not installed or shipped by this project | LGPL/GPL (depends on the build) | https://ffmpeg.org/legal.html |

yue2-infer brings further dependencies (transformers, huggingface-hub,
safetensors, tiktoken, numpy, soundfile, accelerate) under their own licenses;
see the upstream `THIRD_PARTY_NOTICES.md`.

The model weights are not covered by this repository's Apache-2.0 license.
Their terms are set by the YuE2 authors and are authoritative as published
upstream:
https://github.com/multimodal-art-projection/YuE/blob/main/MODEL_LICENSE
