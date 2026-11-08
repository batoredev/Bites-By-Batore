"""Local Qwen token budget guard using the installed model's own GGUF vocabulary."""

from functools import lru_cache
import httpx
from .providers import Unavailable

PATTERN = r"(?:'[sS]|'[tT]|'[rR][eE]|'[vV][eE]|'[mM]|'[lL][lL]|'[dD])|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"


@lru_cache(maxsize=2)
def installed_tokenizer(url, model, digest):
    from tokenizers import Tokenizer, Regex, models, pre_tokenizers

    from .local_models import inference_client

    response = inference_client().post(url + "/api/show", json={"model": model, "verbose": True}, timeout=15)
    response.raise_for_status()
    info = response.json()["model_info"]
    if info.get("tokenizer.ggml.model") != "gpt2" or info.get("tokenizer.ggml.pre") != "qwen2":
        raise Unavailable(
            "Exact context guard for this model tokenizer is unavailable; configure its tokenizer before analysis"
        )
    vocab = {value: index for index, value in enumerate(info["tokenizer.ggml.tokens"])}
    merges = [tuple(value.split(" ", 1)) for value in info["tokenizer.ggml.merges"]]
    tokenizer = Tokenizer(models.BPE(vocab=vocab, merges=merges))
    tokenizer.pre_tokenizer = pre_tokenizers.Sequence(
        [
            pre_tokenizers.Split(Regex(PATTERN), behavior="isolated"),
            pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False),
        ]
    )
    return tokenizer


def input_tokens(prompt, text):
    from .local_models import endpoint, inference_client
    from .config import settings

    try:
        url, model = endpoint(), settings().ollama_model
        response = inference_client().get(url + "/api/tags", timeout=3)
        response.raise_for_status()
        digest = next(m["digest"] for m in response.json()["models"] if m["name"] == model)
        tokenizer = installed_tokenizer(url, model, digest)
        return len(tokenizer.encode(prompt, add_special_tokens=False).ids) + len(
            tokenizer.encode(text, add_special_tokens=False).ids
        )
    except (httpx.HTTPError, ValueError, KeyError, StopIteration, TypeError) as exc:
        raise Unavailable(
            "Installed local tokenizer could not be verified; no input truncation is permitted"
        ) from exc
