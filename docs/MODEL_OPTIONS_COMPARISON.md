# Qwen fine-tuning, paid inference and models trained by us

Prepared 7 November 2026 for Bites by Batore. Research and calculations only: no paid model was enabled, no private examples uploaded and no training run performed. The current local-only requirement remains in force.

**Recommendation:** keep the local baseline while building reviewed examples. If cloud inference is later permitted, benchmark a low-cost multimodal API before spending on fine-tuning. Fine-tune Qwen when reviewed data and a measured domain gap justify it. Start fully owned training with narrow classifiers/rankers; do not attempt to replace multilingual vision, speech and reasoning from the present collected dataset.

## What data and hardware we actually have

The local audit found 51 source records across 47 distinct URLs, 26 completed video observation results, **zero operator evaluation labels and zero reviewer corrections**. At this checkpoint the representative records retained only seven raw captions, four transcripts and zero cached media payloads. Existing raw source caches expire; saved summaries, extracted names and six reference images are not a labelled video-training corpus. Details: `data/model-dataset-audit-20261107.json`.

This is an evidence collection database, not a training-ready dataset. Model outputs cannot be treated as correct targets merely because they were stored. Duplicate posts/creators, missing modalities, language coverage, exact branch labels and input/target alignment need review. We should explicitly design permitted training retention and dataset provenance before making long-lived training copies; this work did not change the source-cache policy.

Hardware rechecked: RTX 3050 Laptop GPU with **4,096 MiB VRAM**, about **15.4 GiB usable RAM**. Current inference is Qwen3-VL 2B through Ollama, with separate local Whisper transcription. Ollama is the runner; Qwen and Whisper supply learned capabilities.

## Practical comparison

| Option | What it could improve | Requirements | Main limitation for us | Decision now |
|---|---|---|---|---|
| Keep Qwen plus retrieved corrections | Low-cost local extraction and reuse of scoped reviewer feedback | Existing laptop; actual corrections and independent evaluation | Small-model/OCR/transcription errors remain; retrieval is not training | Keep as baseline under current local-only rule |
| Fine-tune Qwen with LoRA/QLoRA | Domain vocabulary, output format, comment categories, some extraction consistency | Reviewed paired examples, frozen held-out set, training-compatible base weights and framework; enough VRAM | Still depends on Qwen's base weights; small biased data can worsen generalization; tuning Qwen alone does not retrain Whisper | Prepare data first; do not fine-tune the current unlabelled outputs |
| Paid cheap multimodal API | Potentially stronger image/video/language extraction without owning GPU training infrastructure | API access, explicit departure from local-only processing, usage accounting and our benchmark | Quality on Tamil food reels is unmeasured; variable API cost and vendor dependence | Best candidate for an inexpensive future comparison experiment |
| Our own narrow ML models | Relevance filtering, duplicate-pair scoring, comment classes, confidence calibration or itinerary ranking | Reviewed task labels/features; CPU or small GPU | Each model solves a narrow task; cannot independently watch, transcribe and reason about arbitrary reels | First practical path toward owned weights |
| Our own foundation vision/language/speech stack | Broad capabilities with weights trained from initialization | Large diverse aligned datasets, multiple training programs, substantial compute and evaluation | Present data is far too small and lacks labels; laptop/budget are not sufficient | Long-term research program, not the next delivery step |

Qwen provides an official fine-tuning workflow including image/video conversation formats and LoRA options. PEFT documents quantized adapter training. Neither is evidence that our 4 GB laptop can train our desired multimodal configuration successfully. [Qwen training repository](https://github.com/QwenLM/Qwen3-VL/tree/main/qwen-vl-finetune), [PEFT quantization](https://huggingface.co/docs/peft/main/developer_guides/quantization).

Fine-tuning adapts Qwen rather than creating an independent foundation model. Its model card lists Apache-2.0; a fine-tuned adapter still requires the compatible base model and applicable notices. [Qwen model card](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct).

## Paid candidates and price calculation

Rates checked against official pricing pages on 7 November. Gemini prices below are standard text/image/video input and text output per million tokens; audio can have a different rate. Gemini 3.8 prices are introductory through 31 December 2026. DeepSeek prices below use uncached input and its documented peak/off-peak distinction. No account or paid-model test was performed. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing.md), [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing.md).

**Scenario assumptions:** 1,000 reels/month; across all specialist calls for each reel, 10,000 billed input tokens and 2,000 billed output tokens. INR 90/USD is a planning assumption, not a live exchange-rate quote. These token counts are not measured usage; image resolution, video sampling, audio, repeated prompts and thinking output can change them substantially.

`Monthly USD = reel_count × (input_tokens × input_rate + output_tokens × output_rate) / 1,000,000`

| Candidate | Input / output USD per 1M | 1,000 reels/month, assumed INR | 3,000 reels/month, assumed INR |
|---|---:|---:|---:|
| Gemini 2.5 Flash-Lite, account eligibility unverified | 0.10 / 0.40 | 162 | 486 |
| Gemini 3.1 Flash-Lite | 0.25 / 1.50 | 495 | 1,485 |
| Gemini 3.5 Flash-Lite | 0.30 / 2.50 | 720 | 2,160 |
| Gemini 3.8 Flash, introductory | 0.75 / 3.75 | 1,350 | 4,050 |
| DeepSeek Flash, off-peak | 0.15 / 0.60 | 243 | 729 |
| DeepSeek Flash, peak | 0.30 / 1.20 | 486 | 1,458 |

Availability matters as well as price: Google's Developer API deprecation page still lists stable 2.5 Flash-Lite without a shutdown date, but notes restricted access to older 2.5 models; the separate Agent Platform route has already shut its general-use 2.5 models down. Do not assume a new account can use the cheapest legacy price. Verify the exact API and account; prefer the newer shortlist for this project. [Developer API lifecycle](https://ai.google.dev/gemini-api/docs/deprecations.md), [Google supported-model table](https://firebase.google.com/docs/ai-logic/models).

These are **model inference scenarios, not the full app bill**. They exclude taxes, currency/card charges, collection/search/Maps, storage, retries, manual review and engineering. A 1.5 multiplier for reprocessing changes the 1,000-reel Gemini 3.1 example from INR 495 to about INR 743. At ten times the input tokens, even a cheap model needs a new calculation. There is no promise that all our agents fit these example rates.

Gemini 3.1 Flash-Lite accepts text, images, audio and video; this makes it a useful first end-to-end candidate. DeepSeek Flash's documented API supports text/images, so our comparison would retain local audio transcription and sampled frames. Neither should be called better for our application until the same held-out cases are evaluated. [Gemini model card](https://deepmind.google/models/model-cards/gemini-3-1-flash-lite/), [DeepSeek model metadata](https://api-docs.deepseek.com/api/list-models/).

My proposed future shortlist is Gemini 3.1 Flash-Lite for a balanced multimodal baseline, the cheapest account-available Flash-Lite as a cost baseline, and DeepSeek Flash for text/frame comparison. Use a stronger model only for a measured subset of difficult cases. Do not select solely by model age, general leaderboards or the lowest token price. The INR 3,000 monthly target covers the whole application, so model spending needs its own allocation; an initial INR 1,000 ceiling would leave INR 2,000 for the other services. This is a proposal, not a changed configuration.

## Fine-tuning calculations and implementation

For an approximate 2-billion-parameter model:

- BF16 weights alone: `2B × 2 bytes = 4 GB` decimal, before vision activations, temporary buffers and training state. That already nearly consumes the laptop GPU.
- Four-bit base storage alone: approximately `2B × 0.5 = 1 GB`, excluding quantization metadata and unquantized modules. Training needs much more than stored weight size.
- An illustrative mixed-precision full Adam setup with two-byte weights/gradients, four-byte master weights and eight-byte moment state uses `2B × 16 = 32 GB` before activations. Actual layouts vary.

The 4 GB GPU is therefore not a sensible primary machine for representative video fine-tuning. Tiny, reduced-resolution adapter experiments might fit with careful offloading, but are not a validated production training setup. An engineering planning target for a 2B multimodal adapter experiment is **16–24 GB VRAM, 32 GB host RAM and 100–200 GB free SSD**, subject to a real memory benchmark. Larger frame counts/context or full fine-tuning need more. These are planning allowances, not guaranteed minima or a purchase recommendation.

Use the full training-compatible base model, PyTorch/Transformers/PEFT and the Qwen data processor. Freeze vision components initially where appropriate; start with short contexts, small frame sets, gradient accumulation and checkpointing. Keep the current model available for rollback. An Ollama quantized inference artifact is not automatically a suitable training checkpoint. Validate any adapter/merged-model conversion and multimodal runtime compatibility before deployment.

**Illustrative experiment:** 2,000 reviewed examples × 2,048 training tokens × 3 epochs = **12.288 million tokens**. At an assumed 100–500 effective training tokens/second, that is **34.1–6.8 GPU hours** per run, excluding preparation/evaluation. At a hypothetical INR 50/GPU-hour, approximately **INR 1,707–341** per run. Throughput and rental price are assumptions, not measurements or quotations; video processing and larger visual-token counts can make this higher. Three experiments triple compute.

Labelling can cost more than compute: 2,000 examples × 4 minutes = **133.3 hours**. At an assumed INR 200/hour, that is **INR 26,667**, before independent QA. If you review them yourself the cash expense may differ, but the time remains. Complex multilingual video labels often take longer than four minutes. The proposed example count is an initial experiment size, not evidence of sufficiency.

Fine-tune stable extraction behavior; keep changing menus/hours/closures in SQL evidence retrieval. Training weights on current menus does not keep them current.

## Training our own models

Start with a narrow supervised baseline such as TF-IDF plus logistic regression for comment/relevance classes, or a small ranker for branch candidates. CPU training on this laptop is feasible for such small models. No existing pretrained LLM weights are needed for that classifier, but reliable reviewed targets, negative examples and leakage-aware evaluation are still required. It cannot replace ASR, OCR, visual understanding and planning by itself.

For scale context only: an illustrative 2B foundation model trained on 40B tokens requires roughly `6 × parameters × tokens = 4.8 × 10^20` training FLOPs. At an assumed sustained 100 TFLOP/s, this is **1,333 GPU-hours** for the simplified core computation; at 10 TFLOP/s it is **13,333 hours**. This excludes failed runs, data preparation, multimodal encoders, ASR training, evaluation and deployment. The assumed throughput is not this laptop's measured training performance. Forty-seven discovered URLs do not supply anything close to such a broad corpus. Smaller specialist models need much less compute but have narrower capability.

## Experiment and deployment procedure

1. Collect agent-found examples and establish permitted retained inputs, exact time/frame alignment and independent references. Capture Tamil, English, code-switching, difficult signage, wrong-city clips, missing locations, reposts, conflicting comments and multiple branches.
2. Keep creator/venue/repost groups separate across training, tuning and final test partitions. Do not let held-out corrections enter retrieval. Start with a diverse reviewed benchmark; expand it when uncertainty intervals are wide. Existing provisional gates are not proof that a small benchmark represents all users/languages.
3. Run unchanged Qwen as the baseline. If cloud use is authorized later, send only the approved evaluation inputs to the selected APIs and log model IDs, prompt versions, exact billed usage, failures and latency.
4. Measure venue-name precision/recall, exact branch correctness, Tamil/English transcription and OCR errors, per-class comment scores, unknown/abstention behavior, cost and end-to-end latency. Count unsupported facts as errors. A model's own confidence or another model's agreement is not independent truth.
5. Tune Qwen only if the reviewed dataset and error analysis show a learnable gap. Compare on untouched groups against both unchanged Qwen and the affordable API. Require quality improvement without unacceptable cost/latency or language regression.
6. Promote a version only after offline evaluation and shadow operation. Keep model/prompt/config hashes, rollback, per-request budget limits and the final human location approval gate. Retraining never grants publication authority.

**Current decision:** no fine-tuning or scratch training from the present database; keep local Qwen/Whisper running. The fastest potential capability upgrade is a small paid-model benchmark once source-data cloud processing is permitted, while reviewed datasets accumulate for future owned specialists and Qwen adaptation.

Machine-readable calculations: `data/model-cost-comparison-20261107.json`. The broader ownership study remains in [OWNED_AI_FEASIBILITY.md](OWNED_AI_FEASIBILITY.md); this document provides the current three-way decision comparison, not a claim that owned models already exist.
